import cv2,numpy as np,json,sys,rasterio
from PIL import Image; Image.MAX_IMAGE_PIXELS=None
from rasterio.warp import transform
from rasterio.transform import from_origin
Fj,piece,lon,lat,half,out=sys.argv[1],sys.argv[2],float(sys.argv[3]),float(sys.argv[4]),float(sys.argv[5]),sys.argv[6]
F=np.array(json.load(open(Fj))['F']); Fi=cv2.invertAffineTransform(F)
x,y=transform('EPSG:4326','EPSG:32643',[lon],[lat]); X0=round(x[0]-half); Y0=round(y[0]+half); n=int(2*half/2)
jj,ii=np.meshgrid(np.arange(n)+0.5,np.arange(n)+0.5); E=X0+jj*2; N=Y0-ii*2
u=Fi[0,0]*E+Fi[0,1]*N+Fi[0,2]; v=Fi[1,0]*E+Fi[1,1]*N+Fi[1,2]
im=Image.open(piece); x0,y0=int(max(0,u.min())),int(max(0,v.min())); x1,y1=int(min(im.size[0],u.max()+2)),int(min(im.size[1],v.max()+2))
cr=np.array(im.crop((x0,y0,x1,y1)))
o=cv2.remap(cr,(u-x0).astype(np.float32),(v-y0).astype(np.float32),cv2.INTER_LINEAR,borderValue=0)
with rasterio.open(out,'w',driver='GTiff',width=n,height=n,count=1,dtype='uint8',crs='EPSG:32643',transform=from_origin(X0,Y0,2,2),compress='deflate',tiled=True,nodata=0) as d: d.write(o,1); d.update_tags(SOURCE=piece)
print(out,(o>0).mean())
