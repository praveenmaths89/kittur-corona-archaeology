# Task D: schematic 3D reconstruction c.1824 (assumptions in release/README and findings.md)
import numpy as np,rasterio,cv2,sys,os,matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from scipy.ndimage import map_coordinates
from shapely import wkt
feats=[wkt.loads(l) for l in open('feats_utm.wkt')]
R='../qgis/rasters/'
WALL_H=6.0   # 5 m earth rampart + 1 m parapet (assumption; Lawe 1825: mud rampart, parapet 3 ft)
WALL_W=6.0   # rendered footprint width (m)
MOAT_D=4.9; MOAT_W=10.0  # 16 ft deep (Gazetteer 1884); width assumed
CIT_H=4.0    # each citadel ring wall height above terrain (assumption)
VEX=2.0      # vertical exaggeration in render
g=5.0; cx=477470; cy=1724470; half=850
xs=np.arange(cx-half,cx+half,g); ys=np.arange(cy+half,cy-half,-g); X,Y=np.meshgrid(xs,ys)
d=rasterio.open(R+'cop_dem30_elevation.tif'); Z0=d.read(1).astype(float); c,r=~d.transform*(X,Y)
Z=map_coordinates(Z0,[r-0.5,c-0.5],order=3)
Z=cv2.GaussianBlur(Z,(0,0),2)
def raster(geom,width):
    m=np.zeros(Z.shape,np.uint8)
    cs=[geom.exterior.coords] if geom.geom_type=='Polygon' else [geom.coords]
    for co in cs:
        p=np.array([[(x-xs[0])/g,(ys[0]-y)/g] for x,y in co],np.int32)
        cv2.polylines(m,[p],geom.geom_type=='Polygon',1,max(1,int(round(width/g))))
    return m.astype(bool)
H=np.zeros_like(Z)
H[raster(feats[0],WALL_W)]=WALL_H
H[raster(feats[2],WALL_W)]=WALL_H*0.7
for i in (5,6,7): H[raster(feats[i],WALL_W)]=CIT_H
moat=raster(feats[1],MOAT_W); H[moat]=-MOAT_D
for i in (3,4):
    m=np.zeros(Z.shape,np.uint8); p=np.array([[(x-xs[0])/g,(ys[0]-y)/g] for x,y in feats[i].exterior.coords],np.int32); cv2.fillPoly(m,[p],1); H[m>0]=-2
ZZ=(Z+H)
cr=rasterio.open(R+'corona_1968_kittur.tif'); A=cr.read(1).astype(float); cc,rr=~cr.transform*(X,Y)
T=map_coordinates(A,[rr-0.5,cc-0.5],order=1)/255.
T=np.clip((T-np.percentile(T,1))/(np.percentile(T,99)-np.percentile(T,1)),0,1)
col=plt.cm.gray(T); col[H>0]=[0.80,0.55,0.35,1]; col[H<0]=[0.25,0.35,0.55,1]
def render(az,fn,el=32,dpi=110,size=(9,7)):
    fig=plt.figure(figsize=size); ax=fig.add_subplot(111,projection='3d')
    ax.plot_surface(X-cx,Y-cy,(ZZ-Z.min())*VEX,facecolors=col,rstride=1,cstride=1,linewidth=0,antialiased=False,shade=False)
    ax.view_init(el,az); ax.set_box_aspect((1,1,0.18),zoom=1.9); ax.set_axis_off()
    ax.set_title('Kittur lower fort and citadel, schematic c.1824 (TENTATIVE)\nCopernicus GLO-30 terrain, CORONA 31 Jan 1968 drape, walls %g m, moat %g m deep; vert. exag. %g×'%(WALL_H,MOAT_D,VEX),fontsize=9)
    plt.subplots_adjust(0,0,1,0.93); plt.savefig(fn,dpi=dpi); plt.close()
if sys.argv[1:]==['mp4']:
    os.makedirs('/tmp/f3d',exist_ok=True)
    for k,az in enumerate(range(0,360,6)): render(az-120,f'/tmp/f3d/f{k:03d}.png',dpi=80,size=(8,6))
else:
    render(-120,'../previews/findings_3d.png',dpi=150,size=(11,8.5))
