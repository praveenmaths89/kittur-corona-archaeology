import rasterio,numpy as np
from rasterio.windows import from_bounds
from rasterio.warp import reproject,Resampling,calculate_default_transform
from scipy.ndimage import uniform_filter
u="https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_N15_00_E074_00_DEM/Copernicus_DSM_COG_10_N15_00_E074_00_DEM.tif"
bbox=(74.45,15.45,74.95,15.90)
with rasterio.open(u) as s:
    w=from_bounds(*bbox,transform=s.transform).round_offsets().round_lengths()
    a=s.read(1,window=w).astype("float32"); tr=s.window_transform(w); crs=s.crs
dt,W,H=calculate_default_transform(crs,"EPSG:32643",a.shape[1],a.shape[0],*bbox,resolution=30)
d=np.zeros((H,W),"float32")
reproject(a,d,src_transform=tr,src_crs=crs,dst_transform=dt,dst_crs="EPSG:32643",resampling=Resampling.bilinear,dst_nodata=-9999)
prof=dict(driver="GTiff",crs="EPSG:32643",transform=dt,width=W,height=H,count=1,compress="deflate")
def wr(n,x,dtp="float32",nd=-9999):
    with rasterio.open(f"qgis/rasters/{n}.tif","w",**prof,dtype=dtp,nodata=nd) as f: f.write(x.astype(dtp),1)
wr("cop_dem30_elevation",d)
dz=np.where(d==-9999,np.nan,d); dz=np.where(np.isnan(dz),np.nanmean(dz),dz)
gy,gx=np.gradient(dz,30)
slope=np.arctan(np.hypot(gx,gy)); asp=np.arctan2(-gx,gy)
az,alt=np.radians(315),np.radians(45)
hs=np.sin(alt)*np.cos(slope)+np.cos(alt)*np.sin(slope)*np.cos(az-asp)
wr("cop_dem30_hillshade",np.clip(hs*255,0,255),"uint8",0)
lrm=dz-uniform_filter(dz,size=17)   # ~500 m window
wr("cop_dem30_localrelief_500m",lrm)
print(W,H,np.nanmin(dz),np.nanmax(dz),np.percentile(lrm,[1,99]))
