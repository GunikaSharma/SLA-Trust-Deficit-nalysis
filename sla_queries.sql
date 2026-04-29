-- ============================================================
-- FILE: sla_queries.sql
-- HOW TO USE:
--   1. Open MySQL Workbench
--   2. Click File → Open SQL Script → select this file
--   3. Run each query one at a time (highlight it, press Ctrl+Enter)
--   4. Take a screenshot of each result for your GitHub README
-- ============================================================

USE sla_analysis;

-- ============================================================
-- QUERY 1: Health check — make sure data loaded correctly
-- Run this first to verify everything uploaded OK
-- ============================================================
SELECT
    COUNT(*)                                     AS total_tickets,
    MIN(created_at)                              AS earliest_ticket,
    MAX(created_at)                              AS latest_ticket,
    ROUND(AVG(raw_breach) * 100, 1)             AS breach_rate_pct,
    ROUND(AVG(reclassified) * 100, 1)           AS reclass_rate_pct,
    ROUND(AVG(client_nps), 1)                   AS avg_nps
FROM tickets;

-- ============================================================
-- QUERY 2: THE KEY FINDING — Compliance gap by service line
-- This is the most important query in your project.
-- It shows the gap between what was reported vs what really happened.
-- ============================================================
SELECT
    service_line,
    COUNT(*)                                                          AS total_tickets,
    ROUND(100 - AVG(raw_breach) * 100, 1)                           AS actual_compliance_pct,
    ROUND(100 - AVG(reported_breach) * 100, 1)                      AS reported_compliance_pct,
    ROUND(
        (100 - AVG(reported_breach)*100) - (100 - AVG(raw_breach)*100)
    , 1)                                                              AS gap_points,
    ROUND(SUM(reclassified) / NULLIF(SUM(raw_breach), 0) * 100, 1) AS reclass_rate_pct
FROM tickets
GROUP BY service_line
ORDER BY reclass_rate_pct DESC;

-- ============================================================
-- QUERY 3: Reclassification timing — the forensics
-- Shows HOW CLOSE to the SLA deadline reclassifications happen.
-- Infrastructure gets reclassified right before the window closes.
-- ============================================================
SELECT
    service_line,
    priority,
    COUNT(*)                                                               AS breach_tickets,
    SUM(reclassified)                                                      AS reclassified_count,
    ROUND(SUM(reclassified) / NULLIF(COUNT(*), 0) * 100, 1)              AS reclass_rate_pct,
    ROUND(AVG(resolution_hours), 1)                                        AS avg_resolution_hours,
    ROUND(AVG(sla_hours), 1)                                               AS avg_sla_hours,
    ROUND(AVG(resolution_hours / NULLIF(sla_hours, 0)) * 100, 1)         AS avg_pct_of_sla_used
FROM tickets
WHERE raw_breach = 1
GROUP BY service_line, priority
ORDER BY reclass_rate_pct DESC;

-- ============================================================
-- QUERY 4: NPS score by reclassification behaviour
-- Clients whose tickets get reclassified more → lower NPS
-- ============================================================
SELECT
    client_id,
    ROUND(AVG(client_nps), 1)                   AS avg_nps,
    ROUND(AVG(reclassified) * 100, 1)           AS reclass_rate_pct,
    COUNT(*)                                     AS total_tickets,
    CASE
        WHEN AVG(client_nps) < 45  THEN 'AT-RISK  (NPS < 45)'
        WHEN AVG(client_nps) < 65  THEN 'WATCH    (NPS 45-65)'
        ELSE                             'HEALTHY  (NPS > 65)'
    END AS nps_tier
FROM tickets
GROUP BY client_id
ORDER BY reclass_rate_pct DESC
LIMIT 20;

-- ============================================================
-- QUERY 5: Team accountability — who is doing the reclassifying?
-- Risk tiers: HIGH (>25%), MEDIUM (15-25%), ACCEPTABLE (<15%)
-- ============================================================
SELECT
    team,
    service_line,
    COUNT(*)                                        AS total_tickets,
    ROUND(AVG(raw_breach) * 100, 1)               AS breach_rate_pct,
    ROUND(AVG(reclassified) * 100, 1)             AS reclass_rate_pct,
    ROUND(AVG(client_nps), 1)                     AS avg_client_nps,
    CASE
        WHEN AVG(reclassified) > 0.25 THEN 'HIGH RISK'
        WHEN AVG(reclassified) > 0.15 THEN 'MEDIUM'
        ELSE                               'ACCEPTABLE'
    END AS risk_tier
FROM tickets
GROUP BY team, service_line
ORDER BY reclass_rate_pct DESC;

-- ============================================================
-- QUERY 6: Monthly trend — 12 months of data
-- You can paste this output into Power BI or Excel for a line chart
-- ============================================================
SELECT
    month,
    service_line,
    COUNT(*)                                                         AS tickets,
    ROUND(100 - AVG(raw_breach) * 100, 1)                          AS actual_compliance,
    ROUND(100 - AVG(reported_breach) * 100, 1)                     AS reported_compliance,
    ROUND(SUM(reclassified) / NULLIF(SUM(raw_breach), 0) * 100, 1) AS reclass_rate
FROM tickets
GROUP BY month, service_line
ORDER BY month, service_line;

-- ============================================================
-- QUERY 7: Contract tier analysis
-- Are Premium clients getting better service? Or are they
-- also getting reclassified to hide breaches?
-- ============================================================
SELECT
    contract_tier,
    COUNT(*)                                        AS tickets,
    ROUND(100 - AVG(raw_breach) * 100, 1)         AS actual_compliance_pct,
    ROUND(100 - AVG(reported_breach) * 100, 1)    AS reported_compliance_pct,
    ROUND(AVG(reclassified) * 100, 1)             AS reclass_rate_pct,
    ROUND(AVG(client_nps), 1)                     AS avg_nps
FROM tickets
GROUP BY contract_tier
ORDER BY FIELD(contract_tier, 'Premium', 'Standard', 'Basic');

-- ============================================================
-- QUERY 8: Priority breakdown
-- P1 = Critical (4hr SLA). Are the most urgent tickets
-- being reclassified more?
-- ============================================================
SELECT
    priority,
    sla_hours,
    COUNT(*)                                        AS total_tickets,
    SUM(raw_breach)                                AS raw_breaches,
    SUM(reclassified)                              AS reclassified,
    ROUND(AVG(raw_breach) * 100, 1)               AS breach_rate_pct,
    ROUND(AVG(reclassified) * 100, 1)             AS reclass_rate_pct,
    ROUND(AVG(resolution_hours), 1)               AS avg_resolution_hours
FROM tickets
GROUP BY priority, sla_hours
ORDER BY sla_hours;

-- ============================================================
-- QUERY 9: NPS gap — compare clean vs dirty reporting clients
-- The headline number: clients with high reclass rate
-- have NPS scores X points lower
-- ============================================================
SELECT
    CASE
        WHEN reclassify_rate > 25 THEN 'High reclass (>25%)'
        WHEN reclassify_rate > 10 THEN 'Medium reclass (10-25%)'
        ELSE                           'Low reclass (<10%)'
    END AS client_group,
    COUNT(*)                     AS num_clients,
    ROUND(AVG(avg_nps), 1)      AS avg_nps_score,
    ROUND(AVG(reclassify_rate), 1) AS avg_reclass_rate
FROM (
    SELECT
        client_id,
        AVG(client_nps)          AS avg_nps,
        AVG(reclassified) * 100  AS reclassify_rate
    FROM tickets
    GROUP BY client_id
) AS client_summary
GROUP BY client_group
ORDER BY avg_nps_score DESC;

-- ============================================================
-- QUERY 10: CHAIN OF EVIDENCE — full audit trail CTE
-- This is the most impressive query: it uses WITH (CTE) syntax
-- to build a complete audit chain from raw data to findings.
-- Perfect for your GitHub portfolio — shows advanced SQL.
-- ============================================================
WITH raw_stats AS (
    -- Step 1: Calculate raw stats per service line
    SELECT
        service_line,
        COUNT(*)                                   AS total_tickets,
        SUM(raw_breach)                            AS raw_breaches,
        SUM(reclassified)                          AS reclassified_count,
        SUM(reported_breach)                       AS reported_breaches
    FROM tickets
    GROUP BY service_line
),
compliance_calc AS (
    -- Step 2: Calculate compliance percentages
    SELECT
        *,
        ROUND((1 - raw_breaches / total_tickets) * 100, 1)      AS actual_compliance,
        ROUND((1 - reported_breaches / total_tickets) * 100, 1) AS reported_compliance,
        ROUND(reclassified_count / NULLIF(raw_breaches, 0) * 100, 1) AS reclass_rate
    FROM raw_stats
),
nps_stats AS (
    -- Step 3: Get NPS by service line
    SELECT service_line, ROUND(AVG(client_nps), 1) AS avg_nps
    FROM tickets
    GROUP BY service_line
)
-- Step 4: Join everything together for the final report
SELECT
    c.service_line,
    c.total_tickets,
    c.actual_compliance   AS actual_compliance_pct,
    c.reported_compliance AS reported_compliance_pct,
    ROUND(c.reported_compliance - c.actual_compliance, 1) AS gap_points,
    c.reclass_rate        AS reclass_rate_pct,
    n.avg_nps,
    CASE
        WHEN c.reclass_rate > 25 THEN 'HIGH RISK — Immediate audit needed'
        WHEN c.reclass_rate > 15 THEN 'MEDIUM RISK — Monitor closely'
        ELSE                          'LOW RISK — Acceptable levels'
    END AS audit_recommendation
FROM compliance_calc c
JOIN nps_stats n ON c.service_line = n.service_line
ORDER BY c.reclass_rate DESC;
