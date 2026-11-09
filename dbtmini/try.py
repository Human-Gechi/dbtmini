import duckdb

conn = duckdb.connect("dbtmini.duckdb")
print(conn.sql("SELECT * FROM fct_orders"))
