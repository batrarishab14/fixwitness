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
    "postgres": {"integer": "BIGINT", "number": "DOUBLE PRECISION", "date": "DATE", "text": "TEXT"},
    "snowflake": {"integer": "NUMBER(38,0)", "number": "FLOAT", "date": "DATE", "text": "VARCHAR"},
    "bigquery": {"integer": "INT64", "number": "FLOAT64", "date": "DATE", "text": "STRING"},
}
_SIMPLE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


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


def ident(name: str, kind: str) -> str:
    """A simple name is left unquoted, so the warehouse folds its case the way your SQL's names fold."""
    if _SIMPLE.fullmatch(name):
        return name
    if kind == "bigquery":
        return "`" + name.replace("`", "\\`") + "`"
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

    def load(self, tables: dict[str, str], types: dict) -> None:
        from fixwitness.sql import typed_rows
        for name, text in tables.items():
            header, kinds, rows = typed_rows(name, text, types)
            cols = ", ".join(f"{ident(c, self.kind)} {TYPES[self.kind][k]}" for c, k in zip(header, kinds))
            if self.kind == "bigquery":
                from google.cloud import bigquery
                schema = [bigquery.SchemaField(c, TYPES["bigquery"][k]) for c, k in zip(header, kinds)]
                table = f"{self.client.project}.{self.schema}.{name}"
                self.client.create_table(bigquery.Table(table, schema=schema))
                if rows:
                    data = [{c: (v.isoformat() if hasattr(v, "isoformat") else v) for c, v in zip(header, r)}
                            for r in rows]
                    job = self.client.load_table_from_json(data, table, job_config=bigquery.LoadJobConfig(schema=schema))
                    job.result()
                continue
            self._exec(f"CREATE TABLE {ident(name, self.kind)} ({cols})")
            if rows:
                marks = ", ".join(["%s"] * len(header))
                self.con.cursor().executemany(f"INSERT INTO {ident(name, self.kind)} VALUES ({marks})", rows)

    def query(self, sql: str):
        if self.kind == "bigquery":
            cur = self.con.cursor()  # unqualified names resolve in this run's dataset
            cur.execute(sql, job_config=self._job_config())
            return cur
        return self._exec(sql)

    def create_as(self, name: str, sql: str) -> None:
        self.query(f"CREATE TABLE {ident(name, self.kind)} AS {sql}")


def url_from_env() -> str:
    url = os.environ.get(URL_ENV)
    if not url:
        raise WarehouseError(f"engine 'warehouse' needs {URL_ENV} (set by fixwitness from --warehouse)")
    return url
