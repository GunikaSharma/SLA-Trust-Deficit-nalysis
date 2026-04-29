# ============================================================
# FILE: 03_export_to_mysql.py
# WHAT THIS DOES: Uploads your cleaned CSV data into MySQL
# so you can run SQL queries in MySQL Workbench.
#
# BEFORE RUNNING THIS:
#   1. Open MySQL Workbench
#   2. Run this SQL to create the database:
#        CREATE DATABASE IF NOT EXISTS sla_analysis;
#   3. Come back here and set your password below
#
# HOW TO RUN: python 03_export_to_mysql.py
# ============================================================

import pandas as pd
import sqlalchemy   # connects Python to MySQL

# ── SET YOUR MYSQL PASSWORD HERE ──────────────────────────
MYSQL_PASSWORD = "Gunika%40123"   
MYSQL_USER     = "root"                 # usually root
MYSQL_HOST     = "localhost"            # usually localhost
MYSQL_PORT     = 3306                   # default MySQL port
DB_NAME        = "sla_analysis"
# ─────────────────────────────────────────────────────────

# Install if needed: pip install sqlalchemy pymysql
try:
    import pymysql
except ImportError:
    print("Installing pymysql...")
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pymysql"])
    import pymysql

print("Connecting to MySQL...")

# Build the connection string
connection_string = (
    f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}"
    f"@{MYSQL_HOST}:{MYSQL_PORT}/{DB_NAME}"
)

try:
    engine = sqlalchemy.create_engine(connection_string)
    with engine.connect() as conn:
        print("Connected to MySQL successfully!")
except Exception as e:
    print(f"Connection failed: {e}")
    print("\nTroubleshooting:")
    print("  1. Is MySQL running? Open MySQL Workbench and check.")
    print("  2. Is your password correct? Update MYSQL_PASSWORD above.")
    print("  3. Did you create the database? Run: CREATE DATABASE sla_analysis;")
    exit()

# ── UPLOAD MAIN TICKETS TABLE ─────────────────────────────
print("\nUploading tickets table...")
df = pd.read_csv("data/cleaned/sla_cleaned.csv")
print(f"  Loaded {len(df)} rows from cleaned CSV")

df.to_sql(
    name      = "tickets",
    con       = engine,
    if_exists = "replace",   # replaces table if it already exists
    index     = False,
    chunksize = 1000,        # upload 1000 rows at a time
)
print(f"  Uploaded {len(df)} rows to table: tickets")

# ── UPLOAD SUMMARY TABLES ─────────────────────────────────
summaries = {
    "compliance_gap":    "data/summary/compliance_gap.csv",
    "nps_by_client":     "data/summary/nps_by_client.csv",
    "monthly_trend":     "data/summary/monthly_trend.csv",
    "team_accountability":"data/summary/team_accountability.csv",
}

for table_name, filepath in summaries.items():
    try:
        summary_df = pd.read_csv(filepath)
        summary_df.to_sql(table_name, engine, if_exists="replace", index=False)
        print(f"  Uploaded {len(summary_df)} rows to table: {table_name}")
    except FileNotFoundError:
        print(f"  Skipped {table_name} (file not found — run 02_analysis.py first)")

# ── CREATE USEFUL VIEWS ───────────────────────────────────
print("\nCreating SQL views...")

views = [
    ("v_compliance_gap", """
        SELECT service_line,
               COUNT(*) AS total_tickets,
               ROUND(100 - AVG(raw_breach)*100, 1)      AS actual_compliance_pct,
               ROUND(100 - AVG(reported_breach)*100, 1) AS reported_compliance_pct,
               ROUND((100 - AVG(reported_breach)*100) - (100 - AVG(raw_breach)*100), 1) AS gap_pct,
               ROUND(SUM(reclassified) / NULLIF(SUM(raw_breach), 0) * 100, 1) AS reclass_rate_pct
        FROM tickets
        GROUP BY service_line
    """),
    ("v_nps_by_client", """
        SELECT client_id,
               ROUND(AVG(client_nps), 1) AS avg_nps,
               ROUND(AVG(reclassified)*100, 1) AS reclass_rate_pct,
               COUNT(*) AS tickets,
               CASE
                   WHEN AVG(client_nps) < 45 THEN 'AT-RISK'
                   WHEN AVG(client_nps) < 65 THEN 'WATCH'
                   ELSE 'HEALTHY'
               END AS nps_tier
        FROM tickets
        GROUP BY client_id
        ORDER BY reclass_rate_pct DESC
    """),
    ("v_monthly_trend", """
        SELECT month, service_line,
               COUNT(*) AS tickets,
               ROUND(100 - AVG(raw_breach)*100, 1)      AS actual_compliance,
               ROUND(100 - AVG(reported_breach)*100, 1) AS reported_compliance,
               ROUND(SUM(reclassified) / NULLIF(SUM(raw_breach), 0) * 100, 1) AS reclass_rate
        FROM tickets
        GROUP BY month, service_line
        ORDER BY month, service_line
    """),
    ("v_team_risk", """
        SELECT team, service_line,
               COUNT(*) AS tickets,
               ROUND(AVG(raw_breach)*100, 1)    AS breach_rate_pct,
               ROUND(AVG(reclassified)*100, 1)  AS reclass_rate_pct,
               ROUND(AVG(client_nps), 1)        AS avg_client_nps,
               CASE
                   WHEN AVG(reclassified) > 0.25 THEN 'HIGH RISK'
                   WHEN AVG(reclassified) > 0.15 THEN 'MEDIUM'
                   ELSE 'ACCEPTABLE'
               END AS risk_tier
        FROM tickets
        GROUP BY team, service_line
        ORDER BY reclass_rate_pct DESC
    """),
]

with engine.connect() as conn:
    for view_name, view_sql in views:
        try:
            conn.execute(sqlalchemy.text(f"DROP VIEW IF EXISTS {view_name}"))
            conn.execute(sqlalchemy.text(f"CREATE VIEW {view_name} AS {view_sql}"))
            conn.commit()
            print(f"  Created view: {view_name}")
        except Exception as e:
            print(f"  Could not create view {view_name}: {e}")

print("\n" + "=" * 55)
print("MySQL upload complete!")
print("=" * 55)
print("""
Open MySQL Workbench and run:
  USE sla_analysis;
  SELECT * FROM v_compliance_gap;
  SELECT * FROM v_nps_by_client LIMIT 20;
  SELECT * FROM v_team_risk;

Then run the queries in: sql/sla_queries.sql
""")
