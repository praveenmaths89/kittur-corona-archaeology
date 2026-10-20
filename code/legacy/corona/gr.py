import rasterio,cv2,numpy as np,sys
f,c0,r0,n,z,out=sys.argv[1],int(sys.argv[2]),int(sys.argv[3]),int(sys.argv[4]),float(sys.argv[5]),sys.argv[6]
a=rasterio.open(f).read(1)[r0:r0+n,c0:c0+n]
a=cv2.createCLAHE(2.5,(8,8)).apply(a)
a=cv2.cvtColor(cv2.resize(a,None,fx=z,fy=z,interpolation=cv2.INTER_CUBIC),cv2.COLOR_GRAY2BGR)
st=int(sys.argv[7]) if len(sys.argv)>7 else 50
for g in range(0,n+1,st):
  p=int(g*z); cv2.line(a,(p,0),(p,a.shape[0]),(0,200,255),1); cv2.line(a,(0,p),(a.shape[1],p),(0,200,255),1)
  cv2.putText(a,str(c0+g),(p+2,12),0,0.4,(0,0,255),1); cv2.putText(a,str(r0+g),(2,p+12),0,0.4,(0,0,255),1)
cv2.imwrite(out,a)
