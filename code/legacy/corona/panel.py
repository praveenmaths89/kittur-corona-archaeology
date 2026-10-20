import rasterio,numpy as np
from rasterio.warp import reproject,Resampling
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
R='qgis/rasters/'
for site,soi,lab,pt in [('kittur','SoI_48_I_14_Belgaum_District__1924__roughgeoref','Kittur fort',(74.79107,15.60044)),('nandagad','SoI_48_I_10_Belgaum_District__1924__c_roughgeoref','Nandagad (Rayanna samadhi)',(74.57366,15.57888))]:
  c=rasterio.open(R+'corona_1968_%s.tif'%site); n=1250; t=c.transform*c.transform.scale(2,2)
  def rp(f,b):
    s=rasterio.open(R+f+'.tif'); d=np.zeros((len(b),n,n),'float32')
    for i,k in enumerate(b): reproject(rasterio.band(s,k),d[i],dst_transform=t,dst_crs=c.crs,resampling=Resampling.bilinear)
    return d
  A=rp(soi,[1,2,3]).transpose(1,2,0).astype('uint8')
  B=rp('corona_1968_%s'%site,[1])[0]
  C=rp('s2_dry_20260217_truecolour',[1,2,3]).transpose(1,2,0); C=np.clip(C/np.percentile(C,99.5)*255,0,255).astype('uint8')
  from rasterio.warp import transform as tr
  x,y=tr('EPSG:4326',c.crs,[pt[0]],[pt[1]]); col,row=~t*(x[0],y[0])
  f,ax=plt.subplots(1,3,figsize=(21,7.6))
  for a,im,ti in zip(ax,[A,B,C],['Survey of India 1924 (sheet %s, rough georef, error ~100s m)'%soi.split('_')[2:4],'CORONA KH-4A 31 Jan 1968 (USGS DS1045-1102DA224)','Sentinel-2 L2A 17 Feb 2026 true colour']):
    a.imshow(im,cmap='gray' if im.ndim==2 else None); a.plot(col,row,'r+',ms=18,mew=2); a.set_title(ti,fontsize=11); a.set_xticks([]); a.set_yticks([])
  ax[0].set_title('Survey of India 1924, sheet 48 %s %s (rough georef, error ~100s m)'%tuple(soi.split('_')[2:4]),fontsize=11)
  ax[1].plot([n-260,n-10],[n-30,n-30],'y-',lw=4); ax[1].text(n-260,n-45,'1 km',color='y',fontsize=12)
  f.suptitle('%s, 5 x 5 km, north up, UTM 43N. Red cross = gazetteer point'%lab,fontsize=14)
  plt.tight_layout(); plt.savefig('previews/compare_%s.png'%site,dpi=90); plt.close()
print('ok')
