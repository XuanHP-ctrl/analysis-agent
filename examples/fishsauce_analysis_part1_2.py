"""
PHẦN 3 (revised) + CLUSTER MERGED
- Dùng d_score đã tính sẵn (Greenwald 2003, trial-level pooled SD — không thể
  tái tính từ block means; d_score trong file là đúng)
- Phân ngưỡng |d|: <0.15 None, 0.15-0.30 Small, 0.30-0.50 Medium,
  0.50-0.70 Strong, >0.70 Very strong
- Positive d_score = implicit pro-TT (xác nhận từ design: Version A/B: B4=congruent;
  Version C/D: B7=congruent → sign convention nhất quán)
- Merge WA + Explicit + IAT → cluster
"""
import warnings; warnings.filterwarnings("ignore")
import pandas as pd, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt, matplotlib.patches as mpatches
from scipy import stats
from scipy.cluster.hierarchy import linkage, dendrogram
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from statsmodels.stats.multitest import multipletests

WA_PATH  = "data/Word_association.xlsx"
IAT_PATH = "data/Data_IAT.xlsx"
EXPL     = ["liking","tasty","packaging","protein","healthy","price","ingre","familar","popular"]

def recode_region_vi(s):
    m={"Bắc":"North","Bắc Trung Bộ":"Centre","Nam Trung Bộ":"Centre","Nam":"South"}
    return s.astype(str).str.strip().map(m)
def recode_region_en(s):
    m={"north":"North","northern":"North","central":"Centre","south":"South","southern":"South"}
    return s.astype(str).str.strip().str.lower().map(m)
def parse_vn_float(s):
    def _p(v):
        v=str(v).strip().replace(" ",""); parts=v.split(".")
        if len(parts)==3: return float(parts[0]+parts[1]+"."+parts[2])
        try: return float(v)
        except: return np.nan
    return s.apply(_p)
def d_strength(d):
    a=abs(d)
    if   a<0.15: return "None (<0.15)"
    elif a<0.30: return "Small (0.15–0.30)"
    elif a<0.50: return "Medium (0.30–0.50)"
    elif a<0.70: return "Strong (0.50–0.70)"
    else:        return "Very strong (>0.70)"
def d_direction(d):
    if   d> 0.15: return "Implicit pro-TT"
    elif d<-0.15: return "Implicit pro-CN"
    else:         return "No clear link"
def p_s(t):
    print("\n"+"="*70+f"\n{t}\n"+"="*70)

# ════════════════════════════════════════════════════════════════════════════
p_s("BƯỚC 1 — PHÂN NGƯỠNG D-SCORE (Greenwald et al. 2003)")
iat = pd.read_excel(IAT_PATH, sheet_name="RawData")
iat["Region3"]    = recode_region_en(iat["region"])
iat["B4_ms"]      = parse_vn_float(iat["B4_RT"])
iat["B7_ms"]      = parse_vn_float(iat["B7_RT"])
iat["d_strength"] = iat["d_score"].apply(d_strength)
iat["d_direction"]= iat["d_score"].apply(d_direction)
iat["user_vi"]    = iat["user"].map({"TT":"Truyền thống","CN":"Công nghiệp"})
iat["pref_expl"]  = iat["liking_TT"] - iat["liking_CN"]

ds = iat.dropna(subset=["d_score"])
print(f"\nn = {len(ds)}  |  mean = {ds['d_score'].mean():.3f}  SD = {ds['d_score'].std():.3f}")
print(f"range [{ds['d_score'].min():.3f}, {ds['d_score'].max():.3f}]")
print("\nLưu ý: d_score = (M_incongruent – M_congruent) / SD_pooled_all_trials")
print("Positive = implicit pro-TT (TT+pleasant pairing faster)")
print("D-score đã tính sẵn từ trial-level data; không tái tính được từ block means.\n")

print("── Phân phối theo ngưỡng |d| ──")
order_str = ["None (<0.15)","Small (0.15–0.30)","Medium (0.30–0.50)",
             "Strong (0.50–0.70)","Very strong (>0.70)"]
for cat in order_str:
    n = (ds["d_strength"]==cat).sum()
    print(f"  {cat}: n={n} ({n/len(ds)*100:.1f}%)")

print("\n── Hướng implicit ──")
for cat in ["Implicit pro-TT","No clear link","Implicit pro-CN"]:
    n=(ds["d_direction"]==cat).sum()
    print(f"  {cat}: n={n} ({n/len(ds)*100:.1f}%)")

print("\n── d_strength × User ──")
print(pd.crosstab(ds["user_vi"],ds["d_strength"])[order_str].to_string())
print("\n── d_strength × Region3 ──")
print(pd.crosstab(ds["Region3"],ds["d_strength"])[order_str].to_string())

# Mann-Whitney TT vs CN d_score
tt_d=ds[ds["user"]=="TT"]["d_score"]; cn_d=ds[ds["user"]=="CN"]["d_score"]
u,p_u=stats.mannwhitneyu(tt_d.dropna(),cn_d.dropna(),alternative="two-sided")
print(f"\nMann-Whitney (d_score TT vs CN): U={u:.1f}, p={p_u:.4f}"
      f"  mean_TT={tt_d.mean():.3f}  mean_CN={cn_d.mean():.3f}"
      f"  {'*' if p_u<0.05 else 'ns'}")

h_kw,p_kw=stats.kruskal(*[ds[ds["Region3"]==r]["d_score"].dropna()
                            for r in ["North","Centre","South"]])
print(f"Kruskal-Wallis (d_score by Region): H={h_kw:.3f}, p={p_kw:.4f}"
      f"  {'*' if p_kw<0.05 else 'ns'}")

# Histogram + strength bar
fig,axes=plt.subplots(1,2,figsize=(14,5))
ax=axes[0]
ax.hist(ds["d_score"],bins=30,color="#5dade2",edgecolor="white",lw=0.5)
for x,c in [(-0.70,"#c0392b"),(-0.50,"#e67e22"),(-0.30,"#f39c12"),(-0.15,"#bdc3c7"),
             (0.15,"#bdc3c7"),(0.30,"#f39c12"),(0.50,"#e67e22"),(0.70,"#c0392b")]:
    ax.axvline(x,color=c,lw=1.5,ls="--",alpha=0.85)
ax.axvline(0,color="black",lw=1.5)
ax.set_xlabel("IAT D-score",fontsize=12); ax.set_ylabel("Count",fontsize=12)
ax.set_title("D-score distribution\n(đứt = ngưỡng |d|; + = pro-TT)",fontweight="bold")
for xt,lb in [(-0.8,"Very\nstrong"),(-0.6,"Strong"),(-0.4,"Medium"),(-0.22,"Small"),
               (0.22,"Small"),(0.4,"Medium"),(0.6,"Strong"),(0.8,"Very\nstrong")]:
    ax.text(xt,ax.get_ylim()[1]*0.85,lb,ha="center",fontsize=7,color="grey")

# Stacked bar by user
width=0.35; x_pos=np.arange(len(order_str))
colors_s=["#bdc3c7","#85c1e9","#f0b27a","#eb984e","#c0392b"]
bottom_tt=np.zeros(len(order_str)); bottom_cn=np.zeros(len(order_str))
for i,(cat,col) in enumerate(zip(order_str,colors_s)):
    tt_n=((ds["user"]=="TT")&(ds["d_strength"]==cat)).sum()
    cn_n=((ds["user"]=="CN")&(ds["d_strength"]==cat)).sum()
    axes[1].bar(x_pos-0.18,[((ds["user"]=="TT")&(ds["d_strength"]==o)).sum()
                              for o in order_str][i],width=width,
                bottom=0,color=col,label=cat if i==0 else "")
for grp,offset,clr in [("TT",-0.18,"#e74c3c"),("CN",0.18,"#3498db")]:
    vals=[(ds["user"]==grp)&(ds["d_strength"]==o) for o in order_str]
    axes[1].bar(x_pos+offset,[v.sum() for v in vals],width=width,
                label=grp,color=clr,alpha=0.8)
axes[1].set_xticks(x_pos)
axes[1].set_xticklabels([o.split("(")[0].strip() for o in order_str],rotation=20,ha="right",fontsize=9)
axes[1].set_title("D-score strength by User",fontweight="bold")
axes[1].set_ylabel("Count"); axes[1].legend(fontsize=9)
plt.tight_layout()
plt.savefig("output_Dscore_strength.png",dpi=150,bbox_inches="tight"); plt.close()
print("\n→ Saved: output_Dscore_strength.png")

# ════════════════════════════════════════════════════════════════════════════
p_s("BƯỚC 2 — DISSONANCE ANALYSIS")

an = ds.dropna(subset=["pref_expl","d_score"])
an = an.copy()
an["quadrant"] = np.select(
    [(an["pref_expl"]>=0)&(an["d_score"]>=0),
     (an["pref_expl"]>=0)&(an["d_score"]< 0),
     (an["pref_expl"]< 0)&(an["d_score"]< 0),
     (an["pref_expl"]< 0)&(an["d_score"]>=0)],
    ["Consistent pro-TT",
     "Dissonance (explicit TT / implicit CN)",
     "Consistent pro-CN",
     "Dissonance (explicit CN / implicit TT)"],default="?")
an["dissonant"]=an["quadrant"].str.contains("Dissonance").astype(int)

r,p_r=stats.pearsonr(an["d_score"],an["pref_expl"])
print(f"\nPearson r(d_score, liking_TT−CN) = {r:.3f},  p = {p_r:.4f}")

print("\n── Quadrant distribution ──")
for q,n in an["quadrant"].value_counts().items():
    print(f"  {q}: n={n} ({n/len(an)*100:.1f}%)")

print(f"\nTổng tỷ lệ dissonance: {an['dissonant'].mean()*100:.1f}%")

# Dissonance by d_strength
print("\n── Dissonance rate by d_strength ──")
dds=an.groupby("d_strength")["dissonant"].agg(["sum","count","mean"])
dds.columns=["n_dissonant","n_total","rate"]; dds["rate"]=(dds["rate"]*100).round(1)
print(dds.reindex(order_str).to_string())

# Dissonance × user
print("\n── Dissonance × User ──")
ct_u=pd.crosstab(an["user_vi"],an["dissonant"],colnames=["dissonant(1=yes)"])
print(ct_u.to_string())
c2u,pu,_,_=stats.chi2_contingency(ct_u)
print(f"χ²={c2u:.3f}, p={pu:.4f}  {'*' if pu<0.05 else 'ns'}")

# Dissonance × Region
print("\n── Dissonance × Region3 ──")
ct_r=pd.crosstab(an["Region3"],an["dissonant"],colnames=["dissonant(1=yes)"])
print(ct_r.to_string())
c2r,pr,_,_=stats.chi2_contingency(ct_r)
print(f"χ²={c2r:.3f}, p={pr:.4f}  {'*' if pr<0.05 else 'ns'}")

# Scatter dissonance
fig,axes=plt.subplots(1,2,figsize=(16,7))
colors_q={"Consistent pro-TT":"#e74c3c",
           "Consistent pro-CN":"#3498db",
           "Dissonance (explicit TT / implicit CN)":"#f39c12",
           "Dissonance (explicit CN / implicit TT)":"#9b59b6"}
for q,sub in an.groupby("quadrant"):
    axes[0].scatter(sub["pref_expl"],sub["d_score"],c=colors_q.get(q,"grey"),
                    label=f"{q} (n={len(sub)}, {len(sub)/len(an)*100:.0f}%)",
                    alpha=0.65,s=50,edgecolors="white",lw=0.3)
axes[0].axhline(0,color="black",lw=0.8,ls="--")
axes[0].axvline(0,color="black",lw=0.8,ls="--")
for y in [0.15,0.30,0.50,0.70,-0.15,-0.30,-0.50,-0.70]:
    axes[0].axhline(y,color="grey",lw=0.5,ls=":",alpha=0.6)
axes[0].set_xlabel("Explicit preference (liking_TT − liking_CN)",fontsize=11)
axes[0].set_ylabel("IAT D-score (implicit)\n+ = pro-TT",fontsize=11)
axes[0].set_title("Cognitive Dissonance Map\n(đường chấm = ngưỡng d_strength)",
                   fontweight="bold",fontsize=11)
axes[0].legend(fontsize=8,loc="upper left",framealpha=0.9)
r_str = f"{r:.2f}" if not np.isnan(r) else "NaN"
p_str = f"{p_r:.3f}" if not np.isnan(p_r) else "NaN"
axes[0].annotate(f"r = {r_str}, p = {p_str}",xy=(0.98,0.02),xycoords="axes fraction",
                 ha="right",fontsize=10,bbox=dict(boxstyle="round",fc="lightyellow",alpha=0.9))

# Pie strength
st_cnt=an["d_strength"].value_counts().reindex(order_str).fillna(0)
pie_labels=[f"{s.split('(')[0].strip()}\n(n={int(v)})" for s,v in st_cnt.items()]
pie_clr=["#bdc3c7","#85c1e9","#f0b27a","#eb984e","#c0392b"]
axes[1].pie(st_cnt.values,labels=pie_labels,autopct="%1.1f%%",startangle=90,
            explode=[0.04]*5,colors=pie_clr)
axes[1].set_title("D-score strength (|d|)\nn="+str(len(an)),fontweight="bold",fontsize=11)
plt.tight_layout()
plt.savefig("output_Dscore_dissonance.png",dpi=150,bbox_inches="tight"); plt.close()
print("\n→ Saved: output_Dscore_dissonance.png")

# ════════════════════════════════════════════════════════════════════════════
p_s("BƯỚC 3 — MERGE 3 NGUỒN + CLUSTER")

df_t=pd.read_excel(WA_PATH, sheet_name="Binary (topic)")
df_e=pd.read_excel(WA_PATH, sheet_name="Binary (element)")
for df in [df_t,df_e]:
    df["Region3"]=recode_region_vi(df["region"])
df_t=df_t.dropna(subset=["Region3"]); df_e=df_e.dropna(subset=["Region3"])
terms_t=[c for c in df_t.columns if c not in
         ("Mã đăng nhập","region","gender","age","user","frequency","Region3")]
terms_e=[c for c in df_e.columns if c not in
         ("Mã đăng nhập","region","gender","age","user","frequency","Region3")]

wa_merged=(df_t[["Mã đăng nhập","Region3","user"]+terms_t]
           .merge(df_e[["Mã đăng nhập"]+terms_e],on="Mã đăng nhập",how="inner")
           .rename(columns={"Mã đăng nhập":"ID","user":"user_vi"}))

iat_cols=(["ID","user","Region3","d_score","d_strength","d_direction","pref_expl",
           "user_vi","quadrant","dissonant"]
          +[f"{a}_TT" for a in EXPL]+[f"{a}_CN" for a in EXPL])
iat_sel=an[iat_cols].copy()

merged=wa_merged.merge(iat_sel,on="ID",how="inner",suffixes=("_wa",""))
merged=merged.dropna(subset=["d_score"]+[f"{a}_TT" for a in EXPL])
print(f"\nMerged rows: {len(merged)}")
print(f"Region3: {merged['Region3_wa'].value_counts().to_dict()}")
print(f"User:    {merged['user_vi_wa'].value_counts().to_dict()}")

# Feature matrix
feat_expl=[f"{a}_TT" for a in EXPL]+[f"{a}_CN" for a in EXPL]
feat_iat =["d_score"]
feat_wa  =terms_t+terms_e
all_feat =feat_expl+feat_iat+feat_wa

Xdf=merged[all_feat].dropna(); idx=Xdf.index
X=StandardScaler().fit_transform(Xdf)
print(f"\nCluster input: {X.shape[0]} respondents × {X.shape[1]} vars"
      f"  ({len(feat_expl)} explicit + {len(feat_iat)} IAT + {len(feat_wa)} WA)")

inertias=[]; sils=[]
for k in range(2,8):
    km=KMeans(n_clusters=k,random_state=42,n_init=30).fit(X)
    inertias.append(km.inertia_); sils.append(silhouette_score(X,km.labels_))
print("\nk  | inertia  | silhouette")
for k,ine,sil in zip(range(2,8),inertias,sils):
    print(f"k={k} | {ine:8.1f} | {sil:.3f}{'  ←' if sil==max(sils) else ''}")

best_k=2+int(np.argmax(sils))
km_best=KMeans(n_clusters=best_k,random_state=42,n_init=30)
labels=km_best.fit_predict(X)
res=merged.loc[idx].copy(); res["cluster"]=labels+1

print(f"\n── Cluster sizes (k={best_k}) ──")
print(res["cluster"].value_counts().sort_index().to_string())
print("\n── Cluster × User ──")
print(pd.crosstab(res["cluster"],res["user_vi_wa"]).to_string())
print("\n── Cluster × Region3 ──")
print(pd.crosstab(res["cluster"],res["Region3_wa"]).to_string())
print("\n── Cluster × d_direction ──")
print(pd.crosstab(res["cluster"],res["d_direction"]).to_string())
print("\n── Cluster × d_strength ──")
print(pd.crosstab(res["cluster"],res["d_strength"]).reindex(columns=order_str,fill_value=0).to_string())
print("\n── Cluster × Dissonant ──")
print(pd.crosstab(res["cluster"],res["dissonant"],colnames=["dissonant(1=yes)"]).to_string())

# Cluster means
key=["liking_TT","liking_CN","d_score","pref_expl"]
cm=res.groupby("cluster")[key].mean().round(3)
cm["TT−CN"]=(cm["liking_TT"]-cm["liking_CN"]).round(2)
print(f"\n── Cluster means (key) ──\n{cm.to_string()}")

print("\n── Top-5 WA element per cluster ──")
for c in sorted(res["cluster"].unique()):
    sub=res[res["cluster"]==c][terms_e].mean().sort_values(ascending=False)
    print(f"  C{c}: {', '.join(f'{t}({sub[t]*100:.0f}%)' for t in sub.head(5).index)}")

print("\n── Top-5 WA topic per cluster ──")
for c in sorted(res["cluster"].unique()):
    sub=res[res["cluster"]==c][terms_t].mean().sort_values(ascending=False)
    print(f"  C{c}: {', '.join(f'{t}({sub[t]*100:.0f}%)' for t in sub.head(5).index)}")

for grp_col in ["user_vi_wa","Region3_wa","d_direction","dissonant"]:
    ct=pd.crosstab(res["cluster"],res[grp_col])
    c2,p2,_,exp=stats.chi2_contingency(ct)
    print(f"\nCluster × {grp_col}: χ²={c2:.3f}, p={p2:.4f} {'*sig' if p2<0.05 else 'ns'}"
          f"  min_exp={exp.min():.1f}")

# PCA 3-panel
pca2=PCA(n_components=2); X2=pca2.fit_transform(X)
fig,axes=plt.subplots(1,3,figsize=(21,7))
clr={1:"#e74c3c",2:"#2ecc71",3:"#3498db",4:"#9b59b6",5:"#f39c12",6:"#1abc9c"}

for c in sorted(res["cluster"].unique()):
    mask=res["cluster"]==c; r=cm.loc[c]
    lbl=f"C{c} n={mask.sum()} | TT={r['liking_TT']:.1f} CN={r['liking_CN']:.1f} d={r['d_score']:.3f}"
    axes[0].scatter(X2[mask,0],X2[mask,1],c=clr[c],label=lbl,alpha=0.65,s=50,
                    edgecolors="white",lw=0.3)
axes[0].set_title(f"Clusters (k={best_k}) — WA+Explicit+IAT",fontweight="bold",fontsize=11)
axes[0].set_xlabel(f"PC1 ({pca2.explained_variance_ratio_[0]*100:.1f}%)")
axes[0].set_ylabel(f"PC2 ({pca2.explained_variance_ratio_[1]*100:.1f}%)")
axes[0].legend(fontsize=7.5)

uc={"Truyền thống":"#e74c3c","Công nghiệp":"#3498db"}
for usr,sub in res.groupby("user_vi_wa"):
    mask2=res.index.isin(sub.index)
    axes[1].scatter(X2[mask2,0],X2[mask2,1],c=uc.get(usr,"grey"),
                    label=f"{usr} (n={mask2.sum()})",alpha=0.45,s=40,edgecolors="white",lw=0.2)
axes[1].set_title("User overlay",fontweight="bold",fontsize=11)
axes[1].set_xlabel(f"PC1 ({pca2.explained_variance_ratio_[0]*100:.1f}%)")
axes[1].set_ylabel(f"PC2 ({pca2.explained_variance_ratio_[1]*100:.1f}%)")
axes[1].legend(fontsize=10)

dc={"Implicit pro-TT":"#e74c3c","Implicit pro-CN":"#3498db","No clear link":"#95a5a6"}
for dd,sub in res.groupby("d_direction"):
    mask3=res.index.isin(sub.index)
    axes[2].scatter(X2[mask3,0],X2[mask3,1],c=dc.get(dd,"grey"),
                    label=f"{dd} (n={mask3.sum()})",alpha=0.55,s=40,edgecolors="white",lw=0.2)
axes[2].set_title("IAT direction overlay",fontweight="bold",fontsize=11)
axes[2].set_xlabel(f"PC1 ({pca2.explained_variance_ratio_[0]*100:.1f}%)")
axes[2].set_ylabel(f"PC2 ({pca2.explained_variance_ratio_[1]*100:.1f}%)")
axes[2].legend(fontsize=9)
plt.tight_layout()
plt.savefig("output_Cluster_merged.png",dpi=150,bbox_inches="tight"); plt.close()

# HAC
fig,ax=plt.subplots(figsize=(12,6))
Z=linkage(X,method="ward"); cut=Z[-(best_k),2]
dendrogram(Z,ax=ax,truncate_mode="lastp",p=40,leaf_rotation=90,leaf_font_size=8,
           color_threshold=cut)
ax.axhline(cut,color="red",lw=1.5,ls="--",label=f"k={best_k} cut")
ax.set_title("HAC Dendrogram — WA + Explicit + IAT (Ward)",fontweight="bold",fontsize=12)
ax.legend(fontsize=10)
plt.tight_layout()
plt.savefig("output_HAC_merged.png",dpi=150,bbox_inches="tight"); plt.close()
print("\n→ Saved: output_Cluster_merged.png, output_HAC_merged.png")

# Assumption checks
p_s("ASSUMPTION CHECKS")
W,p_n=stats.shapiro(ds["d_score"].sample(50,random_state=42))
print(f"[1] d_score Shapiro (n=50): W={W:.3f}, p={p_n:.4f}"
      f"  {'normal ✓' if p_n>0.05 else 'non-normal → non-param'}")
rt_out=((iat["B4_ms"]<200)|(iat["B4_ms"]>10000)).sum()
print(f"[2] RT outliers (B4_ms <200 or >10000 ms): n={rt_out}"
      f"  {'⚠ review' if rt_out>0 else '✓'}")
sil_f=silhouette_score(X,labels)
print(f"[3] Silhouette (k={best_k}): {sil_f:.3f}"
      f"  {'adequate ✓' if sil_f>=0.25 else 'weak — overlap; interpret thận trọng'}")
print(f"[4] n cluster min = {res['cluster'].value_counts().min()} (>30 để diễn giải ổn định)")

print("\n"+"="*70)
print("⏸  GATE 2 — Toàn bộ số đã chạy thực từ data. Chờ sign-off.")
print("="*70)
# patched cluster block (append to fix the merge issue)
