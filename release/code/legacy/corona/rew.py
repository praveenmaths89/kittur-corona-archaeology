# re-warp corona into s2 window via affine T (c-window->s-window) composed with stored A; usage: rew.py site a b c d e f  (T rows)
import cv2,numpy as np,json,sys
from PIL import Image; Image.MAX_IMAGE_PIXELS=None
site=sys.argv[1]; T=np.array(list(map(float,sys.argv[2:8]))).reshape(2,3)
J=json.load(open('gcp_%s.json'%site)); A=np.array(J.get('An',J['A']))
A3=np.vstack([A,[0,0,1]]); An=(np.vstack([T,[0,0,1]])@A3)[:2]
J['An']=An.tolist(); json.dump(J,open('gcp_%s.json'%site,'w'))
Ai=cv2.invertAffineTransform(An)
cor=Ai@np.array([[0,1200,0,1200],[0,0,1200,1200],[1,1,1,1]])
x0,y0=cor.min(1).astype(int)-10; x1,y1=cor.max(1).astype(int)+10
big=Image.open('DS1045-1102DA224_b.tif'); x0=max(0,x0);y0=max(0,y0)
cr=np.array(big.crop((x0,y0,x1,y1))).astype(np.float32)
A2=An.copy(); A2[:,2]+=An[:,:2]@[x0,y0]
k=1/np.sqrt(abs(np.linalg.det(An[:,:2])))
cr=cv2.GaussianBlur(cr,(0,0),k/2.5)
wc=cv2.warpAffine(cr,A2,(1200,1200),flags=cv2.INTER_LINEAR)
cl=cv2.createCLAHE(2,(8,8)); cv2.imwrite('w_%s_c.png'%site,cl.apply(np.clip(wc,0,255).astype('uint8')))
print('px size m',10*k)
