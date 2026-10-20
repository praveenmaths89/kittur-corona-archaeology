import cv2,numpy as np,rasterio,sys,json
from PIL import Image; Image.MAX_IMAGE_PIXELS=None
from rasterio.warp import transform
# candidate: crop px (full-res, relative to crop origin) -> UTM via similarity derived from template match
px,sx,sy,ang,lx,ly,tw,th=2.0,1.0,0.85,2,291,307,284,244
X0c,Y0c=30040-3600,4144-3600+800
x,y=transform('EPSG:4326','EPSG:32643',[74.8337],[15.7171]); x,y=x[0],y[0]
# S window 700px@40m origin at (x-14000,y+14000)
im=Image.open('DS1045-1102DF224/DS1045-1102DF224_c.tif'); cr=np.array(im.crop((X0c,Y0c,X0c+7200,Y0c+6400)))
f=px/40; h,wd=int(6400*f),int(7200*f)
M=cv2.getRotationMatrix2D((wd/2,h/2),ang,1); M[0]*=sx; M[1]*=sy
M[0,2]=wd/2-(M[0,0]*wd/2+M[0,1]*h/2); M[1,2]=h/2-(M[1,0]*wd/2+M[1,1]*h/2)
m=int(0.12*min(h,wd))
# full chain: crop px u -> base px u*f -> M -> minus m -> plus l -> S px -> UTM
A=np.vstack([M,[0,0,1]])@np.diag([f,f,1]); A[:2,2]+=[lx-m,ly-m]
S2U=np.array([[40,0,x-14000],[0,-40,y+14000],[0,0,1]]); F=(S2U@A)[:2]
json.dump({'F':F.tolist(),'origin':[X0c,Y0c]},open('sg_cand.json','w'))
# render overlay at 10 m: UTM grid 12x12 km centred on Sangolli
T=np.array([[10,0,x-6000],[0,-10,y+6000],[0,0,1]]); Fi=np.linalg.inv(np.vstack([F,[0,0,1]]))@T
jj,ii=np.meshgrid(np.arange(1200,dtype=np.float32),np.arange(1200,dtype=np.float32))
u=(Fi[0,0]*jj+Fi[0,1]*ii+Fi[0,2]).astype(np.float32); v=(Fi[1,0]*jj+Fi[1,1]*ii+Fi[1,2]).astype(np.float32)
o=cv2.remap(cv2.GaussianBlur(cr,(0,0),2),u,v,cv2.INTER_LINEAR); o=cv2.createCLAHE(2,(8,8)).apply(o)
cv2.imwrite('w_sgdf_c.png',o)
