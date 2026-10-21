import rasterio,numpy as np,pandas as pd,cv2,json
from rasterio.warp import reproject,Resampling,transform
from rasterio.transform import from_origin
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
R='qgis/rasters/'
def grid(lo,la,half,res):
    x,y=transform('EPSG:4326','EPSG:32643',[lo],[la]); n=int(2*half/res); return from_origin(x[0]-half,y[0]+half,res,res),n
def rp(path,bands,t,n):
    s=rasterio.open(path); d=np.zeros((len(bands),n,n),'float32')
    for i,b in enumerate(bands): reproject(rasterio.band(s,b),d[i],dst_transform=t,dst_crs='EPSG:32643',resampling=Resampling.bilinear)
    return d
def rgb(d): d=np.nan_to_num(d).transpose(1,2,0); return np.clip(d/np.percentile(d[d>0],99),0,1)
cl=cv2.createCLAHE(2,(8,8))
sites=[('Kittur fort + SW hillock',(74.7895,15.5985,900),'corona_1968_kittur','SoI_48_I_14_Belgaum_District__1924__roughgeoref','corona_1967DA_kittur'),
       ('Sangolli / Malaprabha',(74.8337,15.733,2600),'corona_1968_sangolli','SoI_48_I_14_Belgaum_District__1924__roughgeoref',None)]
eps=['1924 SoI','1967 CORONA','1968 CORONA','L1990','L2000','L2010','S2016','S2020','S2026']
lab={'L1990':'Landsat 5, 1990-91','L2000':'Landsat 5/7, 1999-2001','L2010':'Landsat 7, 2009 (SLC-off, median)','S2016':'Sentinel-2, 2016-17','S2020':'Sentinel-2, 2020','S2026':'Sentinel-2, 2026'}
f,ax=plt.subplots(2,9,figsize=(36,8.6))
for r,(nm,(lo,la,h),co,soi,c67) in enumerate(sites):
    t,n=grid(lo,la,h,max(2,h/450))
    for j,e in enumerate(eps):
        a=ax[r,j]; a.set_xticks([]); a.set_yticks([])
        if e=='1924 SoI': a.imshow(rp(R+soi+'.tif',[1,2,3],t,n).transpose(1,2,0).astype('uint8'))
        elif e=='1968 CORONA': a.imshow(cl.apply(rp(R+co+'.tif',[1],t,n)[0].astype('uint8')),cmap='gray')
        elif e=='1967 CORONA':
            if c67: a.imshow(cl.apply(rp(R+c67+'.tif',[1],t,n)[0].astype('uint8')),cmap='gray')
            else: a.text(.5,.5,'not covered\n(DA/DF217 stop south\nof Sangolli)',ha='center',va='center',transform=a.transAxes)
        else: a.imshow(rgb(rp(f'epochs/{e}.tif',[3,2,1],t,n)))
        if r==0: a.set_title({**lab}.get(e,e),fontsize=13)
    ax[r,0].set_ylabel(nm,fontsize=14)
plt.tight_layout(); plt.savefig('previews/findings_timeline_strip.png',dpi=60); plt.close()
d=pd.read_csv('epochs/metrics.csv'); yr={'L1990':1990,'L2000':2000,'L2010':2009,'S2016':2017,'S2020':2020,'S2026':2026}
d['year']=d.epoch.map(yr)
f,ax=plt.subplots(1,3,figsize=(20,5.2))
q=d[d.aoi=='sangolli_valley_3km']; ax[0].plot(q.year,q.water_ha,'o-'); ax[0].axvline(1972,ls='--',c='k'); ax[0].text(1972.5,ax[0].get_ylim()[1]*0.9,'Malaprabha dam\ncompleted 1972 (WRIS)')
ax[0].set_title('Dry-season open water within 3 km of old Sangoli (ha)'); ax[0].scatter([1968],[0],marker='*',s=200,c='r'); ax[0].text(1968,2,'1968: river only',color='r')
for a_,k in [('kittur_1.5km','Kittur 1.5 km'),('fort_enclosure','fort enclosure'),('ring_outer','SW hillock ring')]:
    q=d[d.aoi==a_]; ax[1].plot(q.year,q.built_frac,'o-',label=k)
ax[1].legend(); ax[1].set_title('Bare/built index fraction (NDBI>-0.05 & NDVI<0.25) - indicative only')
for a_,k in [('ring_outer_contrast','hillock ring: in minus 80 m buffer'),('fort_enclosure_contrast','fort enclosure: in minus 80 m buffer')]:
    q=d[d.aoi==a_]; ax[2].plot(q.year,q.ndvi,'o-',label=k)
ax[2].axhline(0,c='k',lw=.5); ax[2].legend(); ax[2].set_title('Dry-season NDVI contrast (feature visibility proxy)')
for a in ax: a.grid(alpha=.3); a.set_xlim(1964,2028)
plt.tight_layout(); plt.savefig('previews/findings_timeline_metrics.png',dpi=80); plt.close()
A=cv2.imread('previews/findings_timeline_strip.png'); B=cv2.imread('previews/findings_timeline_metrics.png')
B=cv2.resize(B,(A.shape[1],int(B.shape[0]*A.shape[1]/B.shape[1]))); cv2.imwrite('previews/findings_timeline.png',np.vstack([A,B]))
print('ok')
