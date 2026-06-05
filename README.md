# Data-Analysis Agent (sensory / consumer / brand / product)

An evidence-based analysis agent. You supply two input contracts — a **project declaration**
and a **data-structure descriptor** — and the agent profiles the data, recommends methods
(grounded in three sensometrics references), generates code, executes the analysis, and
reports, with two human approval gates in between.

## Repo layout

```
.
├── kit/                         # the reusable agent
│   ├── project_declaration.schema.json   # input contract #1 (WHAT/WHY)
│   ├── data_structure.schema.json        # input contract #2 (raw-data shape)
│   ├── method_selection_rules.yaml       # the brain: structure+objective -> methods
│   ├── agent_system_prompt.md            # reasoning core + the two gates + hard rules
│   ├── run_agent.py                      # orchestration skeleton
│   └── README.md                         # kit-level docs
├── examples/                    # runnable demo on SYNTHETIC data only
│   ├── simulate.py              # generates a structured yogurt dataset
│   └── analyze.py               # runs ANOVA, PCA, MFA, clustering, pref maps, penalty
├── tests/validate_kit.py        # validates schemas, examples, rules, code (run in CI)
├── .github/workflows/validate.yml
├── requirements.txt
├── .env.example                 # copy to .env (gitignored) and add your key
├── .gitignore
└── LICENSE
```

## Quick start

```bash
git clone <your-repo-url> && cd <repo>
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # then edit .env with your real ANTHROPIC_API_KEY

# run the synthetic demo end-to-end (no API key needed for the stats themselves)
cd examples && python simulate.py && python analyze.py

# drive the agent on your own contracts (needs ANTHROPIC_API_KEY)
python kit/run_agent.py --declaration project.json --structure data_structure.json
```

## Three things that must NEVER be committed

This is the part that makes the difference between "stored on GitHub" and "leaked on GitHub".
The `.gitignore` already blocks all three, but understand *why*:

1. **Secrets** — your `ANTHROPIC_API_KEY` and any credentials. Use `.env` (gitignored) locally
   and GitHub Actions encrypted secrets in CI. A key pushed to a public repo is compromised
   the moment it lands, even if you delete it later (it stays in history).
2. **Real research data** — consumer demographic/attitude data is often personal data and/or
   client-confidential. Keep it out entirely (private storage), or use a private repo plus
   anonymization, and version large files with Git LFS / DVC rather than raw commits. Only
   synthetic example data belongs here.
3. **The reference textbooks (PDFs)** — they are copyrighted. This repo *cites* them in the
   rule base; it must not store or redistribute the PDFs. `*.pdf` is gitignored for this reason.

## What this repo is and isn't

It is the input contracts, the grounded method-selection logic, the guardrailed reasoning
prompt, a runnable synthetic demo, and CI that keeps the contracts valid. It is **not** a
finished product: you still wire a code-execution sandbox (so the "never report an
un-executed number" rule holds), schema validation at runtime, state/persistence, and — if
you want R verbatim — an R + CRAN runtime. See `kit/README.md`.

Method selection is heuristic, so the agent stops at GATE 1 for human approval before running.
Rules flagged `extrapolated: true` (brand-health, 4Ps, shelf-life) apply the same math to
data the references do not demonstrate — treat them as starting points needing a domain source.

## Sources behind the rule base
- Husson, Lê & Pagès (2017), *Exploratory Multivariate Analysis by Example Using R*, 2nd ed.
- Lê & Worch (2018), *Analyzing Sensory Data with R*.
- Lawless & Heymann, *Sensory Evaluation of Food: Principles and Practices*.
