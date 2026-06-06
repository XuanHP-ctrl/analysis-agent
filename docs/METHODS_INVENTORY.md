# Methods inventory, gaps & extensibility

Sources: **HLP** = Husson, Lê & Pagès (2017) *Exploratory Multivariate Analysis by Example Using R*;
**LW** = Lê & Worch (2018) *Analyzing Sensory Data with R*; **LH** = Lawless & Heymann *Sensory Evaluation of Food*;
**Rmd** = your merged_all_chapters.Rmd (working R notebook compiling the above).

---

## A. What we already have (grounded in the sources)

### A1. Difference / discrimination testing
- Triangle, duo-trio, tetrad, 2-AFC, 3-AFC, paired comparison, same-different, A-not-A — **LH ch5**, **LW ch5** (`sensR`: `discrim`, `rescale`, `d.primePwr`).
- Thurstonian models, d-prime (δ), signal detection, R-index, ROC — **LH ch5**.
- Similarity / equivalence testing, power & sample-size tables — **LH ch5**.
- Bradley–Terry model — **LW ch5**.

### A2. Thresholds & scaling
- Detection / recognition thresholds (ASTM E-679, best-estimate threshold) — **LH ch6**.
- Category, line, magnitude estimation, labeled magnitude scales — **LH ch7**.

### A3. Descriptive analysis & panel
- QDA, Flavor Profile, Texture Profile, Spectrum, free-choice profiling — **LH ch10**.
- ANOVA (product / panelist / session / interaction), panel performance — **LW ch1** (`decat`, `paneliperf`), **LH**.
- Confidence ellipses (real & virtual panels) — **LW**.

### A4. Temporal methods
- Time–Intensity (TI), Temporal Dominance of Sensations (TDS) — **LH ch8**; analysis of dominance curves, binomial significance.

### A5. Rapid / holistic methods
- Word association, free sorting, Napping, sorted Napping (`fasnt`), Flash profile — **LW ch4, ch6, ch7**.

### A6. Multivariate engine (domain-agnostic)
- PCA, CA, MCA — **HLP ch1–3**, **LW ch2,4,6**.
- MFA, Hierarchical MFA (HMFA), MFA for contingency tables — **HLP**, **LW ch3,4,7**.
- Canonical Variate Analysis (CVA), GPA, MDS — **LH ch18**, **LW**.
- Clustering: hierarchical (HAC), k-means, **HCPC** (PC + clustering) — **HLP**, **LW ch8**.
- Supplementary variables/individuals; dimension & cluster description (`catdes`, `condes`, `dimdesc`) — **HLP**.

### A7. Affective & optimization
- Hedonic / acceptance / preference tests, 9-point hedonic — **LH ch13–14**.
- Internal preference mapping (MDPref); external preference mapping (PREFMAP), `carto` — **LH ch18**, **LW ch9**.
- Drivers of (dis)liking; PLS / PCR regression — **LW ch9**.
- Penalty analysis (JAR); Ideal Profile Method, IdMap, `ConsistencyIdeal` — **LW ch10**, **LH 14.5**.
- PLS path modelling (physicochemical → sensory → hedonic) — Pagès & Tenenhaus (2001), in **LW ch9** readings.

---

## B. Gaps — what to add for a *complete* market + marketing + behavioral platform

Two kinds of gap. **[RULE]** = the method is reachable with libraries we already use; just add a rule
(+ a code template). **[SOURCE]** = not covered by the three books; needs a dedicated reference before
the agent should recommend it responsibly.

### B1. Inferential depth
- Mixed-effects models (random panelist/consumer effects, `lmer`) — **[RULE]** (statsmodels/pymer). The books mostly use fixed-effect ANOVA.
- Generalized linear models: logistic, **ordinal logistic** (proper for Likert/JAR), Poisson, beta regression — **[RULE]**.
- Multiple-testing control, effect sizes, power analysis as a general layer (we applied BH by hand) — **[RULE]**.
- Bayesian estimation / credible intervals — **[SOURCE]**.

### B2. Marketing research (largely absent from the sources)
- Conjoint analysis / Discrete Choice Experiments (choice-based conjoint) — **[SOURCE]**.
- MaxDiff (best–worst scaling) — **[SOURCE]**.
- Price sensitivity: Van Westendorp, Gabor–Granger — **[SOURCE]**.
- TURF (reach & frequency) — **[SOURCE]**.
- Key-driver analysis: Shapley/relative-weights regression, Kano model — **[SOURCE]**.
- Brand-health / brand-equity KPIs, NPS driver analysis — **[SOURCE]**.

### B3. Behavioral / psychometric
- Implicit measures: IAT d-score scoring & interpretation (we hit this with the fish-sauce data) — **[SOURCE]**.
- Structural Equation Modelling (CB-SEM) and a full PLS-PM treatment — **[SOURCE]**.
- Scale validation: Cronbach's alpha, EFA/CFA, Item Response Theory — **[SOURCE]**.

### B4. Modern / scale
- Machine learning for driver importance & prediction (random forest, gradient boosting) — **[RULE]** (scikit-learn).
- Text analytics / NLP beyond CA: topic modelling, sentiment, embeddings (for open-ends at scale) — **[SOURCE]** (+ libraries).
- Survival / shelf-life modelling (only *mentioned* in LH) — **[RULE]** (lifelines) but **[SOURCE]** for methodology.
- Experimental design / DOE / response-surface / mixture designs — **[SOURCE]**.
- Survey weighting, missing-data imputation, causal inference — **[SOURCE]**.

---

## C. Is the platform easy to extend? Mostly yes — here is the honest breakdown

**Easy (declarative).** Adding a method *within an existing data family* = add one block to
`method_selection_rules.yaml`. No code change. Template:

```yaml
  - id: ordinal_logistic_jar
    when:
      objective_any: [optimize_product, compare_products]
      has_role: [jar]
    recommend:
      method: "Ordinal logistic regression on JAR vs liking"
      python: "statsmodels OrderedModel"
      assumptions_to_check: [proportional_odds, enough_per_category]
      source: ["[SOURCE] add an ordinal-regression reference"]
    # extrapolated: true   # set when applying beyond the cited sources
```

The schemas also grow cleanly: add an enum value (e.g. a new `objective_type` or block `lens`) and the
CI (`tests/validate_kit.py`) keeps the contracts valid.

**Needs a little code.** A genuinely new **data shape** needs loader work — e.g. the multi-sheet
workbook (word association + IAT) exceeds the current single-table loader; `run_agent.py` needs a
`sheet` field + multi-block loading. A genuinely new **method family** needs (a) the library installed
and (b) a code template the agent can run via `run_python`.

**Needs a new source (governance).** For **[SOURCE]** methods, the responsible step is to add a reference
to the rule's `source` and, until then, mark the rule `extrapolated: true` so the agent flags it as not
validated by the current library. The platform makes this explicit rather than hiding it — which is the
point: extensibility should not outrun the evidence base.

### Suggested order to build out
1. **[RULE]** deepen inference: mixed models, ordinal logistic, a shared multiple-testing/effect-size/power layer.
2. Loader: multi-sheet / multi-block support (unblocks datasets like the fish-sauce workbook).
3. **[SOURCE]** behavioral block you already have data for: IAT scoring + scale validation.
4. **[SOURCE]** marketing block: conjoint / MaxDiff / price sensitivity / key-driver — each with a cited reference.
5. **[RULE]** ML + survival; **[SOURCE]** NLP and DOE last.
