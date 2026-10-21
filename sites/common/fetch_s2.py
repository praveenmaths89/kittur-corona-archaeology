# usage: fetch_s2.py <site_dir> <lat> <lon> [halfkm=8]; Earth Search sentinel-2-l2a, least-cloudy Jan-Mar 2026 scene containing the point
import sys,json,numpy as np,rasterio,os
from pystac_client import Client
from rasterio.warp import transform
from rasterio.windows import from_bounds
from rasterio.enums import Resampling
site,la,lo=sys.argv[1],float(sys.argv[2]),float(sys.argv[3]); H=float(sys.argv[4] if len(sys.argv)>4 else 8)*1000
import os
c=Client.open("https://earth-search.aws.element84.com/v1")
its=list(c.search(collections=["sentinel-2-l2a"],intersects={"type":"Point","coordinates":[lo,la]},datetime="2026-01-01/2026-03-31",query={"eo:cloud:cover":{"lt":10}} if False else None,max_items=60).items())
its=[i for i in its if i.properties.get("eo:cloud_cover",100)<5]
if os.environ.get("S2_ITEM"): its=[c.get_collection("sentinel-2-l2a").get_item(os.environ["S2_ITEM"])]
its.sort(key=lambda i:(i.properties["eo:cloud_cover"],-i.properties.get("s2:nodata_pixel_percentage",0)*0))
for it in its:
    out={}
    try:
        for b in ["blue","green","red","nir","swir16"]:
            with rasterio.open(it.assets[b].href) as s:
                x,y=[v[0] for v in transform("EPSG:4326",s.crs,[lo],[la])]
                w=from_bounds(x-H,y-H,x+H,y+H,s.transform)
                n=int(2*H/10); out[b]=s.read(1,window=w,out_shape=(n,n),resampling=Resampling.bilinear,boundless=True,fill_value=0).astype("float32")
                crs=s.crs
        if (out["red"]==0).mean()>0.01: continue
        break
    except Exception as e: print("skip",it.id,e)
from rasterio.transform import from_origin
tr=from_origin(x-H,y+H,10,10)
p=dict(driver="GTiff",width=n,height=n,count=5,dtype="float32",crs=crs,transform=tr,compress="deflate")
os.makedirs(f"{site}/raw/sentinel",exist_ok=True)
fn=f"{site}/raw/sentinel/{it.id}_5band.tif"
with rasterio.open(fn,"w",**p) as d:
    for k,b in enumerate(["blue","green","red","nir","swir16"]): d.write(out[b],k+1); d.set_band_description(k+1,b)
json.dump(dict(id=it.id,datetime=str(it.datetime),cloud=it.properties["eo:cloud_cover"],crs=str(crs),file=fn,source="https://earth-search.aws.element84.com/v1 sentinel-2-l2a"),open(f"{site}/raw/sentinel/s2_meta.json","w"),indent=1)
print(it.id,it.datetime,it.properties["eo:cloud_cover"],crs)
