"""
run_agent.py — orchestration skeleton for the Level-2 analysis agent.

This is a SKELETON, not a finished product. It shows the wiring you own:
loading the two input contracts, profiling the real data, calling Claude as the
reasoning core, and enforcing the two human gates. Replace the TODOs with your
stack (queue, persistence, auth, a sandbox for executing generated code).

Run:  python run_agent.py --declaration project.json --structure data_structure.json
Env:  ANTHROPIC_API_KEY must be set in the environment (never hard-code it).

Deps: pip install anthropic pandas pyyaml openpyxl
"""

from __future__ import annotations
import argparse, json, os, sys
from pathlib import Path

import pandas as pd
import yaml

try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None  # allows profiling/dry-run without the SDK

KIT = Path(__file__).parent
MODEL = "claude-opus-4-8"  # pick the model you want the agent to run on


# ---------------------------------------------------------------------------
# 1. Load the two input contracts + the rule base
# ---------------------------------------------------------------------------
def load_contracts(declaration_path: str, structure_path: str):
    declaration = json.loads(Path(declaration_path).read_text(encoding="utf-8"))
    structure = json.loads(Path(structure_path).read_text(encoding="utf-8"))
    rules = yaml.safe_load((KIT / "method_selection_rules.yaml").read_text(encoding="utf-8"))
    system_prompt = (KIT / "agent_system_prompt.md").read_text(encoding="utf-8")
    # TODO: validate against the JSON schemas (e.g. jsonschema.validate) before proceeding.
    return declaration, structure, rules, system_prompt


# ---------------------------------------------------------------------------
# 2. Profile the REAL data file -> ground truth the agent reconciles against
# ---------------------------------------------------------------------------
def profile_data(structure: dict) -> dict:
    f = structure["file"]
    fmt = f.get("format", "csv")
    if fmt in ("csv", "tsv"):
        df = pd.read_csv(f["path"], sep=f.get("sep", ";"), decimal=f.get("decimal", "."),
                         encoding=f.get("encoding", "utf-8"))
    elif fmt == "xlsx":
        df = pd.read_excel(f["path"])
    elif fmt == "parquet":
        df = pd.read_parquet(f["path"])
    else:
        raise ValueError(f"Unsupported format: {fmt}")

    profile = {
        "n_rows": int(len(df)),
        "n_cols": int(df.shape[1]),
        "columns": [],
    }
    for col in df.columns:
        s = df[col]
        info = {
            "name": str(col),
            "pandas_dtype": str(s.dtype),
            "n_missing": int(s.isna().sum()),
            "n_unique": int(s.nunique(dropna=True)),
        }
        if pd.api.types.is_numeric_dtype(s):
            info["min"] = float(s.min()) if s.notna().any() else None
            info["max"] = float(s.max()) if s.notna().any() else None
        else:
            info["sample_levels"] = [str(x) for x in s.dropna().unique()[:8]]
        profile["columns"].append(info)
    return profile


# ---------------------------------------------------------------------------
# 3. Call Claude (the reasoning core) with everything it needs
# ---------------------------------------------------------------------------
def call_agent(system_prompt: str, payload: dict, conversation: list | None = None):
    if Anthropic is None:
        raise RuntimeError("anthropic SDK not installed; run pip install anthropic")
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    messages = conversation or []
    messages.append({"role": "user", "content": json.dumps(payload, ensure_ascii=False)})

    resp = client.messages.create(
        model=MODEL,
        max_tokens=4000,
        system=system_prompt,
        messages=messages,
        # To let the agent EXECUTE generated analysis code, attach a code-execution
        # tool here and handle tool_use/tool_result in a loop. The hard rule
        # "never report a number you did not execute" depends on this being wired up.
        # TODO: tools=[code_execution_tool], then run the tool-use loop.
    )
    text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
    messages.append({"role": "assistant", "content": text})
    return text, messages


def human_gate(label: str, agent_text: str) -> bool:
    """Blocking human checkpoint. Replace with your UI/approval flow."""
    print("\n" + "=" * 70)
    print(f"[{label}]")
    print(agent_text)
    print("=" * 70)
    ans = input(f"Approve {label}? [y/N] ").strip().lower()
    return ans == "y"


# ---------------------------------------------------------------------------
# Main flow with the two gates
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--declaration", required=True)
    ap.add_argument("--structure", required=True)
    ap.add_argument("--profile-only", action="store_true", help="Just profile the data and exit.")
    args = ap.parse_args()

    declaration, structure, rules, system_prompt = load_contracts(args.declaration, args.structure)
    profile = profile_data(structure)
    print(json.dumps(profile, indent=2, ensure_ascii=False))
    if args.profile_only:
        return

    base_payload = {
        "project_declaration": declaration,
        "data_structure": structure,
        "method_selection_rules": rules,
        "data_profile": profile,
    }

    # GATE 1 — method approval
    gate1_text, convo = call_agent(
        system_prompt,
        {**base_payload, "instruction": "Run pipeline steps 1-3. Stop at GATE 1 (method approval)."},
    )
    if not human_gate("GATE 1 — method approval", gate1_text):
        print("Stopped at GATE 1.")
        return

    # Steps 4-6 — generate, execute (needs the code-exec tool wired), interpret
    gate2_text, convo = call_agent(
        system_prompt,
        {"instruction": "Methods approved. Run steps 4-6, execute the analysis, stop at GATE 2."},
        conversation=convo,
    )

    # GATE 2 — conclusion sign-off
    if not human_gate("GATE 2 — conclusion sign-off", gate2_text):
        print("Sent back for revision at GATE 2.")
        return
    print("\nSigned off. Persist the report here.")  # TODO: persistence/export


if __name__ == "__main__":
    sys.exit(main())
