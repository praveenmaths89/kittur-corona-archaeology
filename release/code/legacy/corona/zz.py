import cv2,sys
site,k,x0,y0,n,dx,dy=sys.argv[1],sys.argv[2],*map(int,sys.argv[3:8])
a=cv2.imread('w_%s_%s.png'%(site,k),0)
if k=='c': x0-=dx; y0-=dy
a=cv2.cvtColor(a[y0:y0+n,x0:x0+n],cv2.COLOR_GRAY2BGR); z=800/n
a=cv2.resize(a,(800,800),interpolation=cv2.INTER_CUBIC)
st=10 if n<=200 else 25
for g in range(0,n+1,st):
  p=int(g*z); cv2.line(a,(p,0),(p,800),(0,200,255),1); cv2.line(a,(0,p),(800,p),(0,200,255),1)
  if g%(st*2)==0: cv2.putText(a,str(x0+g),(p+2,12),0,0.4,(0,0,255),1); cv2.putText(a,str(y0+g),(2,p+12),0,0.4,(0,0,255),1)
cv2.imwrite('zz_%s.png'%k,a)
