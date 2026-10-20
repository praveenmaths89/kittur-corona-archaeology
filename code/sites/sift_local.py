# usage: sift_local.py <s2_5band> <piece> cx cy halfpx ds out.json  : SIFT+RANSAC affine between a scan window (centre cx,cy full-res px) and S2
import sys,numpy as np,cv2,rasterio,json
from rasterio.windows import Window
s2,pc=sys.argv[1],sys.argv[2]; cx,cy,hp,ds=map(int,sys.argv[3:7]); out=sys.argv[7]
s=rasterio.open(s2); a=s.read([3,2,1]).mean(0); a=np.clip(a/np.percentile(a[a>0],99.5)*255,0,255).astype('uint8')
r=rasterio.open(pc); x0,y0=max(0,cx-hp),max(0,cy-hp); w=Window(x0,y0,min(2*hp,r.width-x0),min(2*hp,r.height-y0))
b=r.read(1,window=w,out_shape=(int(w.height//ds),int(w.width//ds)))
cl=cv2.createCLAHE(3,(16,16)); A=cl.apply(a); B=cl.apply(b)
sf=cv2.SIFT_create(30000); k1,d1=sf.detectAndCompute(A,None); k2,d2=sf.detectAndCompute(B,(B>10).astype('uint8'))
m=cv2.BFMatcher().knnMatch(d2,d1,k=2); good=[x for x,y in m if x.distance<0.85*y.distance]
p2=np.float32([k2[x.queryIdx].pt for x in good]); p1=np.float32([k1[x.trainIdx].pt for x in good])
best=None
for th in (3,5,8):
    M,inl=cv2.estimateAffine2D(p2,p1,method=cv2.RANSAC,ransacReprojThreshold=th,maxIters=50000,confidence=0.999)
    if M is None: continue
    n=int(inl.sum()); 
    if best is None or n>best[1]: best=(M,n,inl.ravel().astype(bool),th)
M,n,inl,th=best
res=p1[inl]-(p2[inl]@M[:,:2].T+M[:,2]); rms=float(np.sqrt((res**2).sum(1).mean()))*10
# full-res scan px -> S2 px
F=M.copy(); F[:,:2]=M[:,:2]/ds; F[:,2]=M[:,2]-(M[:,:2]/ds)@[x0,y0]
sc=np.sqrt(abs(np.linalg.det(F[:,:2])))*10
json.dump(dict(F_scan_to_s2px=F.tolist(),s2=s2,piece=pc,inliers=n,good=len(good),rms_m=rms,thr=th,gsd_m=float(sc)),open(out,'w'),indent=1)
print('good',len(good),'inliers',n,'rms m',round(rms,1),'gsd',round(sc,2))
