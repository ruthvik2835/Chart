# export_sqlite_to_csv.py
import sqlite3
import pandas as pd
from django.db import models


DB = "db.sqlite3"
TABLES = [
    "Item",
    "Item_1ms", "Item_10ms", "Item_100ms",
    "Item_1s", "Item_10s", "Item_1min"
]

conn = sqlite3.connect(DB)
for tbl in TABLES:
    df = pd.read_sql_query(f"SELECT * FROM {tbl}", conn)
    # rename columns to avoid q conflicts
    if "min" in df.columns: df = df.rename(columns={"min":"min_price"})
    if "max" in df.columns: df = df.rename(columns={"max":"max_price"})
    fname = f"{tbl}.csv"
    df.to_csv(fname, index=False)
    print(f"→ wrote {len(df)} rows to {fname}")

conn.close()
