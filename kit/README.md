# Analysis Agent Kit (Level 2)

A starter kit for an agent where you supply two things — a **project declaration form**
and a **data-structure descriptor** — and the agent profiles the data, recommends methods,
generates code, executes the analysis, and reports, with two human gates in between.

## The pieces

| File | Role | You edit? |
|---|---|---|
| `project_declaration.schema.json` | Input contract #1: WHAT/WHY (objectives, data collection, governance) | Fill one per project |
| `data_structure.schema.json` | Input contract #2: the raw-data shape (columns, roles, blocks) | Fill or auto-profile, then confirm |
| `method_selection_rules.yaml` | The brain: structure + objective -> methods + R/Python + assumptions + sources | Extend over time |
| `agent_system_prompt.md` | The reasoning core, with the two gates and hard rules baked in | Tune wording |
| `run_agent.py` | Orchestration skeleton: load -> profile -> call -> gate -> execute -> gate | Wire to your stack |

## Flow

```
project_declaration.json  ─┐
data_structure.json       ─┼─> profile data ─> fire rules ─> [GATE 1] ─> generate+run ─> [GATE 2] ─> report
method_selection_rules    ─┘                                  (human)      code/exec       (human)
```

## Quick start

```bash
pip install anthropic pandas pyyaml openpyxl jsonschema
export ANTHROPIC_API_KEY=...        # never commit this
python run_agent.py --declaration project.json --structure data_structure.json --profile-only
python run_agent.py --declaration project.json --structure data_structure.json
```

## What this kit gives you vs. what you still own

Given: the input contracts, the grounded method-selection logic, the guardrailed reasoning
prompt, the profiling step, and the gate scaffolding.

You still build:
1. **Schema validation** — wire `jsonschema` so a malformed form is rejected early.
2. **A code-execution sandbox** — the hard rule "never report an un-executed number" only
   holds if the agent can actually run code. Attach a code-execution tool to the API call
   and handle the tool-use loop, or run generated code in a contained worker.
3. **R runtime (optional)** — to run the FactoMineR/SensoMineR code verbatim you need an R
   environment with CRAN access. The Python path (`prince`, `scikit-learn`, `statsmodels`)
   runs anywhere `pip` reaches.
4. **State & multi-user** — the reasoning core is stateless per call; persistence, project
   history, and concurrency are your orchestration layer.
5. **An auto-profiler -> descriptor** — optionally infer a draft `data_structure.json` from
   the file and have the human confirm at GATE 1, instead of writing it by hand.

## Honest boundaries

- Method selection is **heuristic** — GATE 1 exists so a human approves before anything runs.
- Exploratory methods (PCA/MCA/MFA/CA) describe structure; they do **not** produce classical
  p-values. For significance, the rules pair them with ANOVA / chi-square / Cochran's Q.
- Rules marked `extrapolated: true` (brand-health, 4Ps, shelf-life) apply the same math to
  data the three sensometrics sources do **not** demonstrate. Treat them as starting points
  needing a domain-specific source, not validated practice.
- The agent reads data *structure*; it cannot vouch for sampling, representativeness, or
  measurement quality. That stays with the analyst named in the declaration.

## Sources behind the rule base
- Husson, Lê & Pagès (2017), *Exploratory Multivariate Analysis by Example Using R*, 2nd ed.
- Lê & Worch (2018), *Analyzing Sensory Data with R*.
- Lawless & Heymann, *Sensory Evaluation of Food: Principles and Practices*.
