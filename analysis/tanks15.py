import numpy as np,rasterio,json,geopandas as gp
from rasterio.features import geometry_mask
from shapely.geometry import Point
R='../qgis/rasters/'
m=rasterio.open(R+'corona_1968_mosaic15km_10m.tif'); A=m.read(1).astype(float); S=rasterio.open(R+'corona_1968_mosaic15km_source.tif').read(1)
nd=rasterio.open(R+'s2_dry_20260217_ndvi.tif')
g=gp.read_file('../osm_raw.gpkg'); w=g[(g.category=='water')&g.geom_type.isin(['Polygon','MultiPolygon'])].to_crs(32643)
k=gp.GeoSeries([Point(74.785,15.598)],crs=4326).to_crs(32643)[0]
w=w[(w.centroid.distance(k)<15000)&(w.area>1e4)].copy()
rows=[]
for i,r in w.iterrows():
    gin=r.geometry; ring=gin.buffer(150).difference(gin.buffer(40))
    mi=~geometry_mask([gin],A.shape,m.transform); mo=~geometry_mask([ring],A.shape,m.transform)
    cov=float((S[mi]>0).mean()) if mi.any() else 0
    lo,la=gp.GeoSeries([gin.centroid],crs=32643).to_crs(4326)[0].coords[0]
    d=dict(osm_id=r.get('osm_id'),name=r.get('name'),lat=round(la,5),lon=round(lo,5),area2026_ha=round(gin.area/1e4,1),dist_km=round(gin.centroid.distance(k)/1000,1),corona_cover=round(cov,2),src={1:'DA224',2:'DF224'}.get(int(np.bincount(S[mi]).argmax()) if mi.any() else 0,'none'))
    if cov>0.8 and (S[mo]>0).mean()>0.8:
        ti,to=np.median(A[mi&(S>0)]),np.median(A[mo&(S>0)]); d['tone_ratio_in_out']=round(ti/to,2)
        d['status_1968']='dark (water/wet) in 1968: pre-1968 tank' if ti/to<0.75 else ('intermediate' if ti/to<0.9 else 'not distinguishable from surroundings in 1968: new or enlarged after 1968 (tentative)')
    else: d['status_1968']='outside georeferenced 1968 coverage'
    rows.append(d)
rows.sort(key=lambda d:-d['area2026_ha']); json.dump(rows,open('osm_tanks_vs_1968.json','w'),indent=1,default=str)
import collections; print(len(rows),collections.Counter(d['status_1968'] for d in rows))
for d in rows[:40]: print(d)
