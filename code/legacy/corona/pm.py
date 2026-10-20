import cv2,numpy as np,sys
site=sys.argv[1]; ps=int(sys.argv[2]); srch=int(sys.argv[3]); thr=float(sys.argv[4])
c=cv2.imread('w_%s_c.png'%site,0).astype(np.float32); s=cv2.imread('w_%s_s.png'%site,0).astype(np.float32)
def edge(z):
    z=cv2.GaussianBlur(z,(0,0),2); gx=cv2.Sobel(z,cv2.CV_32F,1,0); gy=cv2.Sobel(z,cv2.CV_32F,0,1); return np.sqrt(gx*gx+gy*gy)
for mode in ['int','edge']:
  C=c if mode=='int' else edge(c); S=s if mode=='int' else edge(s)
  P=[];Q=[];W=[]
  for yy in range(srch+ps,1200-ps-srch,ps):
    for xx in range(srch+ps,1200-ps-srch,ps):
      if (c[yy-ps:yy+ps,xx-ps:xx+ps]==0).mean()>0.05: continue
      t=C[yy-ps:yy+ps,xx-ps:xx+ps]
      r=cv2.matchTemplate(S[yy-ps-srch:yy+ps+srch,xx-ps-srch:xx+ps+srch],t,cv2.TM_CCOEFF_NORMED); _,mx,_,l=cv2.minMaxLoc(r)
      r2=r.copy(); cv2.circle(r2,l,6,-1,-1)
      if mx>thr and mx-r2.max()>0.04: P.append((xx,yy)); Q.append((xx+l[0]-srch,yy+l[1]-srch)); W.append(mx)
  P=np.float32(P);Q=np.float32(Q)
  if len(P)<4: print(mode,len(P)); continue
  M,inl=cv2.estimateAffine2D(P,Q,method=cv2.RANSAC,ransacReprojThreshold=3,maxIters=20000)
  print(mode,len(P),int(inl.sum()),M.round(3).tolist())
  d=Q-P; print(' median shift',np.median(d,0), 'inlier shifts', d[inl.ravel()==1].round(0).tolist()[:15])
  np.save('pm_%s_%s.npy'%(site,mode),np.hstack([P[inl.ravel()==1],Q[inl.ravel()==1]]))
