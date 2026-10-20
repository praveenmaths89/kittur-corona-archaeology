# georeference a CORONA piece crop to a reference GeoTIFF (same grid) by SIFT; usage: g2r.py piece.tif cx cy halfsize ref.tif out.tif [rot180]
import cv2,numpy as np,rasterio,sys
from PIL import Image; Image.MAX_IMAGE_PIXELS=None
f,cx,cy,R,ref,out=sys.argv[1],int(sys.argv[2]),int(sys.argv[3]),int(sys.argv[4]),sys.argv[5],sys.argv[6]
im=Image.open(f); W,H=im.size
box=(max(0,cx-R),max(0,cy-R),min(W,cx+R),min(H,cy+R)); cr=np.array(im.crop(box))
r=rasterio.open(ref); A=r.read(1)
cl=cv2.createCLAHE(2,(8,8)); sift=cv2.SIFT_create(15000)
def feat(x): x=cl.apply(x); return sift.detectAndCompute(x,(x>5).astype('uint8'))
k1,d1=feat(cr); k2,d2=feat(A)
m=cv2.BFMatcher().knnMatch(d1,d2,k=2); g=[a for a,b in m if a.distance<0.8*b.distance]
P=np.float32([k1[x.queryIdx].pt for x in g]); Q=np.float32([k2[x.trainIdx].pt for x in g])
M,inl=cv2.estimateAffine2D(P,Q,method=cv2.RANSAC,ransacReprojThreshold=4,maxIters=50000); i=inl.ravel()==1
# refine with 2nd-order polynomial on inliers
def X(p): x,y=p[:,0],p[:,1]; return np.c_[np.ones_like(x),x,y,x*x,x*y,y*y]
cx_,cy_=np.linalg.lstsq(X(P[i]),Q[i,0],rcond=None)[0],np.linalg.lstsq(X(P[i]),Q[i,1],rcond=None)[0]
pred=np.c_[X(P[i])@cx_,X(P[i])@cy_]; res=Q[i]-pred; ok=np.sqrt((res**2).sum(1))<3
cx_,cy_=np.linalg.lstsq(X(P[i][ok]),Q[i][ok,0],rcond=None)[0],np.linalg.lstsq(X(P[i][ok]),Q[i][ok,1],rcond=None)[0]
res=Q[i][ok]-np.c_[X(P[i][ok])@cx_,X(P[i][ok])@cy_]
rms=np.sqrt((res**2).sum(1).mean())*abs(r.transform.a)
# inverse map: for each ref pixel find crop pixel -> fit inverse poly
ci=np.linalg.lstsq(X(Q[i][ok]),P[i][ok,0],rcond=None)[0]; ri=np.linalg.lstsq(X(Q[i][ok]),P[i][ok,1],rcond=None)[0]
jj,ii=np.meshgrid(np.arange(A.shape[1],dtype=np.float32),np.arange(A.shape[0],dtype=np.float32)); G=np.c_[np.ones(jj.size),jj.ravel(),ii.ravel(),jj.ravel()**2,jj.ravel()*ii.ravel(),ii.ravel()**2]
u=(G@ci).reshape(A.shape).astype(np.float32); v=(G@ri).reshape(A.shape).astype(np.float32)
o=cv2.remap(cr,u,v,cv2.INTER_LINEAR,borderValue=0)
p=r.profile.copy(); p.update(count=1,dtype='uint8',nodata=0)
with rasterio.open(out,'w',**p) as d: d.write(o,1); d.update_tags(SOURCE=f,GCPS=str(int(ok.sum())),RMS_M_vs_ref=f'{rms:.1f}',REF=ref)
print(out,'matches',len(g),'inliers',int(i.sum()),'poly-ok',int(ok.sum()),'RMS m vs ref',round(rms,1),'coverage',round(float((o>0).mean()),2))
