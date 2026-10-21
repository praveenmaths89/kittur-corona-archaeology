import cv2,numpy as np,rasterio,sys,json
from PIL import Image; Image.MAX_IMAGE_PIXELS=None
from rasterio.warp import transform
from rasterio.windows import from_bounds
site,cx,cy,lon,lat,sc,ang,lx,ly=sys.argv[1],int(sys.argv[2]),int(sys.argv[3]),float(sys.argv[4]),float(sys.argv[5]),float(sys.argv[6]),float(sys.argv[7]),int(sys.argv[8]),int(sys.argv[9])
f0=4.5
big=Image.open('DS1045-1102DA224_b.tif'); cl=cv2.createCLAHE(2,(8,8))
s2=rasterio.open('../qgis/rasters/s2_dry_20260217_truecolour.tif')
x,y=transform('EPSG:4326','EPSG:32643',[lon],[lat]); x,y=x[0],y[0]
H=6000; w=from_bounds(x-H,y-H,x+H,y+H,s2.transform); st=s2.window_transform(w)
a=s2.read(window=w,boundless=True).astype(np.float32).mean(0)
a=cl.apply(np.clip(a/np.percentile(a,99.5)*255,0,255).astype('uint8')).astype(np.float32)
R=1600; k=f0/sc  # full-res px per 10m px
# map full-res pixel (u,v) -> s2 window pixel: rotate180 about crop, scale 1/k, rotate ang about template centre, shift
# build directly: crop rotated coords r=(2R-(u-cx+R), 2R-(v-cy+R)); t=r/k ; rotate by ang about (n/2,n/2) ; minus c ; plus loc
n=int(round(2*R/k)); c=int(n*0.2)
Mr=cv2.getRotationMatrix2D((n/2,n/2),ang,1)
def fwd(u,v):
    r=np.stack([(2*R-(u-cx+R))/k,(2*R-(v-cy+R))/k,np.ones_like(u)],0)
    t=Mr@r; return t[0]-c+lx, t[1]-c+ly
# warp corona into s2 window grid: need inverse. Build affine from 3 points.
U=np.array([cx-R,cx+R,cx-R],float); V=np.array([cy-R,cy-R,cy+R],float)
X,Y=fwd(U,V); A=cv2.getAffineTransform(np.float32(np.c_[U,V]),np.float32(np.c_[X,Y]))
# full-res region big enough
R2=3200
cr=np.array(big.crop((cx-R2,cy-R2,cx+R2,cy+R2))).astype(np.float32)
A2=A.copy(); A2[:,2]+=A[:,:2]@[cx-R2,cy-R2]
cr=cv2.GaussianBlur(cr,(0,0),k/2.5)
wc=cv2.warpAffine(cr,A2,(a.shape[1],a.shape[0]),flags=cv2.INTER_AREA,borderValue=0)
mask=cv2.warpAffine(np.ones_like(cr),A2,(a.shape[1],a.shape[0]))>0.5
wc8=np.clip(wc,0,255).astype('uint8'); wc8=cl.apply(wc8).astype(np.float32)
cv2.imwrite('w_%s_c.png'%site,wc8); cv2.imwrite('w_%s_s.png'%site,a)
# patch matching
P=[];Q=[]; ps=40; srch=25
for yy in range(srch+ps,a.shape[0]-ps-srch,30):
  for xx in range(srch+ps,a.shape[1]-ps-srch,30):
    if not mask[yy-ps:yy+ps,xx-ps:xx+ps].all(): continue
    t=wc8[yy-ps:yy+ps,xx-ps:xx+ps]
    if t.std()<8: continue
    S=a[yy-ps-srch:yy+ps+srch,xx-ps-srch:xx+ps+srch]
    r=cv2.matchTemplate(S,t,cv2.TM_CCOEFF_NORMED); _,mx,_,l=cv2.minMaxLoc(r)
    r2=r.copy(); cv2.circle(r2,l,5,-1,-1); sec=r2.max()
    if mx>0.35 and mx-sec>0.05:
        P.append((xx,yy)); Q.append((xx+l[0]-srch,yy+l[1]-srch))
P=np.float32(P);Q=np.float32(Q); print('patches',len(P))
Ai=cv2.invertAffineTransform(A)
Mh,inl=cv2.estimateAffine2D(P,Q,method=cv2.RANSAC,ransacReprojThreshold=2.5)
inl=inl.ravel()==1; print('inliers',inl.sum())
Pf=(Ai[:,:2]@P[inl].T).T+Ai[:,2]     # full-res pixels
E=np.array([st*(q[0],q[1]) for q in Q[inl]])
json.dump(dict(P=Pf.tolist(),E=E.tolist(),A=A.tolist()),open('gcp_%s.json'%site,'w'))
