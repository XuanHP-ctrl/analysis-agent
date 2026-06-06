# Reference sources to add for [SOURCE] methods

For each method the rule base flags `[SOURCE]` (not covered by the three sensometrics books),
here are the canonical references to add to the project so the agent can recommend them
*responsibly* (cite in the rule's `source`, drop the `extrapolated: true` flag once added).
Citations below are foundational; pair each with a current applied text before production use.

## Behavioral / psychometric
- **Implicit Association Test (IAT) & D-score** — Greenwald, McGhee & Schwartz (1998), *J. Personality & Social Psychology* 74:1464–1480 (original IAT); Greenwald, Nosek & Banaji (2003), *JPSP* 85(2):197–216 (the improved D-score algorithm — practice trials, latency-calibrated, error penalty). NOTE: D-score sign depends on block design.
- **Structural Equation Modelling (CB-SEM)** — Kline, *Principles and Practice of Structural Equation Modeling* (Guilford).
- **PLS path modelling** — Tenenhaus, Esposito Vinzi, Chatelin & Lauro (2005), *Computational Statistics & Data Analysis* 48:159–205; Pagès & Tenenhaus (2001) for the sensory chain.
- **Scale validation** — Cronbach (1951) for alpha; Embretson & Reise (2000), *Item Response Theory for Psychologists*; Brown, *Confirmatory Factor Analysis for Applied Research*.

## Marketing research
- **Conjoint analysis** — Green & Srinivasan (1978, 1990), *J. Consumer Research / J. Marketing*; for choice-based: Louviere, Hensher & Swait (2000), *Stated Choice Methods*.
- **Discrete choice / random utility** — Train (2009), *Discrete Choice Methods with Simulation*.
- **MaxDiff (best–worst scaling)** — Louviere, Flynn & Marley (2015), *Best-Worst Scaling: Theory, Methods and Applications*; Marley & Louviere (2005), *J. Mathematical Psychology*.
- **Price sensitivity** — Van Westendorp (1976), Price Sensitivity Meter (ESOMAR); Gabor & Granger (1966), *Economica*.
- **Key-driver analysis** — Johnson (2000) relative weights, *Multivariate Behavioral Research*; Lipovetsky & Conklin (2001) Shapley-value regression, *Applied Stochastic Models in Business and Industry*.
- **Kano model** — Kano, Seraku, Takahashi & Tsuji (1984), *J. Japanese Society for Quality Control*.
- **TURF** — standard market-research technique; see Cohen, *Marketing Research* texts (no single seminal paper).

## Advanced / statistical depth
- **Mixed-effects models** — Bates et al. (2015) lme4, *J. Statistical Software*; Kuznetsova et al. (2017) lmerTest.
- **Ordinal regression** — Agresti, *Categorical Data Analysis*; Christensen (2019) ordinal R package.
- **Machine learning for driver importance** — Breiman (2001) random forests, *Machine Learning*; Lundberg & Lee (2017) SHAP.
- **Survival / shelf-life** — Hough (2010), *Sensory Shelf Life Estimation of Food Products* (CRC).
- **DOE / response surface / mixture** — Montgomery, *Design and Analysis of Experiments*; Cornell, *Experiments with Mixtures*.
- **Text analytics / NLP** — Blei, Ng & Jordan (2003) LDA topic models, *JMLR*; plus a current applied NLP text.
- **Multiple testing / effect sizes** — Benjamini & Hochberg (1995), *JRSS-B* 57:289–300; Cohen, *Statistical Power Analysis*.
- **Bayesian** — McElreath, *Statistical Rethinking*; Bürkner (2017) brms, *J. Statistical Software*.

## How to use this list
1. Add the chosen reference to the relevant rule's `source` in `method_selection_rules.yaml`.
2. Remove `extrapolated: true` once the method is genuinely backed by a source you have adopted.
3. Add a code template (Python) + ensure the library is in `requirements.txt`.
4. Re-run `tests/validate_kit.py` (CI) to confirm the rule base still validates.
