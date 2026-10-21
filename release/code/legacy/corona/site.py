import cv2,numpy as np,json,sys,rasterio
from PIL import Image; Image.MAX_IMAGE_PIXELS=None
from rasterio.warp import transform
from rasterio.windows import from_bounds
site,lon,lat=sys.argv[1],float(sys.argv[2]),float(sys.argv[3])
J=json.load(open('gcp_kittur.json')); An=np.array(J['An'])
s2=rasterio.open('../qgis/rasters/s2_dry_20260217_truecolour.tif')
def win(lo,la):
  x,y=transform('EPSG:4326','EPSG:32643',[lo],[la]); x,y=x[0],y[0]; H=6000
  return from_bounds(x-H,y-H,x+H,y+H,s2.transform)
wk=win(74.7911,15.6004); ws=win(lon,lat)
off=np.array([ws.col_off-wk.col_off, ws.row_off-wk.row_off])
A=An.copy(); A[:,2]-=off
J2={'A':A.tolist(),'An':A.tolist()}
a=s2.read(window=ws,boundless=True).astype(np.float32).mean(0); cl=cv2.createCLAHE(2,(8,8))
a=cl.apply(np.clip(a/np.percentile(a[a>0],99.5)*255,0,255).astype('uint8')); cv2.imwrite('w_%s_s.png'%site,a)
json.dump(J2,open('gcp_%s.json'%site,'w'))
Ai=cv2.invertAffineTransform(A); print('centre full-res',Ai@[600,600,1])
