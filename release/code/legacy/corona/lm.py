import cv2,numpy as np,sys
site=sys.argv[1]; rad=float(sys.argv[2]) if len(sys.argv)>2 else 40
c=cv2.imread('w_%s_c.png'%site,0); s=cv2.imread('w_%s_s.png'%site,0)
for det in ['sift','orb']:
  D={'sift':cv2.SIFT_create(40000,contrastThreshold=0.01),'orb':cv2.ORB_create(40000)}[det]
  k1,d1=D.detectAndCompute(c,(c>0).astype('uint8')); k2,d2=D.detectAndCompute(s,None)
  p1=np.float32([k.pt for k in k1]); p2=np.float32([k.pt for k in k2])
  norm=cv2.NORM_L2 if det=='sift' else cv2.NORM_HAMMING
  A=[];B=[]
  from scipy.spatial import cKDTree
  T=cKDTree(p2)
  for i,p in enumerate(p1):
    idx=T.query_ball_point(p,rad)
    if len(idx)<2: continue
    dd=np.array([cv2.norm(d1[i],d2[j],norm) for j in idx]); o=np.argsort(dd)
    if dd[o[0]]<0.85*dd[o[1]]: A.append(p); B.append(p2[idx[o[0]]])
  A=np.float32(A);B=np.float32(B)
  M,inl=cv2.estimateAffine2D(A,B,method=cv2.RANSAC,ransacReprojThreshold=3,maxIters=50000,confidence=0.999)
  n=int(inl.sum()); print(det,len(A),n,M.round(3).tolist())
  np.save('lm_%s_%s.npy'%(site,det),np.hstack([A[inl.ravel()==1],B[inl.ravel()==1]]))
