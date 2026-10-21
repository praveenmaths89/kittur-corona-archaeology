import geopandas as gp,cv2,numpy as np,sys,rasterio,json
from rasterio.windows import from_bounds
from rasterio.warp import transform
site,lon,lat,dx,dy=sys.argv[1],float(sys.argv[2]),float(sys.argv[3]),float(sys.argv[4]),float(sys.argv[5])
s2=rasterio.open('../qgis/rasters/s2_dry_20260217_truecolour.tif')
x,y=transform('EPSG:4326','EPSG:32643',[lon],[lat]); x,y=x[0],y[0]
H=6000; w=from_bounds(x-H,y-H,x+H,y+H,s2.transform); st=s2.window_transform(w); inv=~st
g=gp.read_file('../osm_raw.gpkg').to_crs(32643).cx[x-H:x+H,y-H:y+H]
g=g[(g.category=='water')&(g.geom_type=='Polygon')]
c=cv2.imread('w_%s_c.png'%site,0); s=cv2.imread('w_%s_s.png'%site,0)
tiles=[];info=[]; r=50
for i,(_,q) in enumerate(g.iterrows()):
  px,py=inv*(q.geometry.centroid.x,q.geometry.centroid.y); px,py=int(px),int(py)
  cx,cy=int(px-dx),int(py-dy)  # expected in corona frame
  if not(r<=px<1200-r and r<=py<1200-r and r<=cx<1200-r and r<=cy<1200-r): continue
  A=c[cy-r:cy+r,cx-r:cx+r]; B=s[py-r:py+r,px-r:px+r].copy()
  if (A==0).mean()>0.3: continue
  B=cv2.cvtColor(B,cv2.COLOR_GRAY2BGR); p=np.int32([np.array(inv*cc)-[px-r,py-r] for cc in q.geometry.exterior.coords]); cv2.polylines(B,[p],True,(255,128,0),1)
  A=cv2.cvtColor(A,cv2.COLOR_GRAY2BGR)
  T=np.hstack([cv2.resize(A,(200,200)),cv2.resize(B,(200,200))]); cv2.putText(T,str(len(info)),(3,18),0,0.6,(0,0,255),2)
  for X in (100,300): cv2.drawMarker(T,(X,100),(0,255,0),cv2.MARKER_CROSS,12,1)
  tiles.append(T); info.append((len(info),px,py,cx,cy,q['name']))
print(len(tiles)); json.dump(info,open('sheet_%s.json'%site,'w'))
for k in range(0,len(tiles),8):
  t=tiles[k:k+8]; 
  while len(t)<8: t.append(np.zeros_like(tiles[0]))
  cv2.imwrite('sheet_%s_%d.png'%(site,k//8),np.vstack([np.hstack(t[j:j+2]) for j in range(0,8,2)]))
