import cv2,numpy as np,json,sys
from PIL import Image; Image.MAX_IMAGE_PIXELS=None
from rasterio.warp import transform
F=np.array(json.load(open(sys.argv[1]))['F']); out=sys.argv[2]; piece=sys.argv[3]
x,y=transform('EPSG:4326','EPSG:32643',[74.8337],[15.7171]); x,y=x[0],y[0]
Fi=cv2.invertAffineTransform(F) if F.shape==(2,3) else None
jj,ii=np.meshgrid(np.arange(1200,dtype=np.float64),np.arange(1200,dtype=np.float64)); E=x-6000+jj*10+5; N=y+6000-ii*10-5
u=Fi[0,0]*E+Fi[0,1]*N+Fi[0,2]; v=Fi[1,0]*E+Fi[1,1]*N+Fi[1,2]
x0,y0=int(max(0,u.min())),int(max(0,v.min())); im=Image.open(piece); x1,y1=int(min(im.size[0],u.max())),int(min(im.size[1],v.max()))
cr=np.array(im.crop((x0,y0,x1,y1))); cr=cv2.GaussianBlur(cr,(0,0),2)
o=cv2.remap(cr,(u-x0).astype(np.float32),(v-y0).astype(np.float32),cv2.INTER_LINEAR,borderValue=0)
cv2.imwrite(out,cv2.createCLAHE(2,(8,8)).apply(o))
