import numpy as np, pandas as pd
rng = np.random.default_rng(20260604)

# ---- 8 products laid on 2 latent axes -> true sensory means (0-10) ----
prods = [f"P{i+1}" for i in range(8)]
# latent: axis1 ~ sweetness/fruitiness, axis2 ~ body/creaminess
sweet = np.array([3.0, 4.5, 6.0, 7.5, 8.5, 5.5, 2.5, 7.0])
sour  = np.array([8.0, 6.5, 5.0, 3.5, 2.5, 5.0, 8.5, 4.0])
creamy= np.array([3.0, 4.0, 6.5, 7.0, 8.0, 8.5, 2.0, 5.5])
fruity= np.array([4.0, 5.0, 6.0, 7.5, 7.0, 5.0, 3.0, 8.0])
thick = np.array([3.5, 4.5, 6.0, 6.5, 7.5, 8.0, 2.5, 5.0])
true_senso = pd.DataFrame({"Sweet":sweet,"Sour":sour,"Creamy":creamy,"Fruity":fruity,"Thick":thick}, index=prods)
attrs = list(true_senso.columns)

# ---- panel-level QDA: 10 panelists x 2 sessions, with panelist bias + noise ----
panelists = [f"J{j+1:02d}" for j in range(10)]
rows=[]
pan_bias = {p: rng.normal(0,0.6,len(attrs)) for p in panelists}
for s in [1,2]:
    for p in panelists:
        for prod in prods:
            vals = true_senso.loc[prod].values + pan_bias[p] + rng.normal(0,0.7,len(attrs))
            vals = np.clip(vals,0,10)
            rows.append([p,prod,s,*vals])
qda = pd.DataFrame(rows, columns=["Panelist","Product","Session",*attrs])
qda.to_csv("yogurt_qda_long.csv", sep=";", index=False)

# product means (active matrix for PCA/MFA)
senso_means = qda.groupby("Product")[attrs].mean().loc[prods]
senso_means.to_csv("yogurt_senso_means.csv", sep=";")

# ---- physicochemical (triplicate), correlated with sensory means ----
phys_rows=[]
for prod in prods:
    sm = senso_means.loc[prod]
    for r in range(3):
        pH   = 4.6 - 0.10*sm["Sour"]  + rng.normal(0,0.04)   # more sour -> lower pH
        Brix = 6.0 + 1.05*sm["Sweet"] + rng.normal(0,0.4)    # sweeter -> higher Brix
        Visc = 200 + 90*sm["Thick"]   + rng.normal(0,40)     # thicker -> higher viscosity
        Fat  = 0.5 + 0.45*sm["Creamy"]+ rng.normal(0,0.2)    # creamier -> higher fat
        phys_rows.append([prod,r+1,pH,Brix,Visc,Fat])
phys = pd.DataFrame(phys_rows, columns=["Product","Rep","pH","Brix","Viscosity","Fat"])
phys.to_csv("yogurt_physchem.csv", sep=";", index=False)
phys_means = phys.groupby("Product")[["pH","Brix","Viscosity","Fat"]].mean().loc[prods]
phys_means.to_csv("yogurt_phys_means.csv", sep=";")

# ---- hedonic: 100 consumers, 2 latent segments ----
ncons=100
seg = rng.choice([0,1], size=ncons, p=[0.55,0.45])   # seg0 likes sweet, seg1 likes tart/light
ideal_sweet = np.where(seg==0, 8.0, 4.0)
b_creamy    = np.where(seg==0, 0.20, 0.10)
cons = [f"C{c+1:03d}" for c in range(ncons)]
L = np.zeros((ncons,len(prods)))
for ci in range(ncons):
    for pi,prod in enumerate(prods):
        sm = senso_means.loc[prod]
        base = 6.3
        sweet_pen = -0.14*(sm["Sweet"]-ideal_sweet[ci])**2     # optimum (inverted-U)
        creamy_dr = b_creamy[ci]*sm["Creamy"]
        sour_pen  = -0.05*sm["Sour"]
        val = base + sweet_pen + creamy_dr + sour_pen + rng.normal(0,0.8)
        L[ci,pi]=np.clip(round(val),1,9)
liking = pd.DataFrame(L, index=cons, columns=prods)
liking.index.name="Consumer"
liking.to_csv("yogurt_liking.csv", sep=";")
pd.DataFrame({"Consumer":cons,"Segment_true":seg}).to_csv("yogurt_segments_truth.csv", sep=";", index=False)

# ---- JAR: 3 attributes, deviation from each consumer's ideal (-2..+2) ----
jar_rows=[]
for ci in range(ncons):
    for prod in prods:
        sm = senso_means.loc[prod]
        sweet_dev = np.clip(round((sm["Sweet"]-ideal_sweet[ci])/1.5),-2,2)
        thick_dev = np.clip(round((sm["Thick"]-5.0)/1.5),-2,2)
        sour_dev  = np.clip(round((sm["Sour"]-4.5)/1.5),-2,2)
        jar_rows.append([cons[ci],prod,sweet_dev,thick_dev,sour_dev])
jar = pd.DataFrame(jar_rows, columns=["Consumer","Product","JAR_Sweet","JAR_Thick","JAR_Sour"])
jar.to_csv("yogurt_jar.csv", sep=";", index=False)

print("Generated files:")
import os
for f in sorted(os.listdir(".")):
    if f.startswith("yogurt"): print(" ", f, os.path.getsize(f), "bytes")
print("\nSensory product means:\n", senso_means.round(2))
print("\nLiking matrix shape:", liking.shape, "| mean liking per product:\n", liking.mean().round(2).to_dict())
print("True segment sizes:", dict(pd.Series(seg).value_counts()))
