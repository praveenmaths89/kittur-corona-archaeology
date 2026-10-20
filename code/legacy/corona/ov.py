import geopandas as gp,cv2,numpy as np,sys,rasterio
from rasterio.windows import from_bounds
from rasterio.warp import transform
site,lon,lat=sys.argv[1],float(sys.argv[2]),float(sys.argv[3])
s2=rasterio.open('../qgis/rasters/s2_dry_20260217_truecolour.tif')
x,y=transform('EPSG:4326','EPSG:32643',[lon],[lat]); x,y=x[0],y[0]
H=6000; w=from_bounds(x-H,y-H,x+H,y+H,s2.transform); st=s2.window_transform(w); inv=~st
g=gp.read_file('../osm_raw.gpkg').to_crs(32643)
g=g.cx[x-H:x+H,y-H:y+H]
for k in 'cs':
  a=cv2.cvtColor(cv2.imread('w_%s_%s.png'%(site,k),0),cv2.COLOR_GRAY2BGR)
  for _,r in g.iterrows():
    G=r.geometry
    if r.category=='water' and G.geom_type=='Polygon':
      p=np.int32([inv*c for c in G.exterior.coords]); cv2.polylines(a,[p],True,(255,128,0),2)
    elif r.category=='place':
      p=tuple(int(v) for v in inv*(G.x,G.y)); cv2.circle(a,p,6,(0,0,255),2); cv2.putText(a,str(r['name'])[:12],(p[0]+6,p[1]),0,0.6,(0,0,255),2)
    elif r.category=='waterway':
      p=np.int32([inv*c for c in G.coords]); cv2.polylines(a,[p],False,(255,255,0),1)
  cv2.imwrite('o_%s_%s.png'%(site,k),a)
