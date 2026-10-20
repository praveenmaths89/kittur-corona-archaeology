import cv2,numpy as np,rasterio
e=rasterio.open('../qgis/rasters/cop_dem30_elevation.tif').read(1)
v=e-cv2.GaussianBlur(e,(0,0),15)
v=cv2.GaussianBlur(v,(0,0),1.5)
b=cv2.rotate(cv2.imread('ov_b.png',0),cv2.ROTATE_180).astype(np.float32)
s2=cv2.imread('s2_30m.png',0).astype(np.float32)
def prep(x): x=cv2.GaussianBlur(x,(0,0),1.5); return (x-x.mean())/x.std()
best=[]
for name,ref in [('dem',v),('s2',s2)]:
  R=prep(ref.astype(np.float32))
  for sc in np.arange(0.9,1.6,0.05):
    for sy in [0.9,1.0,1.1,1.25]:
      for ang in [-6,-3,0,3,6]:
        t=b[70:560, 1300:2200]  # rotated b' east region
        t=cv2.resize(t,None,fx=sc,fy=sc*sy)
        Mr=cv2.getRotationMatrix2D((t.shape[1]/2,t.shape[0]/2),ang,1); t=cv2.warpAffine(t,Mr,(t.shape[1],t.shape[0]))
        if t.shape[0]>R.shape[0] or t.shape[1]>R.shape[1]:
            # crop template center
            h=min(t.shape[0],R.shape[0]-50); w=min(t.shape[1],R.shape[1]-50)
            y0=(t.shape[0]-h)//2; x0=(t.shape[1]-w)//2; t=t[y0:y0+h,x0:x0+w]
        else: x0=y0=0
        t=prep(t[30:-30,30:-30])
        r=cv2.matchTemplate(R,t,cv2.TM_CCOEFF_NORMED)
        _,mx,_,loc=cv2.minMaxLoc(r)
        best.append((mx,name,round(sc,2),sy,ang,loc))
best.sort(reverse=True)
for x in best[:12]: print(x)
