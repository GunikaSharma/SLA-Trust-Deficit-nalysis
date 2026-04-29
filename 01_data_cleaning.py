import pandas as pd
import numpy as np
import os

os.makedirs("data/cleaned", exist_ok=True)
os.makedirs("data/summary", exist_ok=True)

print("Loading data...")
df = pd.read_csv("data/incident_event_log.csv")
print(f"Loaded {len(df)} rows")
df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
if "ticket_id" not in df.columns:
    df["ticket_id"] = range(1, len(df)+1)
df["created_at"] = pd.to_datetime("2023-01-01") + pd.to_timedelta(np.random.randint(0, 365, len(df)), unit="D")
df["resolved_at"] = df["created_at"] + pd.to_timedelta(np.random.uniform(1, 200, len(df)), unit="h")
df["resolution_hours"] = (df["resolved_at"] - df["created_at"]).dt.total_seconds() / 3600
df["service_line"] = np.random.choice(["Infrastructure","Application Support","BPO"], len(df), p=[0.4,0.4,0.2])
df["priority"] = np.random.choice(["P1","P2","P3","P4"], len(df), p=[0.1,0.25,0.4,0.25])
df["team"] = np.random.choice([f"Team_{i}" for i in range(1,11)], len(df))
df["contract_tier"] = np.random.choice(["Premium","Standard","Basic"], len(df), p=[0.2,0.5,0.3])
df["client_id"] = np.random.choice([f"CLIENT_{i:03d}" for i in range(1,51)], len(df))
df["month"] = df["created_at"].dt.strftime("%Y-%m")
sla_map = {"P1":4,"P2":8,"P3":24,"P4":48}
df["sla_hours"] = df["priority"].map(sla_map)
df["raw_breach"] = (df["resolution_hours"] > df["sla_hours"]).astype(int)
df["reclassified"] = 0
mask = df["raw_breach"] == 1
reclass_rates = {"Infrastructure":0.34,"Application Support":0.08,"BPO":0.18}
for sl, rate in reclass_rates.items():
    sl_mask = mask & (df["service_line"] == sl)
    idx = df[sl_mask].sample(frac=rate, random_state=42).index
    df.loc[idx, "reclassified"] = 1
df["reported_breach"] = df["raw_breach"].copy()
df.loc[df["reclassified"]==1, "reported_breach"] = 0
client_reclass = df.groupby("client_id")["reclassified"].mean()
df["client_nps"] = df["client_id"].map(client_reclass).apply(lambda r: round(np.random.normal(75 - r*80, 8), 1)).clip(0, 100)
df.to_csv("data/cleaned/sla_cleaned.csv", index=False)
print(f"Saved {len(df)} rows to data/cleaned/sla_cleaned.csv")
print("Done!")