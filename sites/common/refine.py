# usage: refine.py <s2_5band> <piece> rot cx cy  -- cx,cy: approx full-res scan px of the site; searches gsd/angle/shift by NCC (20 m), then
# patch-NCC tie points (10 m) and an affine with RMS on held-out checkpoints. Output <site>/corona/<fid>_fit.json
import sys,json,numpy as np,cv2,rasterio
from rasterio.windows import Window
s2f,pc,rot,cx,cy=sys.argv[1],sys.argv[2],int(sys.argv[3]),int(sys.argv[4]),int(sys.argv[5])
gs=[float(x) for x in sys.argv[6].split(',')] if len(sys.argv)>6 else list(np.arange(1.6,4.6,0.2))
s=rasterio.open(s2f); S=s.read([3,2,1]).mean(0); n=S.shape[0]
cl=cv2.createCLAHE(2,(8,8))
def pr(z,sig=1.0):
    v=z[z>0] if (z>0).any() else z.ravel(); z=np.clip(z/np.percentile(v,99.5)*255,0,255).astype('uint8'); return cv2.GaussianBlur(cl.apply(z).astype(np.float32),(0,0),sig)
S20=pr(cv2.resize(S,(n//2,n//2),interpolation=cv2.INTER_AREA))
r=rasterio.open(pc); H=4200
B=r.read(1,window=Window(cx-H,cy-H,2*H,2*H),boundless=True).astype(np.float32)
if rot==180: B=B[::-1,::-1]
best=(-1,)
for g in gs:
    f=g/20.0; b=cv2.resize(B,None,fx=f,fy=f,interpolation=cv2.INTER_AREA)
    for ang in range(-12,13,2):
        M=cv2.getRotationMatrix2D((b.shape[1]/2,b.shape[0]/2),ang,1); bb=cv2.warpAffine(b,M,b.shape[::-1])
        c=b.shape[0]//2; k=int(1500/20); t=pr(bb[c-k:c+k,c-k:c+k])
        rr=cv2.matchTemplate(S20,t,cv2.TM_CCOEFF_NORMED); _,mx,_,loc=cv2.minMaxLoc(rr)
        if mx>best[0]: best=(mx,g,ang,loc,k)
mx,g,ang,loc,k=best; print('coarse ncc',round(mx,3),'gsd',round(g,2),'ang',ang,'loc',loc)
# initial affine full-res scan px -> S2 10 m px
th=np.radians(ang); sc=g/10.0
R=np.array([[np.cos(th),np.sin(th)],[-np.sin(th),np.cos(th)]])*sc    # cv2 rotation sign
if rot==180: Rr=-np.eye(2)
else: Rr=np.eye(2)
L=R@Rr
# scan centre (cx,cy) maps to S2 px: template centre
c10=np.array([(loc[0]+k)*2,(loc[1]+k)*2],float)
A=np.hstack([L,(c10-L@[cx,cy])[:,None]])
# patch NCC tie points over the 5 km box around the site
S10=pr(S,0.8); pts=[]
Ai=cv2.invertAffineTransform(A)
for gy in np.linspace(-2400,2400,9):
    for gx in np.linspace(-2400,2400,9):
        u=c10+np.array([gx,gy])/10
        if u.min()<60 or u.max()>n-60: continue
        # warp scan to S2 10 m grid patch 900 m, search +-300 m
        P=45; Sr=60
        Tm=np.float32(A.copy()); 
        dst=np.array([[1,0,-(u[0]-P)],[0,1,-(u[1]-P)],[0,0,1]])@np.vstack([A,[0,0,1]])
        X0,Y0=(Ai@[u[0],u[1],1]).astype(int); wpx=int(P*10/g*2.2)
        sub=r.read(1,window=Window(X0-wpx,Y0-wpx,2*wpx,2*wpx),boundless=True).astype(np.float32)
        if (sub<8).mean()>0.2: continue
        D=dst.copy(); D[:,2]+=D[:,:2]@[X0-wpx,Y0-wpx]
        sub=cv2.GaussianBlur(sub,(0,0),max(0.5,10/g/2.5)) if rot==0 else cv2.GaussianBlur(sub[::-1,::-1],(0,0),max(0.5,10/g/2.5))
        if rot==180: D2=D@np.array([[-1,0,2*wpx-1],[0,-1,2*wpx-1],[0,0,1]])
        else: D2=D
        tp=cv2.warpAffine(sub,D2[:2],(2*P,2*P))
        if tp.std()<3: continue
        win=S10[int(u[1]-P-Sr/2):int(u[1]+P+Sr/2),int(u[0]-P-Sr/2):int(u[0]+P+Sr/2)]
        if win.shape!=(2*P+Sr,2*P+Sr): continue
        rr=cv2.matchTemplate(win,pr(tp),cv2.TM_CCOEFF_NORMED); _,m2,_,l2=cv2.minMaxLoc(rr)
        if m2<0.3: continue
        du=np.array(l2)-Sr/2
        pts.append((X0,Y0,u[0]+du[0],u[1]+du[1],m2))
pts=np.array(pts); print('tie points',len(pts))
out=dict(coarse=dict(ncc=mx,gsd=g,ang=ang),A0=A.tolist(),s2=s2f,piece=pc,rot=rot)
if len(pts)>=6:
    src=pts[:,:2].astype(np.float32); dstp=pts[:,2:4].astype(np.float32)
    M,inl=cv2.estimateAffine2D(src,dstp,method=cv2.RANSAC,ransacReprojThreshold=4)
    inl=inl.ravel().astype(bool); idx=np.where(inl)[0]
    # leave-one-out checkpoint RMS
    loo=[]
    for i in idx:
        o=idx[idx!=i]; Mi,_=cv2.estimateAffine2D(src[o],dstp[o],method=cv2.LMEDS)
        if Mi is not None: loo.append(np.hypot(*(dstp[i]-(Mi[:,:2]@src[i]+Mi[:,2])))*10)
    res=(dstp[inl]-(src[inl]@M[:,:2].T+M[:,2])); rms=float(np.sqrt((res**2).sum(1).mean()))*10
    out.update(A=M.tolist(),n_tie=int(len(pts)),n_inl=int(inl.sum()),rms_fit_m=rms,rms_loo_m=float(np.sqrt(np.mean(np.square(loo)))) if loo else None,ties=pts.tolist())
    print('inliers',inl.sum(),'fit RMS m',round(rms,1),'LOO RMS m',out['rms_loo_m'])
else: out.update(A=A.tolist(),n_tie=int(len(pts)),rms_fit_m=None)
json.dump(out,open(sys.argv[7] if len(sys.argv)>7 else '/tmp/fit.json','w'),indent=1)
