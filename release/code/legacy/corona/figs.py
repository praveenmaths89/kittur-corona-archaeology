import rasterio,numpy as np,geopandas as gp,cv2
from rasterio.warp import reproject,Resampling,transform
from rasterio.transform import from_origin
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
R='qgis/rasters/'
F=gp.read_file('corona/corona1968_features_utm.gpkg')
def grid(lo,la,half,res):
    x,y=transform('EPSG:4326','EPSG:32643',[lo],[la]); n=int(2*half/res); return from_origin(x[0]-half,y[0]+half,res,res),n,(x[0]-half,x[0]+half,y[0]-half,y[0]+half)
def rp(f,bands,t,n,rs=Resampling.bilinear):
    s=rasterio.open(R+f+'.tif'); d=np.zeros((len(bands),n,n),'float32')
    for i,b in enumerate(bands): reproject(rasterio.band(s,b),d[i],dst_transform=t,dst_crs='EPSG:32643',resampling=rs)
    return d
def rgb(d): d=d.transpose(1,2,0); return np.clip(d/np.percentile(d[d>0],99.5),0,1)
cl=cv2.createCLAHE(2.5,(8,8))
# Fig 1: fort 1968 with outlines (1.6 km)
t,n,ext=grid(74.7895,15.5985,800,2)
c=cl.apply(rp('corona_1968_kittur',[1],t,n)[0].astype('uint8'))
f,ax=plt.subplots(1,2,figsize=(16,8.4))
for a in ax: a.imshow(c,cmap='gray',extent=ext)
cols=['red','cyan','yellow','lime','lime','orange','orange','magenta']
for i,r in F.iterrows():
    G=r.geometry; xs,ys=(G.exterior.xy if G.geom_type=='Polygon' else G.xy); ax[1].plot(xs,ys,color=cols[i],lw=1.6,label=f"{r.feature} ({r.area_ha} ha)" if r.area_ha==r.area_ha else r.feature)
ax[1].legend(loc='lower right',fontsize=7.5,framealpha=0.85)
for a in ax: a.set_xlim(ext[0],ext[1]); a.set_ylim(ext[2],ext[3]); a.set_xticks([]); a.set_yticks([])
ax[0].plot([ext[1]-550,ext[1]-50],[ext[2]+60]*2,'y-',lw=4); ax[0].text(ext[1]-550,ext[2]+90,'500 m',color='y')
ax[0].set_title('CORONA KH-4A 31 Jan 1968 (DS1045-1102DA224), CLAHE, 1.6 km'); ax[1].set_title('Tentative digitisation (corona1968_features); error ~50-100 m')
plt.tight_layout(); plt.savefig('previews/findings_fort1968.png',dpi=90); plt.close()
# Fig 2: ring hill: 1967 DA, 1968 DA, DEM profile, stereo parallax
t,n,ext=grid(74.7863,15.5966,600,2)
A=cl.apply(rp('corona_1968_kittur',[1],t,n)[0].astype('uint8')); B=cl.apply(rp('corona_1967DA_kittur',[1],t,n)[0].astype('uint8'))
s2=rgb(rp('s2_dry_20260217_truecolour',[1,2,3],t,n))
dem=rasterio.open(R+'cop_dem30_elevation.tif'); e=dem.read(1); g=F.geometry[7].centroid; rr,cc=dem.index(g.x,g.y)
f,ax=plt.subplots(1,4,figsize=(24,6.4))
ax[0].imshow(B,cmap='gray',extent=ext); ax[0].set_title('CORONA 11 Nov 1967 (DS1044-2134DA217)')
ax[1].imshow(A,cmap='gray',extent=ext); ax[1].set_title('CORONA 31 Jan 1968 (DS1045-1102DA224)')
ax[2].imshow(s2,extent=ext); ax[2].set_title('Sentinel-2 17 Feb 2026')
for a in ax[:3]:
    for i in [5,6,7]:
        xs,ys=F.geometry[i].exterior.xy; a.plot(xs,ys,'--',color='orange',lw=0.8)
    a.set_xticks([]); a.set_yticks([])
d=np.arange(-12,13)*30
ax[3].plot(d,e[rr,cc-12:cc+13],'-o',label='W-E'); ax[3].plot(d,e[rr-12:rr+13,cc],'-s',label='N-S')
ax[3].set_xlabel('distance from ring centre (m)'); ax[3].set_ylabel('Copernicus DEM GLO-30 (m)'); ax[3].legend(); ax[3].grid(alpha=.3); ax[3].set_title('Profiles through ring centre: ~28 m hillock')
plt.tight_layout(); plt.savefig('previews/findings_ring.png',dpi=85); plt.close()
# Fig 3: Sangolli
t,n,ext=grid(74.8337,15.733,2600,4)
x1,y1=transform('EPSG:4326','EPSG:32643',[74.83368,74.8337],[15.74663,15.71715])
soi=rp('SoI_48_I_14_Belgaum_District__1924__roughgeoref',[1,2,3],t,n).transpose(1,2,0).astype('uint8')
co=cl.apply(rp('corona_1968_sangolli',[1],t,n)[0].astype('uint8')); s2=rgb(rp('s2_dry_20260217_truecolour',[1,2,3],t,n))
osm=gp.read_file('osm_raw.gpkg').to_crs(32643).cx[ext[0]:ext[1],ext[2]:ext[3]]; wat=osm[(osm.category=='water')&(osm.geom_type=='Polygon')]
f,ax=plt.subplots(1,3,figsize=(22,7.8))
for a,im,ti in zip(ax,[soi,co,s2],['Survey of India 48 I/14, 1924 (rough georef, ~100s m)','CORONA KH-4A forward, 31 Jan 1968 (DS1045-1102DF224)','Sentinel-2 17 Feb 2026']):
    a.imshow(im,cmap='gray' if im.ndim==2 else None,extent=ext); a.set_title(ti,fontsize=11)
    for G in wat.geometry: xs,ys=G.exterior.xy; a.plot(xs,ys,color='deepskyblue',lw=0.9)
    a.plot(x1[0],y1[0],'o',mfc='none',mec='red',ms=22,mew=2); a.plot(x1[1],y1[1],'s',mfc='none',mec='yellow',ms=18,mew=2)
    a.set_xlim(ext[0],ext[1]); a.set_ylim(ext[2],ext[3]); a.set_xticks([]); a.set_yticks([])
ax[1].text(x1[0]+250,y1[0]+250,'1968 village\n(= "Sangoli" of 1924)',color='red',fontsize=11)
ax[1].text(x1[1]+250,y1[1],'present Sangolli\n(fields in 1968)',color='yellow',fontsize=11)
f.suptitle('Sangolli, 5.2 x 5.2 km. Blue = OSM water outlines (Malaprabha/Renuka Sagar reservoir, 2020s)',fontsize=13)
plt.tight_layout(); plt.savefig('previews/findings_sangolli.png',dpi=85); plt.savefig('previews/compare_sangolli.png',dpi=85); plt.close()
print('ok')
