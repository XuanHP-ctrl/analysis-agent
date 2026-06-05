"""
run_agent.py — analysis agent with a real, gated code-execution loop.

Design choices (deliberate):
- CLIENT-SIDE execution: generated analysis code runs on THIS machine, so your data
  never leaves it. (The alternative — Anthropic's server-side `code_execution` tool —
  is simpler but uploads data to Anthropic's sandbox; not used here on purpose.)
- The two human gates are enforced STRUCTURALLY, not by trusting the prompt:
    * Phase 1 calls the model WITHOUT the run_python tool, so it physically cannot
      execute anything before GATE 1 approval.
    * Phase 2 attaches run_python only after the human approves at GATE 1.
- The "never report an un-executed number" rule therefore holds: numbers can only come
  from run_python output, which is real subprocess output.

SECURITY: the sandbox below is a minimal subprocess with a timeout. Generated code is
still code. For anything beyond a trusted local demo, run it in a hardened sandbox
(Docker with `--network none`, CPU/memory limits, a non-root user, read-only mounts).
See harden_executor().

Run:
  python kit/run_agent.py --declaration examples/project.json --structure examples/data_structure.json
  python kit/run_agent.py ... --profile-only      # no API key needed
Env:
  ANTHROPIC_API_KEY  (required unless --profile-only)
  AGENT_MODEL        (optional, default claude-opus-4-8)
Deps: pip install anthropic pandas pyyaml openpyxl
"""

from __future__ import annotations
import argparse, json, os, subprocess, sys, tempfile
from pathlib import Path

import pandas as pd
import yaml

try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None

KIT = Path(__file__).resolve().parent
ROOT = KIT.parent
MODEL = os.environ.get("AGENT_MODEL", "claude-opus-4-8")
MAX_TOOL_ITERS = 25          # hard cap so the loop can't run away
EXEC_TIMEOUT_S = 120         # per code block


# ---------------------------------------------------------------------------
# Contracts + data profile
# ---------------------------------------------------------------------------
def load_contracts(declaration_path, structure_path):
    declaration = json.loads(Path(declaration_path).read_text(encoding="utf-8"))
    structure = json.loads(Path(structure_path).read_text(encoding="utf-8"))
    rules = yaml.safe_load((KIT / "method_selection_rules.yaml").read_text(encoding="utf-8"))
    system_prompt = (KIT / "agent_system_prompt.md").read_text(encoding="utf-8")
    return declaration, structure, rules, system_prompt


def profile_data(structure, base=ROOT):
    f = structure["file"]; fmt = f.get("format", "csv")
    path = (base / f["path"]) if not os.path.isabs(f["path"]) else Path(f["path"])
    if fmt in ("csv", "tsv"):
        df = pd.read_csv(path, sep=f.get("sep", ";"), decimal=f.get("decimal", "."),
                         encoding=f.get("encoding", "utf-8"))
    elif fmt == "xlsx":
        df = pd.read_excel(path)
    elif fmt == "parquet":
        df = pd.read_parquet(path)
    else:
        raise ValueError(f"Unsupported format: {fmt}")
    prof = {"path": str(path), "n_rows": int(len(df)), "n_cols": int(df.shape[1]), "columns": []}
    for c in df.columns:
        s = df[c]; info = {"name": str(c), "dtype": str(s.dtype),
                           "n_missing": int(s.isna().sum()), "n_unique": int(s.nunique(dropna=True))}
        if pd.api.types.is_numeric_dtype(s) and s.notna().any():
            info["min"], info["max"] = float(s.min()), float(s.max())
        else:
            info["sample_levels"] = [str(x) for x in s.dropna().unique()[:8]]
        prof["columns"].append(info)
    return prof


# ---------------------------------------------------------------------------
# The client-side code-execution tool
# ---------------------------------------------------------------------------
RUN_PYTHON_TOOL = {
    "name": "run_python",
    "description": (
        "Execute a self-contained Python script in the project working directory and "
        "return its stdout/stderr. Use this to actually run every analysis; never report "
        "a numeric result you have not obtained from this tool. Data files are reachable by "
        "the relative paths given in the data profile. matplotlib uses the 'Agg' backend; "
        "save figures to files rather than calling show()."
    ),
    "input_schema": {
        "type": "object",
        "properties": {"code": {"type": "string", "description": "Python source to execute."}},
        "required": ["code"],
    },
}


def execute_python(code: str, workdir: Path) -> str:
    """Minimal local sandbox: run code in a subprocess with a timeout, capture output.

    HARDENING (do before any non-trusted use): replace this body with a call into a
    Docker container started with `--network none`, `--memory`, `--cpus`, a non-root
    user, and a read-only bind mount of the data directory. See harden_executor().
    """
    with tempfile.NamedTemporaryFile("w", suffix=".py", dir=workdir, delete=False) as tf:
        tf.write(code); script = tf.name
    try:
        p = subprocess.run([sys.executable, script], cwd=str(workdir),
                           capture_output=True, text=True, timeout=EXEC_TIMEOUT_S)
        out = (p.stdout or "")[-12000:]
        err = (p.stderr or "")[-4000:]
        return f"[exit {p.returncode}]\nSTDOUT:\n{out}" + (f"\nSTDERR:\n{err}" if err else "")
    except subprocess.TimeoutExpired:
        return f"[timeout after {EXEC_TIMEOUT_S}s] - the script ran too long."
    finally:
        try:
            os.unlink(script)
        except OSError:
            pass


def harden_executor():
    """Notes only. Example Docker invocation for untrusted code:
       docker run --rm --network none --memory 1g --cpus 1 --user 1000:1000 \
         -v "$DATA_DIR":/data:ro -v "$WORK":/work -w /work python:3.12-slim \
         python /work/script.py
    """
    raise NotImplementedError


# ---------------------------------------------------------------------------
# Model calls + the gated loop
# ---------------------------------------------------------------------------
def _client():
    if Anthropic is None:
        raise RuntimeError("anthropic SDK not installed; run: pip install anthropic")
    return Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


def _text(blocks):
    return "".join(b.text for b in blocks if getattr(b, "type", None) == "text")


def call_once(client, system, messages, tools=None):
    """Single model turn. No tools -> cannot execute (used pre-gate)."""
    resp = client.messages.create(model=MODEL, max_tokens=4000, system=system,
                                  messages=messages, tools=tools or [])
    messages.append({"role": "assistant", "content": resp.content})
    return resp, messages


def run_tool_loop(client, system, messages, workdir):
    """Phase 2: run_python is attached; drive tool_use -> execute -> tool_result."""
    tools = [RUN_PYTHON_TOOL]
    resp, messages = call_once(client, system, messages, tools)
    iters = 0
    while resp.stop_reason == "tool_use" and iters < MAX_TOOL_ITERS:
        iters += 1
        results = []
        for block in resp.content:
            if getattr(block, "type", None) == "tool_use" and block.name == "run_python":
                print(f"\n--- run_python (iter {iters}) ---")
                code = block.input.get("code", "")
                output = execute_python(code, workdir)
                print(output[:1500])
                results.append({"type": "tool_result", "tool_use_id": block.id, "content": output})
        if not results:
            break
        messages.append({"role": "user", "content": results})
        resp, messages = call_once(client, system, messages, tools)
    if iters >= MAX_TOOL_ITERS:
        print(f"\n[stopped: hit MAX_TOOL_ITERS={MAX_TOOL_ITERS}]")
    return _text(resp.content), messages


def human_gate(label, text):
    print("\n" + "=" * 72 + f"\n[{label}]\n" + text + "\n" + "=" * 72)
    return input(f"Approve {label}? [y/N] ").strip().lower() == "y"


# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--declaration", required=True)
    ap.add_argument("--structure", required=True)
    ap.add_argument("--workdir", default=str(ROOT), help="cwd for executed code (data read relative to this).")
    ap.add_argument("--profile-only", action="store_true")
    args = ap.parse_args()

    declaration, structure, rules, system = load_contracts(args.declaration, args.structure)
    profile = profile_data(structure)
    print(json.dumps(profile, indent=2, ensure_ascii=False))
    if args.profile_only:
        return

    workdir = Path(args.workdir).resolve()
    client = _client()
    payload = {"project_declaration": declaration, "data_structure": structure,
               "method_selection_rules": rules, "data_profile": profile}

    # PHASE 1 - no tools attached => execution is impossible before approval
    messages = [{"role": "user", "content": json.dumps(payload, ensure_ascii=False) +
                 "\n\nDo pipeline steps 1-3. Reconcile the structure with the profile, fire the "
                 "rules, and present the candidate methods as a table (method | why it fired | "
                 "key assumptions | source | extrapolated?). STOP at GATE 1; do not propose code yet."}]
    gate1, messages = call_once(client, system, messages)   # tools omitted on purpose
    if not human_gate("GATE 1 - method approval", _text(gate1.content)):
        print("Stopped at GATE 1."); return

    # PHASE 2 - attach run_python; the agent generates AND executes code, then interprets
    messages.append({"role": "user", "content":
                     "Methods approved. Now run steps 4-6: for each approved method generate a "
                     "self-contained Python script, EXECUTE it with run_python, check the listed "
                     "assumptions, and report only executed results. Stop at GATE 2 with: what was "
                     "run | key results | assumptions status | caveats | conditional recommendation."})
    gate2, messages = run_tool_loop(client, system, messages, workdir)
    if not human_gate("GATE 2 - conclusion sign-off", gate2):
        print("Sent back for revision at GATE 2."); return
    print("\nSigned off.")   # TODO: persist/export the report


if __name__ == "__main__":
    sys.exit(main())
