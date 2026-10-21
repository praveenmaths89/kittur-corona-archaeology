import rasterio, numpy as np
from rasterio.warp import transform_bounds
from rasterio.windows import from_bounds
from pystac_client import Client
c=Client.open("https://earth-search.aws.element84.com/v1")
bbox=(74.45,15.45,74.95,15.90)
import sys
for tag,iid in [a.split("=") for a in sys.argv[1:]]:
    item=c.get_collection("sentinel-2-l2a").get_item(iid)
    arrs={}
    for b in ["blue","green","red","nir"]:
        with rasterio.open(item.assets[b].href) as src:
            bb=transform_bounds("EPSG:4326",src.crs,*bbox)
            w=from_bounds(*bb,transform=src.transform).round_offsets().round_lengths()
            arrs[b]=src.read(1,window=w,boundless=True,fill_value=0).astype("float32")
            prof=src.profile.copy(); tr=src.window_transform(w)
    prof.update(driver="GTiff",transform=tr,width=arrs["red"].shape[1],height=arrs["red"].shape[0],compress="deflate",tiled=True,blockxsize=512,blockysize=512)
    def st(a,lo=2,hi=98):
        v=a[a>0]; p1,p2=np.percentile(v,[lo,hi]); return (np.clip((a-p1)/(p2-p1),0,1)*255).astype("uint8")
    tc=np.stack([st(arrs[k]) for k in ["red","green","blue"]]); fc=np.stack([st(arrs[k]) for k in ["nir","red","green"]])
    for nm,a in [("truecolour",tc),("falsecolour",fc)]:
        p=prof.copy(); p.update(count=3,dtype="uint8",nodata=None,photometric="RGB")
        with rasterio.open(f"qgis/rasters/s2_{tag}_{nm}.tif","w",**p) as d: d.write(a)
    nd=(arrs["nir"]-arrs["red"])/(arrs["nir"]+arrs["red"]+1e-6)
    p=prof.copy(); p.update(count=1,dtype="float32",nodata=-9999)
    with rasterio.open(f"qgis/rasters/s2_{tag}_ndvi.tif","w",**p) as d: d.write(np.where(arrs["red"]>0,nd,-9999).astype("float32"),1)
    print(tag,tc.shape,item.properties["eo:cloud_cover"],item.datetime)
