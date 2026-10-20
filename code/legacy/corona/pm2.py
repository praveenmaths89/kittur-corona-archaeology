import cv2,numpy as np,sys,json
site=sys.argv[1]; blur=float(sys.argv[2]); ps=int(sys.argv[3]); srch=int(sys.argv[4]); thr=float(sys.argv[5])
c=cv2.imread('w_%s_c.png'%site,0).astype(np.float32); s=cv2.imread('w_%s_s.png'%site,0).astype(np.float32)
C=cv2.GaussianBlur(c,(0,0),blur); S=cv2.GaussianBlur(s,(0,0),blur)
P=[];Q=[];V=[]
step=ps
for yy in range(srch+ps,1200-ps-srch,step):
  for xx in range(srch+ps,1200-ps-srch,step):
    if (c[yy-ps:yy+ps,xx-ps:xx+ps]==0).mean()>0.02: continue
    t=C[yy-ps:yy+ps,xx-ps:xx+ps]
    if t.std()<5: continue
    r=cv2.matchTemplate(S[yy-ps-srch:yy+ps+srch,xx-ps-srch:xx+ps+srch],t,cv2.TM_CCOEFF_NORMED); _,mx,_,l=cv2.minMaxLoc(r)
    if mx>thr: P.append((xx,yy)); Q.append((xx+l[0]-srch,yy+l[1]-srch)); V.append(mx)
P=np.float32(P);Q=np.float32(Q); print('cand',len(P))
M,inl=cv2.estimateAffine2D(P,Q,method=cv2.RANSAC,ransacReprojThreshold=4,maxIters=20000)
i=inl.ravel()==1; print('inl',i.sum(),M.round(3).tolist())
res=Q[i]-(P[i]@M[:,:2].T+M[:,2]); print('affine rms px',np.sqrt((res**2).sum(1).mean()))
np.save('pm2_%s.npy'%site,np.hstack([P[i],Q[i]]))
