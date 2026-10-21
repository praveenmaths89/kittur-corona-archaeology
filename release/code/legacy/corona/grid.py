import cv2,numpy as np,sys
site,x0,y0,n,z=sys.argv[1],int(sys.argv[2]),int(sys.argv[3]),int(sys.argv[4]),float(sys.argv[5])
out=[]
for k in 'cs':
  a=cv2.imread('w_%s_%s.png'%(site,k),0)[y0:y0+n,x0:x0+n]
  a=cv2.cvtColor(cv2.resize(a,None,fx=z,fy=z,interpolation=cv2.INTER_CUBIC),cv2.COLOR_GRAY2BGR)
  for g in range(0,n,25):
    p=int(g*z); col=(0,255,255) if g%50==0 else (0,140,255)
    cv2.line(a,(p,0),(p,a.shape[0]),col,1); cv2.line(a,(0,p),(a.shape[1],p),col,1)
    if g%50==0:
      cv2.putText(a,str(x0+g),(p+2,12),0,0.4,(0,0,255),1); cv2.putText(a,str(y0+g),(2,p+12),0,0.4,(0,0,255),1)
  out.append(a)
cv2.imwrite('g_%s.png'%site,np.hstack(out))
