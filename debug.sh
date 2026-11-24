set -x
python - <<'PY'
import duckdb
con = duckdb.connect()
con.execute('create table t ("default" BOOLEAN, id BIGINT)')
con.executemany('insert into t values (?, ?)', [[True, 1]])
print(con.execute('select "default" from t').fetchall())
print(con.execute("select column_name from information_schema.columns where table_name='t'").fetchall())
PY
git clone -q https://github.com/fivetran/dbt_zendesk.git z && cd z/integration_tests
mkdir -p ~/.dbt && cat > ~/.dbt/profiles.yml <<'P'
integration_tests:
  target: duckdb
  outputs:
    duckdb:
      type: duckdb
      path: /tmp/z.duckdb
      schema: zendesk_integration_tests
      threads: 1
P
dbt deps -q && dbt seed -q --select brand_data && dbt run -q --select +stg_zendesk__brand ; dbt compile -q --select stg_zendesk__brand stg_zendesk__brand_tmp
cat target/compiled/zendesk/models/staging/stg_zendesk__brand.sql | head -40
python - <<'PY'
import duckdb
con = duckdb.connect('/tmp/z.duckdb', read_only=True)
print(con.execute("select table_schema, table_name, column_name, data_type from information_schema.columns where table_name in ('brand_data','stg_zendesk__brand_tmp') and column_name ilike '%default%'").fetchall())
PY
