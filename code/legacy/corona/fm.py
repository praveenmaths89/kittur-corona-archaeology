import cv2,numpy as np,glob,sys
cl=cv2.createCLAHE(2,(8,8)); sift=cv2.SIFT_create(15000)
T=cl.apply(cv2.imread('ov8_DA224_b.png',0)[:,500:1400]); kt,dt=sift.detectAndCompute(T,(T>10).astype('uint8'))
for f in sorted(glob.glob('DS*/ov8_*.png')):
  I=cl.apply(cv2.imread(f,0)); k,d=sift.detectAndCompute(I,(I>10).astype('uint8'))
  if d is None: continue
  m=cv2.BFMatcher().knnMatch(dt,d,k=2); g=[a for a,b in m if a.distance<0.75*b.distance]
  if len(g)<6: print(f,len(g),flush=True); continue
  A=np.float32([kt[x.queryIdx].pt for x in g]); B=np.float32([k[x.trainIdx].pt for x in g])
  M,inl=cv2.estimateAffine2D(A,B,method=cv2.RANSAC,ransacReprojThreshold=5)
  n=int(inl.sum()); print(f,len(g),n,M.round(2).tolist(),(M@[416,504,1]).round() if n>=10 else None,flush=True)
