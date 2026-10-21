import rasterio,numpy as np,cv2
from rasterio.warp import transform
from rasterio.windows import from_bounds
s=rasterio.open('../qgis/rasters/s2_dry_20260217_truecolour.tif')
lo,la=74.80,15.77
x,y=transform('EPSG:4326','EPSG:32643',[lo],[la]);x,y=x[0],y[0]
H=9000
w=from_bounds(x-H,y-H,x+H,y+H,s.transform)
a=s.read(window=w,out_shape=(3,int(2*H/35.2),int(2*H/35.2))).astype(np.float32).mean(0)
cl=cv2.createCLAHE(2,(8,8))
def prep(z):
    z=cl.apply(np.clip(z/np.percentile(z,99.5)*255,0,255).astype('uint8')).astype(np.float32)
    return cv2.GaussianBlur(z,(0,0),1.5)
t0=prep(a)
best=[]
for p in 'bc':
    im=cv2.imread(f'/tmp/da223_{p}_16.png',0).astype(np.float32); I=prep(im)
    for sc in np.arange(0.8,1.25,0.05):
        for ang in range(-10,11,2):
            t=cv2.resize(t0,None,fx=sc,fy=sc); M=cv2.getRotationMatrix2D((t.shape[1]/2,t.shape[0]/2),ang,1)
            t=cv2.warpAffine(t,M,(t.shape[1],t.shape[0])); c=int(t.shape[0]*0.18); t=t[c:-c,c:-c]
            if t.shape[0]>=I.shape[0]: continue
            r=cv2.matchTemplate(I,t,cv2.TM_CCOEFF_NORMED); _,mx,_,loc=cv2.minMaxLoc(r)
            best.append((mx,p,sc,ang,loc,t.shape))
best.sort(reverse=True); [print(b) for b in best[:6]]
mx,p,sc,ang,loc,sh=best[0]
im=cv2.imread(f'/tmp/da223_{p}_16.png',0)
crop=im[loc[1]:loc[1]+sh[0],loc[0]:loc[0]+sh[1]]
t=cv2.resize(t0,None,fx=sc,fy=sc); M=cv2.getRotationMatrix2D((t.shape[1]/2,t.shape[0]/2),ang,1)
t=cv2.warpAffine(t,M,(t.shape[1],t.shape[0])); c=int(t.shape[0]*0.18); t=t[c:-c,c:-c]
cv2.imwrite('/tmp/chk223.png',np.hstack([cv2.equalizeHist(crop),t.astype('uint8')]))
