import planetary_computer as pc, rasterio, numpy as np
from rasterio.merge import merge
from rasterio.warp import transform_bounds
from pystac_client import Client
p=Client.open("https://planetarycomputer.microsoft.com/api/stac/v1",modifier=pc.sign_inplace)
bbox=(74.45,15.45,74.95,15.90)
its=[i for i in p.search(collections=["sentinel-1-rtc"],bbox=bbox,datetime="2026-10-19/2026-10-19").items()]
print([i.id for i in its])
out={}
for b in ["vv","vh"]:
    srcs=[rasterio.open(i.assets[b].href) for i in its]
    bb=transform_bounds("EPSG:4326",srcs[0].crs,*bbox)
    a,tr=merge(srcs,bounds=bb,res=20,nodata=0); out[b]=a[0]; crs=srcs[0].crs
db={k:10*np.log10(np.where(v>0,v,np.nan)) for k,v in out.items()}
def st(a,lo,hi): return np.nan_to_num((np.clip((a-lo)/(hi-lo),0,1)*255)).astype("uint8")
rgb=np.stack([st(db["vv"],-20,0),st(db["vh"],-28,-8),st(db["vv"]-db["vh"],0,15)])
prof=dict(driver="GTiff",crs=crs,transform=tr,width=rgb.shape[2],height=rgb.shape[1],compress="deflate")
with rasterio.open("qgis/rasters/s1_rtc_20261019_VV_VH_dB.tif","w",**prof,count=2,dtype="float32",nodata=np.nan) as d: d.write(np.stack([db["vv"],db["vh"]]).astype("float32"))
with rasterio.open("qgis/rasters/s1_rtc_20261019_composite_VV_VH_ratio.tif","w",**prof,count=3,dtype="uint8",photometric="RGB") as d: d.write(rgb)
print(rgb.shape, np.isnan(db["vv"]).mean())
