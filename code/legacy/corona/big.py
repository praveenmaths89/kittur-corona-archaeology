import cv2,numpy as np,rasterio,sys
from rasterio.warp import transform
from rasterio.windows import from_bounds
site,lon,lat=sys.argv[1],float(sys.argv[2]),float(sys.argv[3])
s2=rasterio.open('../qgis/rasters/s2_dry_20260217_truecolour.tif')
x,y=transform('EPSG:4326','EPSG:32643',[lon],[lat]); x,y=x[0],y[0]; H=14000
w=from_bounds(x-H,y-H,x+H,y+H,s2.transform)
S=s2.read(window=w,boundless=True,out_shape=(3,700,700)).astype(np.float32).mean(0)
S=cv2.GaussianBlur(S,(0,0),1)
c=cv2.imread('w_%s_c.png'%site,0).astype(np.float32)
C=cv2.resize(cv2.GaussianBlur(c,(0,0),4),(300,300),interpolation=cv2.INTER_AREA)
best=[]
for sc in np.arange(0.85,1.2,0.05):
 for sy in np.arange(0.85,1.2,0.05):
  for ang in [-3,0,3]:
    M=cv2.getRotationMatrix2D((150,150),ang,sc); M[1]*=sy; M[1,2]=150-(M[1,0]*150+M[1,1]*150)
    t=cv2.warpAffine(C,M,(300,300))[70:230,70:230]
    if (t==0).mean()>0.01: continue
    r=cv2.matchTemplate(S,t,cv2.TM_CCOEFF_NORMED); _,mx,_,l=cv2.minMaxLoc(r)
    best.append((round(mx,3),round(sc,2),round(sy,2),ang,((l[0]+80-350)*40,(l[1]+80-350)*40)))
best.sort(reverse=True); print(best[:6])
