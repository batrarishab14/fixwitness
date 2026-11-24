"""Warehouse mode: run both versions of the SQL in your own warehouse, on the generated tables.

    fixwitness check models/revenue.sql --warehouse postgres://ci@db.internal:5432/analytics ...

DuckDB and SQLite stand in for a warehouse well for most logic, but not for everything a
warehouse does its own way (collations, NULL ordering, time zones, numeric types, functions). In
warehouse mode each run gets its own schema in your warehouse, created for that run and dropped
after it: the generated tables are loaded there, the SQL runs there as written (no translation),
and the result is read back.

Supported: Postgres (psycopg), Snowflake (snowflake-connector-python) and BigQuery
(google-cloud-bigquery). Postgres is tested in CI against a Postgres server; Snowflake and
BigQuery are written against their documented Python APIs and have not been run by the authors.

Credentials never go in the URL, because the URL is recorded in the proof: use the driver's own
settings (PGPASSWORD or ~/.pgpass, SNOWFLAKE_PASSWORD or a key file, Google application
credentials). Every case runs twice in the warehouse, so a check costs warehouse time: start
with --max-cases 60.

URL forms:
    postgres://USER@HOST:PORT/DATABASE
    snowflake://USER@ACCOUNT/DATABASE?warehouse=WH&role=ROLE
    bigquery://PROJECT?location=US
"""

from __future__ import annotations

import os
import re
import uuid
from urllib.parse import parse_qs, unquote, urlparse

URL_ENV = "FIXWITNESS_WAREHOUSE"
KINDS = ("postgres", "snowflake", "bigquery")
SECRET_ENV = {
    "postgres": ["PGPASSWORD", "PGPASSFILE", "PGSSLMODE", "PGSSLROOTCERT", "PGSERVICE", "PGSERVICEFILE"],
    "snowflake": ["SNOWFLAKE_PASSWORD", "SNOWFLAKE_PRIVATE_KEY_PATH", "SNOWFLAKE_PRIVATE_KEY_PASSPHRASE",
                  "SNOWFLAKE_AUTHENTICATOR", "SNOWFLAKE_TOKEN"],
    "bigquery": ["GOOGLE_APPLICATION_CREDENTIALS", "GOOGLE_CLOUD_PROJECT", "CLOUDSDK_CONFIG"],
}
DRIVER = {"postgres": "psycopg", "snowflake": "snowflake.connector", "bigquery": "google.cloud.bigquery"}
TYPES = {
    "postgres": {"integer": "BIGINT", "number": "DOUBLE PRECISION", "date": "DATE", "text": "TEXT",
                 "boolean": "BOOLEAN", "timestamp": "TIMESTAMP"},
    "snowflake": {"integer": "NUMBER(38,0)", "number": "FLOAT", "date": "DATE", "text": "VARCHAR",
                  "boolean": "BOOLEAN", "timestamp": "TIMESTAMP_NTZ"},
    "bigquery": {"integer": "INT64", "number": "FLOAT64", "date": "DATE", "text": "STRING",
                 "boolean": "BOOL", "timestamp": "DATETIME"},
}
_SIMPLE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
# Reserved words of Postgres, Snowflake and BigQuery: a column or table with one of these names
# (`default`, `user`, `end`) must be quoted, as dbt does when it loads seeds.
RESERVED = set("""
all analyse analyze and any array as asc assert_rows_modified asymmetric at authorization between binary both
by case cast check collate collation column concurrently connect connection constraint contains create cross
cube current current_catalog current_date current_role current_schema current_time current_timestamp
current_user database default deferrable define delete desc distinct do drop else end enum escape except
exclude exists extract false fetch following for foreign freeze from full grant group grouping groups
gscluster hash having if ignore ilike in increment initially inner insert intersect interval into is isnull
issue join lateral leading left like limit localtime localtimestamp lookup merge minus natural new no not
notnull null nulls of offset on only or order organization outer over overlaps partition placing preceding
primary proto qualify range recursive references regexp respect returning revoke right rlike rollup row rows
sample schema select session_user set similar some start struct symmetric system_user table tablesample then
to trailing treat trigger true try_cast unbounded union unique unnest update user using values variadic
verbose view when whenever where window with within
""".split())


class WarehouseError(Exception):
    pass


def parse_url(url: str) -> dict:
    u = urlparse(url)
    kind = {"postgresql": "postgres", "pg": "postgres"}.get(u.scheme, u.scheme)
    if kind not in KINDS:
        raise WarehouseError(f"unknown warehouse {u.scheme!r}: use postgres://, snowflake:// or bigquery://")
    if u.password:
        raise WarehouseError("put the password in the driver's own setting (PGPASSWORD, SNOWFLAKE_PASSWORD, ...), "
                             "not in the URL: the URL is recorded in the proof")
    q = {k: v[-1] for k, v in parse_qs(u.query).items()}
    return {"kind": kind, "user": unquote(u.username) if u.username else None, "host": u.hostname,
            "port": u.port, "path": u.path.strip("/"), "query": q}


def check_url(url: str) -> str:
    """Validate the URL and that its driver is installed; return the warehouse kind."""
    info = parse_url(url)
    import importlib.util
    mod = DRIVER[info["kind"]]
    try:
        found = importlib.util.find_spec(mod) is not None
    except ModuleNotFoundError:
        found = False
    if not found and info["kind"] == "postgres":
        found = importlib.util.find_spec("psycopg2") is not None
    if not found:
        pip = {"postgres": "psycopg[binary]", "snowflake": "snowflake-connector-python",
               "bigquery": "google-cloud-bigquery"}[info["kind"]]
        raise WarehouseError(f"warehouse mode for {info['kind']} needs its driver: pip install {pip}")
    return info["kind"]


def ident(name: str, kind: str, exact: bool = False) -> str:
    """A simple name is left unquoted, so the warehouse folds its case the way your SQL's names fold;
    a reserved word or any other name is quoted. exact: quote it as written (a name the warehouse
    already stored, or one dbt's compiled SQL quotes)."""
    if _SIMPLE.fullmatch(name) and name.lower() not in RESERVED and not exact:
        return name
    if kind == "bigquery":
        return "`" + name.replace("`", "\\`") + "`"
    if kind == "snowflake" and not exact and _SIMPLE.fullmatch(name):
        name = name.upper()  # what an unquoted name folds to
    return '"' + name.replace('"', '""') + '"'


class Session:
    """One run's private schema: created on enter, dropped on exit."""

    def __init__(self, url: str):
        self.info = parse_url(url)
        self.kind = self.info["kind"]
        self.schema = "fw_" + uuid.uuid4().hex[:12]
        self.con = None
        self.client = None

    # ---- connect
    def __enter__(self):
        k, i = self.kind, self.info
        if k == "postgres":
            try:
                import psycopg
                self.con = psycopg.connect(host=i["host"], port=i["port"] or 5432, user=i["user"],
                                           dbname=i["path"] or None, autocommit=True)
            except ImportError:
                import psycopg2
                self.con = psycopg2.connect(host=i["host"], port=i["port"] or 5432, user=i["user"],
                                            dbname=i["path"] or None)
                self.con.autocommit = True
            self._exec(f"CREATE SCHEMA {self.schema}")
            self._exec(f"SET search_path TO {self.schema}")
            # A query that runs away (a date spine from 1970) is stopped by the server too, not only
            # by fixwitness's own time limit, which ends the client but not the server's work.
            self._exec(f"SET statement_timeout TO '{_statement_seconds()}s'")
        elif k == "snowflake":
            import snowflake.connector
            args = {"user": i["user"], "account": i["host"], "database": i["path"] or None,
                    "warehouse": i["query"].get("warehouse"), "role": i["query"].get("role"),
                    "password": os.environ.get("SNOWFLAKE_PASSWORD"),
                    "authenticator": os.environ.get("SNOWFLAKE_AUTHENTICATOR"),
                    "private_key_file": os.environ.get("SNOWFLAKE_PRIVATE_KEY_PATH"),
                    "private_key_file_pwd": os.environ.get("SNOWFLAKE_PRIVATE_KEY_PASSPHRASE"),
                    "token": os.environ.get("SNOWFLAKE_TOKEN")}
            self.con = snowflake.connector.connect(**{a: v for a, v in args.items() if v})
            self._exec(f"CREATE TRANSIENT SCHEMA {self.schema}")
            self._exec(f"USE SCHEMA {self.schema}")
        else:
            from google.cloud import bigquery
            from google.cloud.bigquery import dbapi
            self.client = bigquery.Client(project=i["host"] or None, location=i["query"].get("location"))
            ds = bigquery.Dataset(f"{self.client.project}.{self.schema}")
            ds.location = i["query"].get("location") or ds.location
            ds.default_table_expiration_ms = 3600 * 1000  # gone within the hour even if the drop fails
            self.client.create_dataset(ds)
            self.con = dbapi.connect(self.client)
        return self

    def __exit__(self, *exc):
        try:
            if self.kind == "bigquery" and self.client is not None:
                self.client.delete_dataset(f"{self.client.project}.{self.schema}", delete_contents=True,
                                           not_found_ok=True)
            elif self.con is not None:
                self._exec(f"DROP SCHEMA IF EXISTS {self.schema} CASCADE")
        finally:
            if self.con is not None:
                self.con.close()
        return False

    def _exec(self, sql: str, params=None):
        cur = self.con.cursor()
        cur.execute(sql, params) if params is not None else cur.execute(sql)
        return cur

    # ---- tables and queries
    def _job_config(self):
        from google.cloud import bigquery
        return bigquery.QueryJobConfig(default_dataset=f"{self.client.project}.{self.schema}")

    def load(self, tables: dict[str, str], types: dict, exact: dict | None = None, quoted: bool = False) -> None:
        """Create and fill each table. `exact`: the SQL type dbt gave a column in this warehouse,
        used in place of the kind's default type. `quoted`: table names exactly as written (dbt's
        compiled SQL quotes every relation it reads)."""
        from fixwitness.sql import seed_column_key as key, typed_rows
        for name, text in tables.items():
            header, kinds, rows = typed_rows(name, text, types)
            given = {key(c): (c, t) for c, t in ((exact or {}).get(name) or {}).items()}
            sql_types = [given[key(c)][1] if key(c) in given else TYPES[self.kind][k] for c, k in zip(header, kinds)]
            # Column names as the warehouse stored them for dbt's seed, quoted exactly; others as usual.
            names = [ident(given[key(c)][0], self.kind, exact=True) if key(c) in given else ident(c, self.kind)
                     for c in header]
            cols = ", ".join(f"{n} {t}" for n, t in zip(names, sql_types))
            if self.kind == "bigquery":
                from google.cloud import bigquery
                schema = [bigquery.SchemaField(c, t) for c, t in zip(header, sql_types)]
                table = f"{self.client.project}.{self.schema}.{name}"
                self.client.create_table(bigquery.Table(table, schema=schema))
                if rows:
                    data = [{c: (v.isoformat() if hasattr(v, "isoformat") else v) for c, v in zip(header, r)}
                            for r in rows]
                    job = self.client.load_table_from_json(data, table, job_config=bigquery.LoadJobConfig(schema=schema))
                    job.result()
                continue
            self._exec(f"CREATE TABLE {ident(name, self.kind, quoted)} ({cols})")
            if rows:
                marks = ", ".join(["%s"] * len(header))
                self.con.cursor().executemany(f"INSERT INTO {ident(name, self.kind, quoted)} VALUES ({marks})", rows)

    def query(self, sql: str):
        if self.kind == "bigquery":
            cur = self.con.cursor()  # unqualified names resolve in this run's dataset
            cur.execute(sql, job_config=self._job_config())
            return cur
        return self._exec(sql)

    def create_as(self, name: str, sql: str, quoted: bool = False) -> None:
        self.query(f"CREATE TABLE {ident(name, self.kind, quoted)} AS {sql}")


def _connect(url: str):
    """A plain connection (no private schema) for housekeeping: listing and dropping schemas."""
    i = parse_url(url)
    if i["kind"] == "postgres":
        try:
            import psycopg
            return psycopg.connect(host=i["host"], port=i["port"] or 5432, user=i["user"],
                                   dbname=i["path"] or None, autocommit=True)
        except ImportError:
            import psycopg2
            con = psycopg2.connect(host=i["host"], port=i["port"] or 5432, user=i["user"], dbname=i["path"] or None)
            con.autocommit = True
            return con
    if i["kind"] == "snowflake":
        import snowflake.connector
        args = {"user": i["user"], "account": i["host"], "database": i["path"] or None,
                "warehouse": i["query"].get("warehouse"), "role": i["query"].get("role"),
                "password": os.environ.get("SNOWFLAKE_PASSWORD"),
                "authenticator": os.environ.get("SNOWFLAKE_AUTHENTICATOR"),
                "private_key_file": os.environ.get("SNOWFLAKE_PRIVATE_KEY_PATH"),
                "private_key_file_pwd": os.environ.get("SNOWFLAKE_PRIVATE_KEY_PASSPHRASE"),
                "token": os.environ.get("SNOWFLAKE_TOKEN")}
        return snowflake.connector.connect(**{a: v for a, v in args.items() if v})
    raise WarehouseError("bigquery uses its client")


def _schemas(url: str, prefix: str) -> list[str]:
    """The schemas (BigQuery: datasets) whose name starts with prefix: a private schema and the
    custom schemas dbt made from it (prefix_staging, ...)."""
    if not re.fullmatch(r"fw_[0-9a-f]{6,32}", prefix):
        raise WarehouseError(f"refusing to touch schemas named {prefix}*: not a fixwitness private schema")
    i = parse_url(url)
    if i["kind"] == "bigquery":
        from google.cloud import bigquery
        client = bigquery.Client(project=i["host"] or None, location=i["query"].get("location"))
        return [d.dataset_id for d in client.list_datasets() if d.dataset_id.lower().startswith(prefix)]
    con = _connect(url)
    try:
        cur = con.cursor()
        cur.execute("select schema_name from information_schema.schemata")
        return [r[0] for r in cur.fetchall() if str(r[0]).lower().startswith(prefix)]
    finally:
        con.close()


def columns(url: str, prefix: str) -> list[tuple[str, str, str, str]]:
    """(schema, table, column, type) of every table in the private schemas."""
    i = parse_url(url)
    names = _schemas(url, prefix)
    out = []
    if i["kind"] == "bigquery":
        from google.cloud import bigquery
        client = bigquery.Client(project=i["host"] or None, location=i["query"].get("location"))
        for ds in names:
            q = (f"select table_schema, table_name, column_name, data_type from "
                 f"`{client.project}.{ds}`.INFORMATION_SCHEMA.COLUMNS order by table_name, ordinal_position")
            out += [tuple(r.values()) for r in client.query(q).result()]
        return out
    con = _connect(url)
    try:
        cur = con.cursor()
        for name in names:
            cur.execute("select table_schema, table_name, column_name, data_type from information_schema.columns "
                        "where table_schema = %s order by table_name, ordinal_position", (name,))
            out += [tuple(r) for r in cur.fetchall()]
    finally:
        con.close()
    return out


def drop_schemas(url: str, prefix: str) -> list[str]:
    """Drop the private schemas (and what dbt built in them)."""
    i = parse_url(url)
    names = _schemas(url, prefix)
    if i["kind"] == "bigquery":
        from google.cloud import bigquery
        client = bigquery.Client(project=i["host"] or None, location=i["query"].get("location"))
        for ds in names:
            client.delete_dataset(f"{client.project}.{ds}", delete_contents=True, not_found_ok=True)
        return names
    con = _connect(url)
    try:
        cur = con.cursor()
        for name in names:
            cur.execute(f"DROP SCHEMA IF EXISTS {ident(name, i['kind'])} CASCADE")
    finally:
        con.close()
    return names


def _statement_seconds() -> int:
    try:
        return max(1, int(float(os.environ.get("FIXWITNESS_STATEMENT_TIMEOUT", "300"))))
    except ValueError:
        return 300


def url_from_env() -> str:
    url = os.environ.get(URL_ENV)
    if not url:
        raise WarehouseError(f"engine 'warehouse' needs {URL_ENV} (set by fixwitness from --warehouse)")
    return url
