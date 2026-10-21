# usage: sift_locate.py <wide_s2_5band.tif> <scan piece tif> [ds=8] -> similarity fit (scan px -> S2 px), inliers
import sys,numpy as np,cv2,rasterio,json
s=rasterio.open(sys.argv[1]); ds=int(sys.argv[3]) if len(sys.argv)>3 else 8
a=s.read([3,2,1]).mean(0); a=np.clip(a/np.percentile(a[a>0],99.5)*255,0,255).astype('uint8')
cl=cv2.createCLAHE(3,(16,16)); sf=cv2.SIFT_create(40000)
g=float(sys.argv[4]) if len(sys.argv)>4 else 1.0   # downscale S2 by g
A=cl.apply(cv2.resize(a,None,fx=1/g,fy=1/g,interpolation=cv2.INTER_AREA))
r=rasterio.open(sys.argv[2]); b=r.read(1,out_shape=(r.height//ds,r.width//ds)); B=cl.apply(b)
k1,d1=sf.detectAndCompute(A,None); k2,d2=sf.detectAndCompute(B,(B>10).astype('uint8'))
m=cv2.BFMatcher().knnMatch(d2,d1,k=2); good=[x for x,y in m if x.distance<0.8*y.distance]
p2=np.float32([k2[x.queryIdx].pt for x in good]); p1=np.float32([k1[x.trainIdx].pt for x in good])
M,inl=cv2.estimateAffinePartial2D(p2,p1,method=cv2.RANSAC,ransacReprojThreshold=4,maxIters=20000)
ni=int(inl.sum()) if inl is not None else 0
sc=np.hypot(M[0,0],M[1,0]) if M is not None else 0; ang=np.degrees(np.arctan2(M[1,0],M[0,0])) if M is not None else 0
print(json.dumps(dict(piece=sys.argv[2],good=len(good),inliers=ni,scale_S2px_per_thumbpx=float(sc),gsd_m=float(sc*10*g/ds),rot_deg=float(ang),M=(M.tolist() if M is not None else None),ds=ds,g=g)))
