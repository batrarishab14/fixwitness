git clone -q https://github.com/fivetran/dbt_zendesk.git z
git -C z log -1 --format='%H %s'
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
print("SEEDS", sorted(g.seeds)[:40])
print("SOURCES", sorted(g.sources)[:10])
st = dbtmode.seed_types(m)
print("SEED TYPES keys:", st[0], sorted(st[1])[:30])
data = json.loads(m.read_text())
for n in data["nodes"].values():
    if n["resource_type"] == "seed" and "brand" in n["name"]:
        print("SEEDNODE", n["name"], n.get("schema"), n.get("alias"), n.get("relation_name"), n.get("original_file_path"))
import duckdb
con = duckdb.connect(str(out / "fixwitness.duckdb"), read_only=True)
print(con.execute("select table_schema, table_name, count(*) from information_schema.columns group by 1,2 order by 1,2").fetchall()[:40])
for name in ("stg_zendesk__brand", "stg_zendesk__ticket"):
    sqltext = dbtmode.bare_sql(g, name)
    print("HAS default:", name, '"default"' in sqltext, sqltext.count("cast(null"))
PY
