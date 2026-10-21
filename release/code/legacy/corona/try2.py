import cv2,numpy as np,rasterio
from PIL import Image; Image.MAX_IMAGE_PIXELS=None
from rasterio.warp import transform
from rasterio.windows import from_bounds
big=Image.open('DS1045-1102DA224_b.tif')
cl=cv2.createCLAHE(2,(8,8)); sift=cv2.SIFT_create(30000)
x,y=transform('EPSG:4326','EPSG:32643',[74.7911],[15.6004]); x,y=x[0],y[0]
for fn in ['s2_dry_20260217_truecolour','s2_newestlowcloud_20261010_truecolour','landsat5_19990304_truecolour']:
  s2=rasterio.open('../qgis/rasters/%s.tif'%fn); r=s2.res[0]
  H=9000; w=from_bounds(x-H,y-H,x+H,y+H,s2.transform)
  a=s2.read(window=w,boundless=True).astype(float).mean(0)
  a=cl.apply(np.clip(a/np.percentile(a,99)*255,0,255).astype('uint8'))
  k2,d2=sift.detectAndCompute(a,None)
  box=(7963-4500,0,7963+4500,10032); cr=np.array(big.crop(box))
  for f in [r/2.2*0.7, r/2.2, r/2.2*1.4]:
    sm=cl.apply(cv2.resize(cr,None,fx=1/f,fy=1/f,interpolation=cv2.INTER_AREA))
    k1,d1=sift.detectAndCompute(sm,None)
    m=cv2.BFMatcher().knnMatch(d1,d2,k=2); g=[p for p,q in m if p.distance<0.8*q.distance]
    A=np.float32([k1[i.queryIdx].pt for i in g]); B=np.float32([k2[i.trainIdx].pt for i in g])
    Ma,inl=cv2.estimateAffinePartial2D(A,B,method=cv2.RANSAC,ransacReprojThreshold=3,maxIters=20000)
    print(fn,round(f,2),len(g),int(inl.sum()),Ma.round(3).tolist())
