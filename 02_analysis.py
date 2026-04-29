# ============================================================
# FILE: 02_analysis.py
# WHAT THIS DOES: Loads the cleaned data and produces:
#   - Charts saved as PNG images
#   - Printed findings with numbers
#   - A summary CSV for Power BI
#
# HOW TO RUN: python 02_analysis.py
# (Run 01_data_cleaning.py FIRST)
# ============================================================

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
from scipy import stats
import os

# Create output folders
os.makedirs("charts", exist_ok=True)
os.makedirs("data/summary", exist_ok=True)

# Set a clean chart style
plt.style.use("seaborn-v0_8-whitegrid")
sns.set_palette("Set2")

# Colours we use throughout
COL_RED   = "#E63946"
COL_GREEN = "#2EC4B6"
COL_BLUE  = "#1A2B4A"
COL_AMBER = "#F4A261"

print("Loading cleaned data...")
df = pd.read_csv("data/cleaned/sla_cleaned.csv", parse_dates=["created_at", "resolved_at"])
print(f"Loaded {len(df)} rows")
print("=" * 55)

# ─────────────────────────────────────────────────────────────
# ANALYSIS 1: Compliance Gap by Service Line
# ─────────────────────────────────────────────────────────────
print("\n[1] Compliance gap by service line")

gap = df.groupby("service_line").agg(
    tickets         = ("ticket_id",       "count"),
    actual_pct      = ("raw_breach",      lambda x: round(100 - x.mean()*100, 1)),
    reported_pct    = ("reported_breach",  lambda x: round(100 - x.mean()*100, 1)),
    reclass_rate    = ("reclassified",     lambda x: round(x.mean()*100, 1)),
).reset_index()

gap["gap"] = (gap["reported_pct"] - gap["actual_pct"]).round(1)
print(gap.to_string(index=False))
gap.to_csv("data/summary/compliance_gap.csv", index=False)

# Chart 1: Grouped bar — actual vs reported
fig, ax = plt.subplots(figsize=(9, 5))
x = np.arange(len(gap))
w = 0.35
bars1 = ax.bar(x - w/2, gap["actual_pct"],   w, label="Actual compliance",   color=COL_RED,   alpha=0.9)
bars2 = ax.bar(x + w/2, gap["reported_pct"], w, label="Reported compliance", color=COL_GREEN, alpha=0.9)

for bar in bars1:
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
            f"{bar.get_height():.0f}%", ha="center", va="bottom", fontsize=10, fontweight="bold")
for bar in bars2:
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
            f"{bar.get_height():.0f}%", ha="center", va="bottom", fontsize=10, fontweight="bold")

ax.set_xticks(x)
ax.set_xticklabels(gap["service_line"], fontsize=11)
ax.set_ylabel("SLA Compliance %", fontsize=11)
ax.set_title("Reported vs Actual SLA Compliance — The Trust Gap", fontsize=13, fontweight="bold", pad=15)
ax.set_ylim(55, 95)
ax.legend(fontsize=10)
ax.axhline(91, color=COL_AMBER, linestyle="--", linewidth=1.2, label="Reported in Annual Report (91%)")
ax.text(2.6, 91.5, "Annual report claim: 91%", fontsize=9, color=COL_AMBER)
plt.tight_layout()
plt.savefig("charts/01_compliance_gap.png", dpi=150, bbox_inches="tight")
plt.close()
print("Saved: charts/01_compliance_gap.png")

# ─────────────────────────────────────────────────────────────
# ANALYSIS 2: NPS Correlation with Reclassification Rate
# ─────────────────────────────────────────────────────────────
print("\n[2] NPS correlation with reclassification rate")

client_data = df.groupby("client_id").agg(
    avg_nps      = ("client_nps",    "mean"),
    reclass_pct  = ("reclassified",  lambda x: round(x.mean()*100, 1)),
    tickets      = ("ticket_id",     "count"),
).reset_index()

# Pearson correlation — this is the key stat for your project
r_value, p_value = stats.pearsonr(client_data["reclass_pct"], client_data["avg_nps"])
print(f"Pearson r = {r_value:.3f}  (p-value = {p_value:.4f})")
print(f"Interpretation: {'Strong' if abs(r_value)>0.5 else 'Moderate'} "
      f"{'negative' if r_value<0 else 'positive'} correlation")

# NPS comparison: high vs low reclassification clients
high_reclass = client_data[client_data["reclass_pct"] > 25]["avg_nps"].mean()
low_reclass  = client_data[client_data["reclass_pct"] <= 25]["avg_nps"].mean()
print(f"\nAvg NPS (reclass > 25%): {high_reclass:.1f}")
print(f"Avg NPS (reclass ≤ 25%): {low_reclass:.1f}")
print(f"NPS GAP: {low_reclass - high_reclass:.1f} points")

client_data.to_csv("data/summary/nps_by_client.csv", index=False)

# Chart 2: Scatter plot with trend line
fig, ax = plt.subplots(figsize=(9, 5))

colors = [COL_RED if r > 25 else COL_GREEN for r in client_data["reclass_pct"]]
scatter = ax.scatter(
    client_data["reclass_pct"],
    client_data["avg_nps"],
    c=colors, s=70, alpha=0.75, edgecolors="white", linewidth=0.5
)

# Add trend line
m, b = np.polyfit(client_data["reclass_pct"], client_data["avg_nps"], 1)
x_line = np.linspace(client_data["reclass_pct"].min(), client_data["reclass_pct"].max(), 100)
ax.plot(x_line, m * x_line + b, color=COL_BLUE, linewidth=2, linestyle="--", label=f"Trend line (r = {r_value:.2f})")

ax.set_xlabel("Reclassification Rate (%)", fontsize=11)
ax.set_ylabel("Client NPS Score", fontsize=11)
ax.set_title(f"Higher Reclassification → Lower Client NPS  (Pearson r = {r_value:.2f})", fontsize=12, fontweight="bold")

red_patch   = mpatches.Patch(color=COL_RED,   label="High risk (reclass > 25%)")
green_patch = mpatches.Patch(color=COL_GREEN, label="Low risk (reclass ≤ 25%)")
ax.legend(handles=[red_patch, green_patch, ax.lines[0]], fontsize=9)

plt.tight_layout()
plt.savefig("charts/02_nps_correlation.png", dpi=150, bbox_inches="tight")
plt.close()
print("Saved: charts/02_nps_correlation.png")

# ─────────────────────────────────────────────────────────────
# ANALYSIS 3: Monthly Trend
# ─────────────────────────────────────────────────────────────
print("\n[3] Monthly compliance trend")

monthly = df.groupby(["month", "service_line"]).agg(
    actual_pct   = ("raw_breach",     lambda x: round(100 - x.mean()*100, 1)),
    reported_pct = ("reported_breach", lambda x: round(100 - x.mean()*100, 1)),
    reclass_rate = ("reclassified",    lambda x: round(x.mean()*100, 1)),
    tickets      = ("ticket_id",       "count"),
).reset_index()

monthly.to_csv("data/summary/monthly_trend.csv", index=False)

fig, axes = plt.subplots(1, 3, figsize=(15, 5), sharey=True)
service_lines = ["Infrastructure", "Application Support", "BPO"]
fig.suptitle("Monthly SLA Compliance Trend — Actual vs Reported", fontsize=13, fontweight="bold")

for ax, sl in zip(axes, service_lines):
    sub = monthly[monthly["service_line"] == sl].sort_values("month")
    months_short = list(sub["month"])   # show just month number
    ax.plot(months_short, sub["actual_pct"],   color=COL_RED,   marker="o", linewidth=2, label="Actual",   markersize=5)
    ax.plot(months_short, sub["reported_pct"], color=COL_GREEN, marker="s", linewidth=2, label="Reported", markersize=5, linestyle="--")
    ax.fill_between(months_short, sub["actual_pct"], sub["reported_pct"], alpha=0.15, color=COL_AMBER, label="Gap")
    ax.set_title(sl, fontsize=11, fontweight="bold")
    ax.set_xlabel("Month (2023)", fontsize=9)
    ax.tick_params(axis="x", rotation=45)
    ax.set_ylim(0, 100)
    if ax == axes[0]:
        ax.set_ylabel("SLA Compliance %", fontsize=10)
    ax.legend(fontsize=8)

plt.tight_layout()
plt.savefig("Charts/03_monthly_trend.png", dpi=150, bbox_inches="tight")
plt.close()
print("Saved: Charts/03_monthly_trend.png")

# ─────────────────────────────────────────────────────────────
# ANALYSIS 4: Team Accountability
# ─────────────────────────────────────────────────────────────
print("\n[4] Team accountability")

team_data = df.groupby(["team", "service_line"]).agg(
    tickets      = ("ticket_id",    "count"),
    breach_rate  = ("raw_breach",   lambda x: round(x.mean()*100, 1)),
    reclass_rate = ("reclassified", lambda x: round(x.mean()*100, 1)),
    avg_nps      = ("client_nps",   lambda x: round(x.mean(), 1)),
).reset_index().sort_values("reclass_rate", ascending=False)

print(team_data.to_string(index=False))
team_data.to_csv("data/summary/team_accountability.csv", index=False)

# Chart 4: Scatter — breach rate vs reclass rate per team
fig, ax = plt.subplots(figsize=(9, 6))
for _, row in team_data.iterrows():
    color = COL_RED if row["reclass_rate"] > 25 else COL_AMBER if row["reclass_rate"] > 15 else COL_GREEN
    ax.scatter(row["breach_rate"], row["reclass_rate"], s=120, color=color, zorder=5)
    ax.annotate(f"{row['team']}\n({row['service_line'][:5]})",
                (row["breach_rate"], row["reclass_rate"]),
                textcoords="offset points", xytext=(5, 5), fontsize=8)

ax.axhline(25, color=COL_RED,   linestyle="--", alpha=0.5, linewidth=1)
ax.axhline(15, color=COL_AMBER, linestyle="--", alpha=0.5, linewidth=1)
ax.text(ax.get_xlim()[1]*0.98, 25.5, "High risk threshold",   fontsize=8, color=COL_RED,   ha="right")
ax.text(ax.get_xlim()[1]*0.98, 15.5, "Medium risk threshold", fontsize=8, color=COL_AMBER, ha="right")

red_p   = mpatches.Patch(color=COL_RED,   label="High risk  (reclass > 25%)")
amb_p   = mpatches.Patch(color=COL_AMBER, label="Medium risk (reclass 15-25%)")
grn_p   = mpatches.Patch(color=COL_GREEN, label="Low risk    (reclass < 15%)")
ax.legend(handles=[red_p, amb_p, grn_p], fontsize=9)

ax.set_xlabel("Raw Breach Rate (%)", fontsize=11)
ax.set_ylabel("Reclassification Rate (%)", fontsize=11)
ax.set_title("Team Accountability — Breach Rate vs Reclassification Rate", fontsize=12, fontweight="bold")
plt.tight_layout()
plt.savefig("charts/04_team_accountability.png", dpi=150, bbox_inches="tight")
plt.close()
print("Saved: charts/04_team_accountability.png")

# ─────────────────────────────────────────────────────────────
# FINAL EXECUTIVE SUMMARY (print to screen)
# ─────────────────────────────────────────────────────────────
actual_overall   = round(100 - df["raw_breach"].mean()*100, 1)
reported_overall = round(100 - df["reported_breach"].mean()*100, 1)
infra_reclass    = round(df[df["service_line"] == "Infrastructure"]["reclassified"].mean()*100, 1)
app_reclass      = round(df[df["service_line"] == "Application Support"]["reclassified"].mean()*100, 1)
nps_gap          = round(low_reclass - high_reclass, 1)

print("\n" + "=" * 55)
print("EXECUTIVE SUMMARY — SLA TRUST DEFICIT ANALYSIS")
print("=" * 55)
print(f"  Actual SLA compliance:    {actual_overall}%")
print(f"  Reported SLA compliance:  {reported_overall}%")
print(f"  Compliance GAP:           {reported_overall - actual_overall:.1f} percentage points")
print(f"  Infrastructure reclass:   {infra_reclass}%")
print(f"  App Support reclass:      {app_reclass}%")
print(f"  NPS gap (clean vs dirty): {nps_gap} points")
print(f"  Pearson r (NPS-reclass):  {r_value:.3f}")
print("=" * 55)
print("\nAll charts saved to: charts/")
print("Summary CSVs saved to: data/summary/")
print("\nNext step: run python 03_export_to_mysql.py")
