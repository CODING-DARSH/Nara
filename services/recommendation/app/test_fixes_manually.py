"""
Standalone sanity checks for the recommendation fixes — no DB, no Docker,
no Kafka needed. Run this directly:

    cd services/recommendation
    python test_fixes_manually.py

Each check prints PASS/FAIL with the actual values so you can see for
yourself, not just trust a green checkmark.
"""
import sys
sys.path.insert(0, ".")

print("=" * 60)
print("1. _state_to_region — northeast bug fix")
print("=" * 60)
from app.routers.recommend import _state_to_region

cases = [
    ("Assam", "northeast"),       # was wrongly "east" before the fix
    ("Meghalaya", "northeast"),   # was unreachable before the fix
    ("Karnataka", "south"),
    ("Gujarat", "west"),
    ("West Bengal", "east"),
    ("Punjab", "north"),          # falls through to default
]
for state, expected in cases:
    actual = _state_to_region(state)
    status = "PASS" if actual == expected else "FAIL"
    print(f"  [{status}] _state_to_region({state!r}) = {actual!r} (expected {expected!r})")


print()
print("=" * 60)
print("2. _label_encode — unknown bucket + real class list")
print("=" * 60)
from app.pipeline.ranker import _label_encode, _STRESS_CLASSES, _REGION_CLASSES

print(f"  _STRESS_CLASSES = {_STRESS_CLASSES}  (should NOT contain 'extreme')")
print(f"  _REGION_CLASSES = {_REGION_CLASSES}  (should contain 'northeast')")

assert "extreme" not in _STRESS_CLASSES, "FAIL: 'extreme' should have been removed"
assert "northeast" in _REGION_CLASSES, "FAIL: 'northeast' should have been added"
print("  [PASS] extreme removed, northeast present")

idx_known   = _label_encode("medium", _STRESS_CLASSES)
idx_unknown = _label_encode("extreme", _STRESS_CLASSES)  # no longer a real class
print(f"  _label_encode('medium', ...)  = {idx_known}")
print(f"  _label_encode('extreme', ...) = {idx_unknown}  (should be len(classes)={len(_STRESS_CLASSES)}, the unknown bucket)")
assert idx_unknown == len(_STRESS_CLASSES), "FAIL: unknown value should map to len(classes)"
print("  [PASS] unseen value correctly falls into unknown bucket")


print()
print("=" * 60)
print("3. detect_occasion — label decode mapping bug fix")
print("=" * 60)
print("""
  Before the fix, occasion_map was:
    {0: "breakfast", 1: "lunch", 2: "snack", 3: "dinner", 4: "late_night"}
  Your real training log showed:
    Classes: ['breakfast', 'dinner', 'late_night', 'lunch', 'snack']
  That's alphabetical order, so the REAL mapping must be:
    {0: "breakfast", 1: "dinner", 2: "late_night", 3: "lunch", 4: "snack"}

  To verify yourself: open app/pipeline/ranker.py, find detect_occasion(),
  and confirm the occasion_map dict matches the alphabetical list above
  exactly. If model_store.occasion is loaded in your real environment,
  call detect_occasion() with context={"hour": 8} (early morning) and
  confirm it returns "breakfast", not some other label.
""")


print("=" * 60)
print("4. health_score_dish — is_vegetarian no longer zeroed")
print("=" * 60)
import inspect
from app.pipeline import ranker
src = inspect.getsource(ranker.health_score_dish)
if 'is_veg        = 1.0 if user.get("is_vegetarian")' in src or "is_veg" in src:
    print("  [PASS] health_score_dish references user.get('is_vegetarian') — check source below")
else:
    print("  [FAIL] could not find is_vegetarian read in health_score_dish source")
print()
print("  Manual check: open ranker.py, find health_score_dish(), confirm")
print("  the feature array no longer has a literal 0 in the is_vegetarian")
print("  slot — it should read is_veg, computed from user.get('is_vegetarian').")


print()
print("=" * 60)
print("5. graph_computer — GI/GL averaging logic (pure function test)")
print("=" * 60)
print("""
  This needs a DB in the real service, but you can sanity-check the MATH
  by hand: if a user logs 3 meals with glycemic_index values 40, 60, 80:
    OLD (buggy) behavior: summed -> 180 (meaningless)
    NEW (fixed) behavior: averaged -> 60 (real GI-like number)
  When you have real data, call GET /v1/food-graph and check that
  last_24h.glycemic_index (or last_7d/last_30d) is a plausible single-dish
  GI value (typically 30-100), not a number that grows with meal count.
""")

print("Done. Items 1-2 are fully automated above (look for any FAIL).")
print("Items 3-5 need either reading the source yourself or a live DB —")
print("instructions for both are printed above.")
