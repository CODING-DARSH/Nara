import sqlite3

conn = sqlite3.connect("harness90.sqlite")

# FIX: the previous version LEFT JOINed recommendation_snapshots AND
# meal_log_events directly onto harness_users in one query. Since both
# are one-to-many tables (many snapshots per user, many meals per user),
# joining both at once produces a CROSS-MULTIPLIED row count -- a user
# with 22 real snapshots and 40 real meals would get 22*40=880 combined
# rows, and COUNT() over that fanned-out result counts 880 for BOTH
# columns, not the real 22 and 40 independently. That's exactly why
# meals_logged always equaled total_snapshots exactly in the previous
# output -- it was the same fan-out number both times, not two real counts.
# Fixed with independent correlated subqueries instead, so each count is
# computed against its own table only.
query = """
SELECT
    h.email,
    (SELECT COUNT(DISTINCT week_number) FROM recommendation_snapshots WHERE user_id = h.user_id) AS weeks_covered,
    (SELECT COUNT(*) FROM recommendation_snapshots WHERE user_id = h.user_id) AS total_snapshots,
    (SELECT COUNT(*) FROM meal_log_events WHERE user_id = h.user_id) AS meals_logged,
    (SELECT COUNT(*) FROM interaction_events WHERE user_id = h.user_id) AS interactions
FROM harness_users h
WHERE h.email IN (SELECT email FROM harness_completed_users)
"""

rows = conn.execute(query).fetchall()
print(f"{'email':<55} {'weeks':>6} {'snapshots':>10} {'meals':>7} {'interactions':>13}")
for email, weeks, snapshots, meals, interactions in rows:
    flag = "  <-- INCOMPLETE" if weeks != 13 or snapshots != 22 else ""
    print(f"{email:<55} {weeks:>6} {snapshots:>10} {meals:>7} {interactions:>13}{flag}")
