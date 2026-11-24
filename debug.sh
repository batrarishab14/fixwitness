git clone -q https://github.com/fivetran/dbt_zendesk.git z
python - <<'PY'
import json, sys, traceback
from pathlib import Path
from fixwitness import dbtmode, sql
proj = Path("z/integration_tests").resolve()
out = Path("/tmp/fwz")
notes = []
m = dbtmode.compile_project(proj, out, notes=notes)
print("NOTES", notes)
g = dbtmode.read_manifest(m, proj)
print("BARE stg_zendesk__brand:\n", dbtmode.bare_sql(g, "stg_zendesk__brand")[:1500])
st = dbtmode.seed_types(m)
print("SEED TYPES brand_data:", st[0], st[1].get("brand_data"))
d = Path("/tmp/fwz_models"); dbtmode.write_models(g, d)
(d / sql.TYPES_FILE).write_text(json.dumps({"adapter": st[0], "types": st[1]}))
tables = {n: p.read_bytes() for n, p in g.seeds.items() if p.is_file()}
types = {n: sql.table_types(b) for n, b in tables.items()}
for n, cols in st[1].items():
    for c in list(types.get(n, {})):
        lc = {k.lower(): v for k, v in cols.items()}
        if c.lower() in lc: types[n][c] = sql.kind_of(lc[c.lower()])
try:
    res = sql.run_pipeline(d, sql.make_bundle(tables, types), engine="duckdb", dbt="off", outputs=["stg_zendesk__brand"])
    print("OK", sql.read_outputs(res)["stg_zendesk__brand"][:300])
except Exception:
    traceback.print_exc()
import duckdb
con = duckdb.connect()
sql.load_tables(con, "duckdb", {"brand_data": tables["brand_data"].decode()}, types, st[1])
print(con.execute("select column_name, data_type from information_schema.columns where table_name='brand_data'").fetchall()[:8])
print(con.execute('select "default" from brand_data').fetchall()[:3])
PY
