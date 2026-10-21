import cv2,numpy as np,sys
site=sys.argv[1]
c=cv2.imread('w_%s_c.png'%site,0).astype(np.float32); s=cv2.imread('w_%s_s.png'%site,0).astype(np.float32)
m=(c>0).astype('uint8')
for sig in [6,4,3,2]:
  for name in ['s']:
    W=np.eye(2,3,dtype=np.float32) if sig==6 else W
    try:
      cc,W=cv2.findTransformECC(s,c,W,cv2.MOTION_AFFINE,(cv2.TERM_CRITERIA_EPS|cv2.TERM_CRITERIA_COUNT,300,1e-6),m,int(sig*4)|1)
      print(sig,round(cc,3),W.round(3).tolist())
    except Exception as e: print(sig,e)
np.save('ecc_%s.npy'%site,W)
