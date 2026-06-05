"""Validate the kit so a broken contract never reaches main. Run locally or in CI."""
import json, sys, pathlib, py_compile
import yaml
from jsonschema import Draft7Validator

ROOT = pathlib.Path(__file__).resolve().parent.parent
KIT = ROOT / "kit"
errors = []

# 1) JSON schemas are valid Draft-7 and their embedded examples validate
for name in ["project_declaration.schema.json", "data_structure.schema.json"]:
    schema = json.loads((KIT / name).read_text(encoding="utf-8"))
    try:
        Draft7Validator.check_schema(schema)
    except Exception as e:
        errors.append(f"{name}: not a valid schema -> {e}")
        continue
    v = Draft7Validator(schema)
    for i, ex in enumerate(schema.get("examples", [])):
        errs = sorted(v.iter_errors(ex), key=lambda e: e.path)
        for e in errs:
            errors.append(f"{name} example[{i}]: {list(e.path)} -> {e.message}")
    print(f"[ok] {name}: schema valid, {len(schema.get('examples', []))} example(s) checked")

# 2) Rule base loads and every rule has the required keys
rules = yaml.safe_load((KIT / "method_selection_rules.yaml").read_text(encoding="utf-8"))
for r in rules.get("rules", []):
    for key in ("id", "when", "recommend"):
        if key not in r:
            errors.append(f"rule {r.get('id','?')} missing '{key}'")
print(f"[ok] method_selection_rules.yaml: {len(rules.get('rules', []))} rules, "
      f"{len(rules.get('global_guards', []))} guards")

# 3) Python files compile
for py in list(KIT.glob("*.py")) + list((ROOT / 'examples').glob("*.py")):
    try:
        py_compile.compile(str(py), doraise=True)
        print(f"[ok] compiles: {py.relative_to(ROOT)}")
    except py_compile.PyCompileError as e:
        errors.append(f"{py.name}: {e}")

if errors:
    print("\nFAILED:")
    for e in errors:
        print("  -", e)
    sys.exit(1)
print("\nAll validations passed.")
