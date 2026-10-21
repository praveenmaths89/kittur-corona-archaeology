import cv2,numpy as np,json,sys,rasterio
from rasterio.warp import transform
from rasterio.windows import from_bounds
src,slon,slat,site,lon,lat=sys.argv[1],float(sys.argv[2]),float(sys.argv[3]),sys.argv[4],float(sys.argv[5]),float(sys.argv[6])
J=json.load(open('gcp_%s.json'%src)); An=np.array(J['An'])
s2=rasterio.open('../qgis/rasters/s2_dry_20260217_truecolour.tif')
def win(lo,la):
  x,y=transform('EPSG:4326','EPSG:32643',[lo],[la]); x,y=x[0],y[0]; H=6000
  return from_bounds(x-H,y-H,x+H,y+H,s2.transform)
wk=win(slon,slat); ws=win(lon,lat)
A=An.copy(); A[:,2]-=[ws.col_off-wk.col_off, ws.row_off-wk.row_off]
a=s2.read(window=ws,boundless=True).astype(np.float32).mean(0); cl=cv2.createCLAHE(2,(8,8))
a=cl.apply(np.clip(a/np.percentile(a[a>0],99.5)*255,0,255).astype('uint8')); cv2.imwrite('w_%s_s.png'%site,a)
json.dump({'A':A.tolist(),'An':A.tolist(),'lonlat':[lon,lat]},open('gcp_%s.json'%site,'w'))
