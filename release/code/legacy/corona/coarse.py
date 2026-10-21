import cv2,numpy as np,rasterio,sys,json
from PIL import Image; Image.MAX_IMAGE_PIXELS=None
from rasterio.warp import transform
from rasterio.windows import from_bounds
site,cx,cy,lon,lat,f0=sys.argv[1],int(sys.argv[2]),int(sys.argv[3]),float(sys.argv[4]),float(sys.argv[5]),float(sys.argv[6])
big=Image.open('DS1045-1102DA224_b.tif')
cl=cv2.createCLAHE(2,(8,8))
s2=rasterio.open('../qgis/rasters/s2_dry_20260217_truecolour.tif')
x,y=transform('EPSG:4326','EPSG:32643',[lon],[lat]); x,y=x[0],y[0]
H=6000; w=from_bounds(x-H,y-H,x+H,y+H,s2.transform)
a=s2.read(window=w,boundless=True).astype(np.float32).mean(0)
a=cl.apply(np.clip(a/np.percentile(a,99.5)*255,0,255).astype('uint8')).astype(np.float32)
R=int(3*1000/2.2*f0/4.5*1.0)  # ~ +-3km
R=1600
cr=np.array(big.crop((cx-R,cy-R,cx+R,cy+R)))
cr=cv2.rotate(cr,cv2.ROTATE_180)
def g(z):
    z=cv2.GaussianBlur(z,(0,0),1.0); return z
best=(-1,)
for sc in np.arange(0.70,1.45,0.03):
  for ang in range(-12,13,2):
    f=1/(f0*sc)*1.0
    t=cv2.resize(cr,None,fx=1/(f0/sc),fy=1/(f0/sc),interpolation=cv2.INTER_AREA)
    t=cl.apply(t).astype(np.float32)
    M=cv2.getRotationMatrix2D((t.shape[1]/2,t.shape[0]/2),ang,1); t=cv2.warpAffine(t,M,(t.shape[1],t.shape[0]))
    h=t.shape[0]; c=int(h*0.2); t=t[c:h-c,c:h-c]
    r=cv2.matchTemplate(g(a),g(t),cv2.TM_CCOEFF_NORMED); _,mx,_,loc=cv2.minMaxLoc(r)
    if mx>best[0]: best=(mx,sc,ang,loc,t.shape)
print(best)
