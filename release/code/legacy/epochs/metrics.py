import rasterio,numpy as np,geopandas as gp,json,os
from rasterio.features import geometry_mask
from shapely.geometry import Point
from rasterio.warp import transform
F=gp.read_file('corona/corona1968_features_utm.gpkg')
fort=F.geometry[0]; ring=F.geometry[5]; moat=F.geometry[1]
def P(lo,la): x,y=transform('EPSG:4326','EPSG:32643',[lo],[la]); return Point(x[0],y[0])
oldS=P(74.83368,15.74663); newS=P(74.8337,15.71715)
aois={'kittur_1.5km':fort.centroid.buffer(1500),'fort_enclosure':fort,'ring_outer':ring,'moat_15m':moat.buffer(15),'oldSangoli_600m':oldS.buffer(600),'newSangolli_600m':newS.buffer(600),'sangolli_valley_3km':oldS.buffer(3000)}
rows=[]
for ep in ['L1990','L2000','L2010','S2016','S2020','S2026']:
    f=f'epochs/{ep}.tif'
    if not os.path.exists(f): continue
    s=rasterio.open(f); b=s.read(); bl,g,r,n,sw=b
    ndvi=(n-r)/(n+r+1e-6); ndbi=(sw-n)/(sw+n+1e-6); mndwi=(g-sw)/(g+sw+1e-6)
    water=mndwi>0.1; built=(ndbi>-0.05)&(ndvi<0.25)&~water
    meta=json.load(open(f'epochs/{ep}.json'))
    for k,G in aois.items():
        m=geometry_mask([G],out_shape=ndvi.shape,transform=s.transform,invert=True)&np.isfinite(ndvi)
        if m.sum()==0: continue
        rows.append(dict(epoch=ep,scenes=';'.join(d for _,d,_ in meta),aoi=k,built_frac=round(float(built[m].mean()),3),water_frac=round(float(water[m].mean()),3),ndvi=round(float(np.nanmean(ndvi[m])),3),built_ha=round(float(built[m].sum()*100/1e4),1),water_ha=round(float(water[m].sum()*100/1e4),1)))
    # ring/moat contrast: NDVI inside minus 60 m ring buffer
    for k,G in [('ring_outer',ring),('fort_enclosure',fort)]:
        inn=geometry_mask([G],out_shape=ndvi.shape,transform=s.transform,invert=True); out=geometry_mask([G.buffer(80).difference(G)],out_shape=ndvi.shape,transform=s.transform,invert=True)
        rows.append(dict(epoch=ep,aoi=k+'_contrast',ndvi=round(float(np.nanmean(ndvi[inn])-np.nanmean(ndvi[out])),3),built_frac=round(float(built[inn].mean()-built[out].mean()),3)))
import pandas as pd
d=pd.DataFrame(rows); d.to_csv('epochs/metrics.csv',index=False); print(d.to_string())
