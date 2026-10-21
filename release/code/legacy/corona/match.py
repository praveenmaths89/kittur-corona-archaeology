import cv2,numpy as np
s2=cv2.imread('s2_30m.png',0)
cl=cv2.createCLAHE(3,(8,8))
s2=cl.apply(s2)
sift=cv2.SIFT_create(8000)
k2,d2=sift.detectAndCompute(s2,None)
for p in 'abcd':
    im=cl.apply(cv2.imread('ov_%s.png'%p,0))
    k1,d1=sift.detectAndCompute(im,None)
    m=cv2.BFMatcher().knnMatch(d1,d2,k=2)
    g=[a for a,b in m if a.distance<0.8*b.distance]
    if len(g)<4: print(p,len(g)); continue
    A=np.float32([k1[x.queryIdx].pt for x in g]); B=np.float32([k2[x.trainIdx].pt for x in g])
    M,inl=cv2.estimateAffinePartial2D(A,B,method=cv2.RANSAC,ransacReprojThreshold=8)
    n=int(inl.sum()) if inl is not None else 0
    print(p,len(g),n,M.round(3).tolist() if M is not None else None)
    if n>=8:
        np.save('M_%s.npy'%p,M); np.save('in_%s.npy'%p,np.hstack([A[inl.ravel()==1],B[inl.ravel()==1]]))
