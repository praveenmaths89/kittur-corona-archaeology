import numpy as np,rasterio,cv2,json
from rasterio.warp import reproject,Resampling,transform
R='../qgis/rasters/'
K=transform('EPSG:4326','EPSG:32643',[74.785],[15.598]); KX,KY=K[0][0],K[1][0]
nd=rasterio.open(R+'s2_dry_20260217_ndvi.tif')
crops={'kittur_DA224':'corona_1968_kittur.tif','sangolli_DF224':'corona_1968_sangolli.tif','oldsangoli_DA223':'corona_1968DA223_oldsangoli.tif','tigadi_DA223':'corona_1968DA223_tigadi.tif','sampgaon_DA223':'corona_1968DA223_sampgaon.tif','bailhongal_DA223':'corona_1968DA223_bailhongal.tif'}
rows=[]
for nm,f in crops.items():
    r=rasterio.open(R+f); A=r.read(1).astype(np.float32); valid=A>5
    B=cv2.GaussianBlur(A,(0,0),4); thr=np.percentile(B[valid],4)
    m=((B<thr)&valid).astype(np.uint8); m=cv2.morphologyEx(m,cv2.MORPH_OPEN,np.ones((7,7),np.uint8))
    n,lab,st,cen=cv2.connectedComponentsWithStats(m)
    W=np.zeros(A.shape,np.float32); reproject(nd.read(1).astype(np.float32),W,src_transform=nd.transform,src_crs=nd.crs,dst_transform=r.transform,dst_crs=r.crs,resampling=Resampling.bilinear)
    for i in range(1,n):
        a=st[i,4]*4/1e4
        if a<0.2 or a>40: continue
        bw,bh=st[i,2],st[i,3]; fill=st[i,4]/(bw*bh)
        if fill<0.35 or max(bw,bh)/min(bw,bh)>4: continue
        x,y=r.transform*(cen[i][0],cen[i][1]); lo,la=transform('EPSG:32643','EPSG:4326',[x],[y])
        msk=lab==i; w26=float(np.mean(W[msk]<0.0)); veg=float(np.mean(W[msk]>0.4))
        st26='water 2026' if w26>0.5 else ('partly water 2026' if w26>0.1 else ('vegetated/cropped 2026' if veg>0.5 else 'dry/other 2026'))
        rows.append(dict(crop=nm,lat=round(la[0],5),lon=round(lo[0],5),area68_ha=round(a,2),water2026_frac=round(w26,2),status2026=st26,dist_kittur_km=round(np.hypot(x-KX,y-KY)/1000,1)))
json.dump(rows,open('tanks_1968.json','w'),indent=1)
import collections; print(len(rows)); print(collections.Counter((r['crop'],r['status2026']) for r in rows))
for r in sorted(rows,key=lambda r:-r['area68_ha'])[:25]: print(r)
