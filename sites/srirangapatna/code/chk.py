import sys,rasterio,cv2,numpy as np
from rasterio.windows import from_bounds
a=rasterio.open(sys.argv[1]); A=a.read(1)
s=rasterio.open(sys.argv[2]); b=s.read([3,2,1],window=from_bounds(*a.bounds,s.transform)).mean(0)
b=np.clip(b/np.percentile(b,99.5)*255,0,255).astype('uint8')
cl=cv2.createCLAHE(2,(8,8)); im=np.hstack([cv2.resize(cl.apply(A),(500,500)),cv2.resize(cl.apply(b),(500,500))])
for i in range(0,1000,50): cv2.line(im,(i,0),(i,499),128,1)
for i in range(0,500,50): cv2.line(im,(0,i),(999,i),128,1)
cv2.imwrite(sys.argv[3],im)
