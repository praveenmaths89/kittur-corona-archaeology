import rasterio,geopandas as gp,numpy as np,shapely
from shapely.geometry import Polygon,LineString,Point
T=rasterio.open('qgis/rasters/corona_1968_kittur.tif').transform
def P(pts): return [T*(c+0.5,r+0.5) for c,r in pts]
def ell(c,r,a,b,n=48): return [ (c+a*np.cos(t), r+b*np.sin(t)) for t in np.linspace(0,2*np.pi,n,endpoint=False)]
F=[]
# vertices in corona_1968_kittur.tif pixel coords (col,row), 2 m px; digitised by eye from CLAHE crops
F.append(('main enclosure inner wall line (lower fort?)','polygon',Polygon(P([(1143,1173),(1230,1172),(1323,1180),(1322,1270),(1317,1357),(1240,1373),(1190,1368),(1163,1353),(1145,1320),(1143,1273)]))))
F.append(('north/west moat (dark band)','line',LineString(P([(1347,1125),(1313,1118),(1220,1105),(1150,1095),(1087,1080),(1105,1140),(1115,1200),(1120,1287),(1135,1340)]))))
F.append(('outer wall/ditch line east (tree-lined bastions)','line',LineString(P([(1340,1135),(1350,1200),(1347,1280),(1350,1360),(1335,1395)]))))
F.append(('round pond inside NW corner','polygon',Polygon(P(ell(1170,1183,14,13)))))
F.append(('round pond east of enclosure','polygon',Polygon(P(ell(1383,1270,20,19)))))
F.append(('SW concentric structure - outer ring','polygon',Polygon(P(ell(1130,1521,70,79)))))
F.append(('SW concentric structure - middle ring','polygon',Polygon(P(ell(1131,1517,52,58)))))
F.append(('SW concentric structure - inner core (dark centre)','polygon',Polygon(P(ell(1133,1515,33,40)))))
g=gp.GeoDataFrame({'feature':[f[0] for f in F],'kind':[f[1] for f in F],'source':'CORONA KH-4A DS1045-1102DA224 31 Jan 1968 (USGS); digitised by eye; positional error ~50-100 m (georef) + ~10 m (digitising)','status':'tentative'},geometry=[f[2] for f in F],crs=32643)
g['area_ha']=[round(x.area/1e4,2) if x.geom_type=='Polygon' else None for x in g.geometry]
g['length_m']=[round(x.length) for x in g.geometry]
b=[x.bounds for x in g.geometry]; g['ew_m']=[round(x[2]-x[0]) for x in b]; g['ns_m']=[round(x[3]-x[1]) for x in b]
print(g.drop(columns=['geometry','source']).to_string())
g.to_crs(4326).to_file('qgis/kittur_vectors.gpkg',layer='corona1968_features')
g.to_file('corona/corona1968_features_utm.gpkg')
