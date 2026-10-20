import numpy as np,rasterio,json,cv2
from rasterio.warp import transform
from rasterio.windows import from_bounds
from rasterio.transform import from_origin
from PIL import Image; Image.MAX_IMAGE_PIXELS=None
C='../corona/'; R='../qgis/rasters/'
KX,KY=[v[0] for v in transform('EPSG:4326','EPSG:32643',[74.785],[15.598])]
g=10.0; half=16000; N=int(2*half/g)
xs=KX-half+g/2+np.arange(N)*g; ys=KY+half-g/2-np.arange(N)*g; X,Y=np.meshgrid(xs,ys)
out=np.zeros((N,N),np.float32); src=np.zeros((N,N),np.uint8)
def sample(path,u,v,sm):
    im=Image.open(path); W,H=im.size
    ok=(u>=0)&(v>=0)&(u<W-1)&(v<H-1)
    if not ok.any(): return ok,None
    c0,r0,c1,r1=int(u[ok].min()),int(v[ok].min()),int(u[ok].max())+2,int(v[ok].max())+2
    # read reduced by factor 4 to save memory
    f=4; sub=np.array(im.crop((c0,r0,c1,r1)).reduce(f)).astype(np.float32)
    val=cv2.remap(sub,((u-c0)/f).astype(np.float32),((v-r0)/f).astype(np.float32),cv2.INTER_LINEAR)
    return ok&(val>8),val
# DF224 piece c, F2: pixel->UTM
F=np.vstack([np.array(json.load(open(C+'df224_F2.json'))['F']),[0,0,1]]); Fi=np.linalg.inv(F)
u=Fi[0,0]*X+Fi[0,1]*Y+Fi[0,2]; v=Fi[1,0]*X+Fi[1,1]*Y+Fi[1,2]
ok,val=sample(C+'DS1045-1102DF224/DS1045-1102DF224_c.tif',u,v,1)
ok&=v<9100
out[ok]=val[ok]; src[ok]=2
# DA224 piece b via gcp_kittur An (scan px -> 10 m S2 window px; window = +-6 km about lonlat)
J=json.load(open(C+'gcp_kittur.json')); An=np.vstack([np.array(J['An']),[0,0,1]])
s2=rasterio.open(R+'s2_dry_20260217_truecolour.tif'); lo,la=J['lonlat']
x,y=[v[0] for v in transform('EPSG:4326','EPSG:32643',[lo],[la])]
w=from_bounds(x-6000,y-6000,x+6000,y+6000,s2.transform); wt=s2.window_transform(w)
Wt=np.array([[wt.a,wt.b,wt.c],[wt.d,wt.e,wt.f],[0,0,1]])
M=np.linalg.inv(Wt@An)   # UTM -> scan px
u=M[0,0]*X+M[0,1]*Y+M[0,2]; v=M[1,0]*X+M[1,1]*Y+M[1,2]
ok,val=sample(C+'DS1045-1102DA224_b.tif',u,v,1)
fill=ok&(src==0); out[fill]=val[fill]; src[fill]=1
tr=from_origin(KX-half,KY+half,g,g)
for nm,a,dt in [('corona_1968_mosaic15km_10m.tif',np.clip(out,0,255).astype('uint8'),'uint8'),('corona_1968_mosaic15km_source.tif',src,'uint8')]:
    with rasterio.open(R+nm,'w',driver='GTiff',width=N,height=N,count=1,dtype=dt,crs='EPSG:32643',transform=tr,compress='deflate') as d: d.write(a,1)
print('coverage DF224 %.0f%%  DA224 %.0f%%'%(100*(src==2).mean(),100*(src==1).mean()))
cv2.imwrite('/tmp/mos15.png',cv2.resize(cv2.createCLAHE(2,(8,8)).apply(np.clip(out,0,255).astype('uint8')),(1000,1000)))
