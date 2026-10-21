import planetary_computer as pc, rasterio, numpy as np
from pystac_client import Client
from rasterio.warp import transform_bounds
from rasterio.windows import from_bounds
c=Client.open("https://planetarycomputer.microsoft.com/api/stac/v1",modifier=pc.sign_inplace)
bbox=(74.45,15.45,74.95,15.90)
it=list(c.search(collections=["landsat-c2-l2"],bbox=bbox,datetime="1990-01-01/1999-12-31",query={"eo:cloud_cover":{"lt":5},"platform":{"eq":"landsat-5"}},max_items=100).items())
it=[i for i in it if i.properties["landsat:wrs_path"]=="146"]
it.sort(key=lambda i:(i.properties["eo:cloud_cover"],-int(i.datetime.month in (1,2,3))))
i=[x for x in it if x.datetime.month in (1,2,3)][0]; print(i.id,i.properties["eo:cloud_cover"])
A={}
for b in ["red","green","blue","nir08"]:
    with rasterio.open(i.assets[b].href) as s:
        bb=transform_bounds("EPSG:4326",s.crs,*bbox); w=from_bounds(*bb,transform=s.transform).round_offsets().round_lengths()
        A[b]=s.read(1,window=w,boundless=True,fill_value=0).astype("float32"); tr=s.window_transform(w); crs=s.crs
def st(a):
    v=a[a>0]; p1,p2=np.percentile(v,[2,98]); return (np.clip((a-p1)/(p2-p1),0,1)*255).astype("uint8")
for nm,ks in [("truecolour",["red","green","blue"]),("falsecolour",["nir08","red","green"])]:
    x=np.stack([st(A[k]) for k in ks])
    with rasterio.open(f"qgis/rasters/landsat5_{i.datetime:%Y%m%d}_{nm}.tif","w",driver="GTiff",crs=crs,transform=tr,width=x.shape[2],height=x.shape[1],count=3,dtype="uint8",compress="deflate",photometric="RGB") as d: d.write(x)
print(crs, x.shape)
