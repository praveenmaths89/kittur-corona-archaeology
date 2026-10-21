# usage: warp.py fit.json lat lon out.tif [half_m=2500] [res=2]
import sys,json,numpy as np,cv2,rasterio
from rasterio.warp import transform
from rasterio.transform import from_origin
from rasterio.windows import Window
J=json.load(open(sys.argv[1])); la,lo=float(sys.argv[2]),float(sys.argv[3]); out=sys.argv[4]
H=float(sys.argv[5]) if len(sys.argv)>5 else 2500; g=float(sys.argv[6]) if len(sys.argv)>6 else 2
s=rasterio.open(J['s2']); T=s.transform
A=np.vstack([np.array(J['A']),[0,0,1]]); Ai=np.linalg.inv(A)
x,y=[v[0] for v in transform('EPSG:4326',s.crs,[lo],[la])]
N=int(2*H/g); X,Y=np.meshgrid(x-H+g/2+np.arange(N)*g,y+H-g/2-np.arange(N)*g)
c,r=~T*(X,Y)   # S2 px
u=Ai[0,0]*c+Ai[0,1]*r+Ai[0,2]; v=Ai[1,0]*c+Ai[1,1]*r+Ai[1,2]
R=rasterio.open(J['piece']); c0,r0=int(u.min())-4,int(v.min())-4; c1,r1=int(u.max())+4,int(v.max())+4
sub=R.read(1,window=Window(c0,r0,c1-c0,r1-r0),boundless=True).astype(np.float32)
img=cv2.remap(sub,(u-c0).astype(np.float32),(v-r0).astype(np.float32),cv2.INTER_LINEAR)
with rasterio.open(out,'w',driver='GTiff',width=N,height=N,count=1,dtype='uint8',crs=s.crs,transform=from_origin(x-H,y+H,g,g),compress='deflate') as d: d.write(np.clip(img,0,255).astype('uint8'),1)
print(out)
