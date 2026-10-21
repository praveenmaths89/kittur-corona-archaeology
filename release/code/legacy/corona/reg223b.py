import rasterio,numpy as np,cv2,json
from rasterio.warp import transform
from rasterio.windows import from_bounds
from rasterio.transform import from_origin
from PIL import Image; Image.MAX_IMAGE_PIXELS=None
exec(open('reg223.py').read().split('mx,p,sc,ang,loc,sh=best')[0].replace("for p in 'bc'","for p in 'b'"))
mx,p,sc,ang,loc,sh=best[0]
# t0 px (35.2m grid, origin x-H,y+H) -> thumb px
n=t0.shape[0]; ctr=(n*sc/2,n*sc/2); c=int(n*sc*0.18)
M=cv2.getRotationMatrix2D(ctr,ang,1)  # on scaled
S=np.diag([sc,sc,1.]); M3=np.vstack([M,[0,0,1]]); T=np.array([[1,0,loc[0]-c],[0,1,loc[1]-c],[0,0,1.]])
G=T@M3@S   # t0px->thumb
# utm->t0px
U=np.array([[1/35.2,0,-(x-H)/35.2],[0,-1/35.2,(y+H)/35.2],[0,0,1]])
Wr,Hr=35506,10032
R=np.array([[-16,0,Wr-1],[0,-16,Hr-1],[0,0,1.]])  # thumb->raw (rot180)
A=R@G@U   # utm->raw
json.dump({'utm2raw':A.tolist(),'piece':'b','ncc':float(mx)},open('da223_coarse.json','w'))
big=Image.open('DS1045-1102DA223/DS1045-1102DA223_b.tif')
sites={'Sampgaon':(15.7954,74.7585),'Bailhongal':(15.8164,74.8569),'OldSangoli':(15.74663,74.83368),'Tigadi':(15.8023,74.7210),'Kittur':(15.598,74.785)}
out={}
for nm,(la,lo) in sites.items():
    X,Y=transform('EPSG:4326','EPSG:32643',[lo],[la]); X,Y=X[0],Y[0]
    rc=A@[X,Y,1]; print(nm,rc[:2].round())
    if not(0<rc[0]<Wr and 300<rc[1]<Hr-300): print(' outside'); continue
    # build 2 m grid 4x4 km, map via A
    half=2000; N=2000
    gx,gy=np.meshgrid(X-half+np.arange(N)*2+1,Y+half-np.arange(N)*2-1)
    u=A[0,0]*gx+A[0,1]*gy+A[0,2]; v=A[1,0]*gx+A[1,1]*gy+A[1,2]
    c0,r0=int(u.min())-5,int(v.min())-5; c1,r1=int(u.max())+5,int(v.max())+5
    sub=np.array(big.crop((c0,r0,c1,r1))).astype(np.float32)
    img=cv2.remap(sub,(u-c0).astype(np.float32),(v-r0).astype(np.float32),cv2.INTER_AREA if False else cv2.INTER_LINEAR)
    # refine shift vs S2 at 10 m
    w=from_bounds(X-half,Y-half,X+half,Y+half,s.transform)
    s2=s.read(window=w,out_shape=(3,400,400),boundless=True).astype(np.float32).mean(0)
    im10=cv2.resize(img,(400,400),interpolation=cv2.INTER_AREA)
    def pr(z): return cv2.GaussianBlur(cl.apply(np.clip(z/np.percentile(z,99.5)*255,0,255).astype('uint8')).astype(np.float32),(0,0),1)
    tpl=pr(s2)[80:320,80:320]; r=cv2.matchTemplate(pr(im10),tpl,cv2.TM_CCOEFF_NORMED); _,m2,_,l2=cv2.minMaxLoc(r)
    dx,dy=(l2[0]-80)*10,(l2[1]-80)*10; print(' refine ncc',round(m2,3),'shift m',dx,dy)
    out[nm]=dict(ncc=float(m2),dx=dx,dy=dy)
    # apply shift: image content at offset -> shift grid
    sh_px=(dx/2,dy/2); Mx=np.float32([[1,0,sh_px[0]],[0,1,sh_px[1]]])
    img2=cv2.warpAffine(img,Mx,(N,N),flags=cv2.WARP_INVERSE_MAP) if abs(m2)>0.25 else img
    tr=from_origin(X-half,Y+half,2,2)
    with rasterio.open(f'../qgis/rasters/corona_1968DA223_{nm.lower()}.tif','w',driver='GTiff',width=N,height=N,count=1,dtype='uint8',crs='EPSG:32643',transform=tr,compress='deflate') as d:
        d.write(np.clip(img2,0,255).astype('uint8'),1)
    cv2.imwrite(f'/tmp/r223_{nm}.png',np.hstack([cv2.resize(cv2.equalizeHist(np.clip(img2,0,255).astype('uint8')),(500,500)),cv2.resize(pr(s2).astype('uint8'),(500,500))]))
json.dump(out,open('da223_sites.json','w'))
