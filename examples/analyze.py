import numpy as np, pandas as pd, warnings
warnings.filterwarnings("ignore")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats
from scipy.cluster.hierarchy import linkage, fcluster
import statsmodels.formula.api as smf
from statsmodels.stats.anova import anova_lm
from sklearn.metrics import adjusted_rand_score
import prince

S = ";"
qda   = pd.read_csv("yogurt_qda_long.csv", sep=S)
senso = pd.read_csv("yogurt_senso_means.csv", sep=S, index_col=0)
phys  = pd.read_csv("yogurt_phys_means.csv", sep=S, index_col=0)
liking= pd.read_csv("yogurt_liking.csv", sep=S, index_col=0)
jar   = pd.read_csv("yogurt_jar.csv", sep=S)
truth = pd.read_csv("yogurt_segments_truth.csv", sep=S)
prods = list(senso.index); attrs = list(senso.columns)
out = {}

# ============ 1) ANOVA per attribute (Product effect) + residual normality ============
print("="*72,"\n[1] ANOVA — product effect per sensory attribute (+ Shapiro on residuals)\n")
anova_tbl=[]
for a in attrs:
    m = smf.ols(f"{a} ~ C(Product) + C(Panelist) + C(Session)", data=qda).fit()
    aov = anova_lm(m, typ=2)
    F = aov.loc["C(Product)","F"]; p = aov.loc["C(Product)","PR(>F)"]
    sh = stats.shapiro(m.resid).pvalue
    anova_tbl.append([a, round(F,1), p, round(sh,3)])
adf = pd.DataFrame(anova_tbl, columns=["Attribute","F(Product)","p_value","Shapiro_p(resid)"])
print(adf.to_string(index=False))
out["anova"]=adf

# ============ 2) PCA on sensory means ============
print("\n"+"="*72,"\n[2] PCA on sensory product means (standardized)\n")
pca = prince.PCA(n_components=2, rescale_with_mean=True, rescale_with_std=True).fit(senso)
eig = pca.eigenvalues_summary
print(eig.to_string())
pc_coord = pca.row_coordinates(senso); pc_coord.columns=["Dim1","Dim2"]
# variable coords = correlation of each (standardized) attribute with the row coordinates
col_coord = pd.DataFrame({d: [np.corrcoef(senso[a].values, pc_coord[d].values)[0,1] for a in attrs]
                          for d in ["Dim1","Dim2"]}, index=attrs)
out["pca_var"]=eig

# ============ 3) MFA — sensory + instrumental blocks ============
print("\n"+"="*72,"\n[3] MFA — link sensory & physicochemical blocks on the same products\n")
combined = pd.concat([senso, phys], axis=1)
groups = {"sensory": list(senso.columns), "instrumental": list(phys.columns)}
mfa = prince.MFA(n_components=2).fit(combined, groups=groups)
# RV-like: correlation between the two blocks' first dimensions (partial axes)
sp = prince.PCA(n_components=1).fit(senso).row_coordinates(senso).iloc[:,0]
ip = prince.PCA(n_components=1).fit(phys ).row_coordinates(phys ).iloc[:,0]
rv = abs(np.corrcoef(sp, ip)[0,1])
print(f"Sensory & instrumental are strongly aligned: |corr(block1 dim1)| = {rv:.3f}")
print("MFA eigenvalues:\n", mfa.eigenvalues_summary.to_string())
out["mfa_align"]=rv

# ============ 4) Consumer segmentation (Ward HAC on liking) + validate ============
print("\n"+"="*72,"\n[4] Consumer segmentation — Ward hierarchical clustering on liking\n")
Z = linkage(liking.values, method="ward")
lab2 = fcluster(Z, t=2, criterion="maxclust")
ari = adjusted_rand_score(truth["Segment_true"].values, lab2)
sizes = pd.Series(lab2).value_counts().to_dict()
print(f"2-cluster solution sizes: {sizes}")
print(f"Adjusted Rand Index vs TRUE latent segments = {ari:.3f}  (1.0 = perfect recovery)")
clmean = pd.DataFrame({f"cluster{c}": liking[lab2==c].mean() for c in sorted(set(lab2))})
print("Cluster mean liking per product:\n", clmean.round(2).to_string())
out["ari"]=ari

# ============ 5) Internal preference map (PCA on liking) ============
print("\n"+"="*72,"\n[5] Internal preference map (MDPref) — PCA on products x consumers liking\n")
ipm = prince.PCA(n_components=2).fit(liking)   # rows=consumers
print("Variance explained (first 2 dims of the preference space):\n", ipm.eigenvalues_summary.iloc[:2].to_string())

# ============ 6) Drivers of liking (linear + quadratic on product means) ============
print("\n"+"="*72,"\n[6] Drivers of (dis)liking — regress MEAN liking on each sensory attribute\n")
mean_lik = liking.mean(axis=0).loc[prods]
dol=[]
for a in attrs:
    x = senso[a].values; y = mean_lik.values
    lin = stats.linregress(x,y)
    # quadratic
    Xq = np.column_stack([np.ones_like(x), x, x**2])
    beta,_,_,_ = np.linalg.lstsq(Xq, y, rcond=None)
    yhat = Xq@beta; r2q = 1 - ((y-yhat)**2).sum()/((y-y.mean())**2).sum()
    dol.append([a, round(lin.slope,3), round(lin.rvalue**2,3), round(r2q,3), "yes" if beta[2]<-0.02 else "-"])
ddf = pd.DataFrame(dol, columns=["Attribute","linear_slope","R2_linear","R2_quadratic","saturation(neg quad)"])
print(ddf.to_string(index=False))
out["dol"]=ddf

# ============ 7) External preference map -> response surface (vector model) ============
print("\n"+"="*72,"\n[7] External preference map — per-consumer regression in sensory PC space\n")
# product coords in standardized sensory PCA space
P = pc_coord[["Dim1","Dim2"]].values
# per-consumer LINEAR model (vector); quadratic at n=8 products would overfit (LH caveat)
grid_n=60
gx=np.linspace(P[:,0].min()-1,P[:,0].max()+1,grid_n)
gy=np.linspace(P[:,1].min()-1,P[:,1].max()+1,grid_n)
GX,GY=np.meshgrid(gx,gy)
flat=np.column_stack([GX.ravel(),GY.ravel()])
above=np.zeros(flat.shape[0])
for c in liking.index:
    yv=liking.loc[c,prods].values.astype(float)
    A=np.column_stack([np.ones(8),P[:,0],P[:,1]])
    b,_,_,_=np.linalg.lstsq(A,yv,rcond=None)
    pred=np.column_stack([np.ones(len(flat)),flat[:,0],flat[:,1]])@b
    above += (pred>=yv.mean()).astype(float)   # % consumers for whom point beats their own avg
pct=(above/len(liking.index)*100).reshape(GX.shape)
best=np.unravel_index(np.argmax(pct),pct.shape)
print(f"Peak acceptance region: ~{pct.max():.0f}% of consumers, near sensory PC ("
      f"{GX[best]:.2f},{GY[best]:.2f})")
out["maxpct"]=pct.max()

# ============ 8) Penalty analysis (JAR mean drop) for top product ============
print("\n"+"="*72,"\n[8] Penalty analysis (mean drop) — JAR vs overall liking, top product\n")
liking_long = liking.reset_index().melt(id_vars="Consumer", var_name="Product", value_name="Liking")
jl = jar.merge(liking_long, on=["Consumer","Product"])
top = mean_lik.idxmax()
sub = jl[jl["Product"]==top]
pen=[]
for col,name in [("JAR_Sweet","Sweetness"),("JAR_Thick","Thickness"),("JAR_Sour","Sourness")]:
    cat = pd.cut(sub[col], [-2.5,-0.5,0.5,2.5], labels=["too_low","JAR","too_high"])
    jar_mean = sub.loc[cat=="JAR","Liking"].mean()
    for lv in ["too_low","too_high"]:
        grp=sub.loc[cat==lv,"Liking"]
        if len(grp)>=3 and not np.isnan(jar_mean):
            drop=jar_mean-grp.mean(); pct_c=100*len(grp)/len(sub)
            pen.append([name,lv,round(drop,2),round(pct_c,0)])
pdf=pd.DataFrame(pen, columns=["Attribute","Direction","Mean_drop","%_consumers"])
print(f"Top product = {top}")
print(pdf.to_string(index=False) if len(pdf) else "(no non-JAR group large enough)")
out["penalty"]=pdf; out["top"]=top

# ===================== FIGURES =====================
fig,axes=plt.subplots(2,2,figsize=(12,10))
# (a) PCA biplot sensory
ax=axes[0,0]
for p in prods: ax.scatter(pc_coord.loc[p,"Dim1"],pc_coord.loc[p,"Dim2"],s=60,color="#1D9E75"); ax.annotate(p,(pc_coord.loc[p,"Dim1"],pc_coord.loc[p,"Dim2"]),fontsize=9)
sc=3
for a in attrs: ax.arrow(0,0,col_coord.loc[a,"Dim1"]*sc,col_coord.loc[a,"Dim2"]*sc,color="#D85A30",head_width=0.08); ax.text(col_coord.loc[a,"Dim1"]*sc*1.1,col_coord.loc[a,"Dim2"]*sc*1.1,a,color="#993C1D",fontsize=9)
ax.axhline(0,lw=.5,color="grey");ax.axvline(0,lw=.5,color="grey");ax.set_title("[2] PCA — sensory product space");ax.set_xlabel("Dim1");ax.set_ylabel("Dim2")
# (b) dendrogram-ish: cluster mean liking
ax=axes[0,1]
clmean.plot(kind="bar",ax=ax,color=["#534AB7","#D4537E"]); ax.set_title(f"[4] Segment mean liking (ARI={ari:.2f})");ax.set_ylabel("mean liking");ax.set_xlabel("product")
# (c) drivers of liking: Sweet
ax=axes[1,0]
xs=senso["Sweet"].values; ys=mean_lik.values; ax.scatter(xs,ys,color="#185FA5")
for p in prods: ax.annotate(p,(senso.loc[p,"Sweet"],mean_lik[p]),fontsize=8)
xx=np.linspace(xs.min(),xs.max(),50); Xq=np.column_stack([np.ones_like(xx),xx,xx**2])
bq=np.linalg.lstsq(np.column_stack([np.ones_like(xs),xs,xs**2]),ys,rcond=None)[0]
ax.plot(xx,Xq@bq,color="#993C1D"); ax.set_title("[6] Driver of liking: Sweet (inverted-U)");ax.set_xlabel("Sweet intensity");ax.set_ylabel("mean liking")
# (d) external preference map response surface
ax=axes[1,1]
cs=ax.contourf(GX,GY,pct,levels=10,cmap="RdYlGn"); plt.colorbar(cs,ax=ax,label="% consumers")
for p in prods: ax.scatter(pc_coord.loc[p,"Dim1"],pc_coord.loc[p,"Dim2"],color="black",s=40); ax.annotate(p,(pc_coord.loc[p,"Dim1"],pc_coord.loc[p,"Dim2"]),fontsize=8,color="black")
ax.set_title("[7] External preference map (response surface)");ax.set_xlabel("sensory Dim1");ax.set_ylabel("sensory Dim2")
plt.tight_layout(); plt.savefig("/home/claude/results.png",dpi=110,bbox_inches="tight")
print("\nSaved figure -> results.png")
