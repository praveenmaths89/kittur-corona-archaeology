# usage: panel_metrics.py site corona_tif s2_tif label out_png
import sys,json,numpy as np,rasterio,cv2,matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from rasterio.warp import reproject,Resampling
site,ct,st,lab,out=sys.argv[1:6]
c=rasterio.open(ct); C=c.read(1).astype(np.float32)
s=rasterio.open(st); B=np.zeros((5,C.shape[0]//5,C.shape[1]//5),np.float32)
tr=c.transform*c.transform.scale(5,5)
for k in range(5): reproject(s.read(k+1),B[k],src_transform=s.transform,src_crs=s.crs,dst_transform=tr,dst_crs=c.crs,resampling=Resampling.average)
bl,gr,rd,nir,sw=B
ndvi=(nir-rd)/(nir+rd+1e-6); mndwi=(gr-sw)/(gr+sw+1e-6); ndbi=(sw-nir)/(sw+nir+1e-6)
water26=mndwi>0.1; veg26=(ndvi>0.4)&~water26; built26=(ndbi>0.0)&(ndvi<0.25)&~water26
# 1960s crude classes from CORONA tone at 10 m: water = dark & smooth, dark textured = vegetation/wet crops
C10=cv2.resize(C,(C.shape[1]//5,C.shape[0]//5),interpolation=cv2.INTER_AREA); valid=C10>8
sd=cv2.resize(np.sqrt(np.maximum(cv2.blur(C*C,(15,15))-cv2.blur(C,(15,15))**2,0)),C10.shape[::-1],interpolation=cv2.INTER_AREA)
p15=np.percentile(C10[valid],15); water60=valid&(C10<p15)&(sd<np.percentile(sd[valid],30)); veg60=valid&(C10<np.percentile(C10[valid],30))&~water60
M=dict(site=site,corona=ct,s2=st,valid_frac=float(valid.mean()),water_1960s_pct=float(100*water60[valid].mean()),darkveg_1960s_pct=float(100*veg60[valid].mean()),
       water_2026_pct=float(100*water26[valid].mean()),veg_2026_pct=float(100*veg26[valid].mean()),built_2026_pct=float(100*built26[valid].mean()),
       note='1960s classes are tone-based (crude, panchromatic); 2026 from S2 MNDWI>0.1, NDVI>0.4, NDBI>0 & NDVI<0.25; 5x5 km box')
json.dump(M,open(f'{site}/analysis/metrics.json','w'),indent=1); print(M)
rgb=np.stack([rd,gr,bl],-1); rgb=np.clip(rgb/np.percentile(rgb,99),0,1)**0.8
fig,ax=plt.subplots(1,3,figsize=(18,6.4)); cl=cv2.createCLAHE(2,(8,8))
ax[0].imshow(cl.apply(np.clip(C,0,255).astype('uint8')),cmap='gray'); ax[0].set_title(lab,fontsize=10)
ax[1].imshow(rgb); ax[1].set_title('Sentinel-2 L2A 2026 (dry season), 10 m',fontsize=10)
cls=np.zeros(ndvi.shape+(3,)); cls[veg26]=[.2,.6,.2]; cls[built26]=[.85,.3,.3]; cls[water26]=[.2,.4,.9]
ax[2].imshow(cls); ax[2].set_title(f"2026 classes: built {M['built_2026_pct']:.0f}%, veg {M['veg_2026_pct']:.0f}%, water {M['water_2026_pct']:.1f}%\n(1960s tone: water {M['water_1960s_pct']:.1f}%, dark veg {M['darkveg_1960s_pct']:.0f}%)",fontsize=10)
for a in ax: a.set_xticks([]);a.set_yticks([])
plt.tight_layout(); plt.savefig(out,dpi=110)
