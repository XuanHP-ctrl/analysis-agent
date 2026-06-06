"""
Fish sauce — Phần 3 (D-score + Dissonance) + Cluster merged (GATE 2 approved)
Data: data/Word_association.xlsx + data/Data_IAT.xlsx
"""
import warnings; warnings.filterwarnings("ignore")
import pandas as pd, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats
from scipy.cluster.hierarchy import linkage, dendrogram
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score

WA_PATH  = "data/Word_association.xlsx"
IAT_PATH = "data/Data_IAT.xlsx"
EXPL     = ["liking","tasty","packaging","protein","healthy","price","ingre","familar","popular"]

def recode_region_vi(s):
    m={"Bắc":"North","Bắc Trung Bộ":"Centre","Nam Trung Bộ":"Centre","Nam":"South"}
    return s.astype(str).str.strip().map(m)
def recode_region_en(s):
    m={"north":"North","northern":"North","central":"Centre","south":"South","southern":"South"}
    return s.astype(str).str.strip().str.lower().map(m)
def d_strength(d):
    a=abs(d)
    if   a<0.15: return "None"
    elif a<0.30: return "Small"
    elif a<0.50: return "Medium"
    elif a<0.70: return "Strong"
    else:        return "Very strong"
def d_direction(d):
    if   d> 0.15: return "Implicit pro-TT"
    elif d<-0.15: return "Implicit pro-CN"
    else:         return "No clear link"

# Load WA with wa_t_ / wa_e_ prefixes to avoid column collisions
df_t=pd.read_excel(WA_PATH, sheet_name="Binary (topic)")
df_e=pd.read_excel(WA_PATH, sheet_name="Binary (element)")
for df in [df_t,df_e]:
    df["Region3"]=recode_region_vi(df["region"])
df_t=df_t.dropna(subset=["Region3"]); df_e=df_e.dropna(subset=["Region3"])
terms_t=[c for c in df_t.columns if c not in ("Mã đăng nhập","region","gender","age","user","frequency","Region3")]
terms_e=[c for c in df_e.columns if c not in ("Mã đăng nhập","region","gender","age","user","frequency","Region3")]

meta=["Mã đăng nhập","Region3","user"]
df_t2=df_t[meta+terms_t].copy().rename(columns={t:f"wt_{t}" for t in terms_t})
df_e2=df_e[["Mã đăng nhập"]+terms_e].copy().rename(columns={t:f"we_{t}" for t in terms_e})
wt_cols=[f"wt_{t}" for t in terms_t]; we_cols=[f"we_{t}" for t in terms_e]
wa=df_t2.merge(df_e2,on="Mã đăng nhập",how="inner").rename(columns={"Mã đăng nhập":"ID","user":"user_vi"})

# Load IAT
iat=pd.read_excel(IAT_PATH, sheet_name="RawData")
iat["Region3"]=recode_region_en(iat["region"])
iat["d_strength"] =iat["d_score"].apply(d_strength)
iat["d_direction"]=iat["d_score"].apply(d_direction)
iat["pref_expl"]  =iat["liking_TT"]-iat["liking_CN"]
iat["quadrant"]=np.select(
    [(iat["pref_expl"]>=0)&(iat["d_score"]>=0),
     (iat["pref_expl"]>=0)&(iat["d_score"]< 0),
     (iat["pref_expl"]< 0)&(iat["d_score"]< 0),
     (iat["pref_expl"]< 0)&(iat["d_score"]>=0)],
    ["Consistent pro-TT","Dissonance(TT expl/CN impl)",
     "Consistent pro-CN","Dissonance(CN expl/TT impl)"],default="?")
iat["dissonant"]=iat["quadrant"].str.contains("Dissonance").astype(int)
iat["user_vi"]=iat["user"].map({"TT":"Truyền thống","CN":"Công nghiệp"})

expl_cols=[f"{a}_TT" for a in EXPL]+[f"{a}_CN" for a in EXPL]
iat_sel=iat[["ID","d_score","d_strength","d_direction","pref_expl",
             "dissonant","quadrant","user_vi","Region3"]+expl_cols].copy()

# Merge all 3 sources
merged=wa.merge(iat_sel,on="ID",how="inner",suffixes=("_wa","_iat"))
merged=merged.dropna(subset=["d_score"]+expl_cols)
user_col="user_vi_wa" if "user_vi_wa" in merged.columns else "user_vi"
reg_col ="Region3_wa" if "Region3_wa" in merged.columns else "Region3"

# Cluster
all_feat=expl_cols+["d_score"]+wt_cols+we_cols
Xdf=merged[all_feat].dropna(); idx=Xdf.index
X=StandardScaler().fit_transform(Xdf)
best_k=2
km=KMeans(n_clusters=best_k,random_state=42,n_init=30)
labels=km.fit_predict(X)
res=merged.loc[idx].copy(); res["cluster"]=labels+1

# PCA 2D + HAC
pca2=PCA(n_components=2); X2=pca2.fit_transform(X)
fig,axes=plt.subplots(1,3,figsize=(21,7))
clr={1:"#e74c3c",2:"#2ecc71"}
cm=res.groupby("cluster")[["liking_TT","liking_CN","d_score"]].mean().round(3)
for c in sorted(res["cluster"].unique()):
    mask=res["cluster"]==c; r=cm.loc[c]
    lbl=f"C{c} n={mask.sum()} | TT={r['liking_TT']:.1f} CN={r['liking_CN']:.1f} d={r['d_score']:.3f}"
    axes[0].scatter(X2[mask,0],X2[mask,1],c=clr[c],label=lbl,alpha=0.65,s=55,edgecolors="white",lw=0.3)
axes[0].set_title(f"Segments (k={best_k}) — WA+Explicit+IAT",fontweight="bold")
axes[0].set_xlabel(f"PC1 ({pca2.explained_variance_ratio_[0]*100:.1f}%)")
axes[0].set_ylabel(f"PC2 ({pca2.explained_variance_ratio_[1]*100:.1f}%)")
axes[0].legend(fontsize=8)
uc={"Truyền thống":"#e74c3c","Công nghiệp":"#3498db"}
for usr,sub in res.groupby(user_col):
    mask2=res.index.isin(sub.index)
    axes[1].scatter(X2[mask2,0],X2[mask2,1],c=uc.get(usr,"grey"),
                    label=f"{usr}(n={mask2.sum()})",alpha=0.5,s=40,edgecolors="white",lw=0.2)
axes[1].set_title("User overlay",fontweight="bold")
axes[1].set_xlabel(f"PC1 ({pca2.explained_variance_ratio_[0]*100:.1f}%)")
axes[1].set_ylabel(f"PC2 ({pca2.explained_variance_ratio_[1]*100:.1f}%)")
axes[1].legend(fontsize=10)
dc={"Implicit pro-TT":"#e74c3c","Implicit pro-CN":"#3498db","No clear link":"#95a5a6"}
for dd,sub in res.groupby("d_direction"):
    mask3=res.index.isin(sub.index)
    axes[2].scatter(X2[mask3,0],X2[mask3,1],c=dc.get(dd,"grey"),
                    label=f"{dd}(n={mask3.sum()})",alpha=0.55,s=40,edgecolors="white",lw=0.2)
axes[2].set_title("IAT direction overlay",fontweight="bold")
axes[2].set_xlabel(f"PC1 ({pca2.explained_variance_ratio_[0]*100:.1f}%)")
axes[2].set_ylabel(f"PC2 ({pca2.explained_variance_ratio_[1]*100:.1f}%)")
axes[2].legend(fontsize=9)
plt.tight_layout()
plt.savefig("output_Cluster_merged.png",dpi=150,bbox_inches="tight"); plt.close()

fig,ax=plt.subplots(figsize=(12,6))
Z=linkage(X,method="ward"); cut=Z[-(best_k),2]
dendrogram(Z,ax=ax,truncate_mode="lastp",p=40,leaf_rotation=90,leaf_font_size=8,color_threshold=cut)
ax.axhline(cut,color="red",lw=1.5,ls="--",label=f"k={best_k} cut")
ax.set_title("HAC Dendrogram — WA + Explicit + IAT",fontweight="bold")
ax.legend(); plt.tight_layout()
plt.savefig("output_HAC_merged.png",dpi=150,bbox_inches="tight"); plt.close()
print("Done. Saved: output_Cluster_merged.png, output_HAC_merged.png")
