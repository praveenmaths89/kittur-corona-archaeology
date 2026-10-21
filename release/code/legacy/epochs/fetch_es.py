import rasterio, numpy as np, sys, json
from pystac_client import Client
from rasterio.warp import reproject, Resampling
from rasterio.transform import from_origin
c=Client.open("https://earth-search.aws.element84.com/v1")
bbox=(74.74,15.56,74.88,15.76)
# common grid UTM43N 10 m
X0,Y0=470500,1743000; W,H=1500,2200; T=from_origin(X0,Y0,10,10)
def grab(item,bands):
    out={}
    for k,a in bands.items():
        d=np.full((H,W),np.nan,'float32')
        with rasterio.open(item.assets[a].href) as s:
            reproject(rasterio.band(s,1),d,dst_transform=T,dst_crs='EPSG:32643',resampling=Resampling.bilinear,src_nodata=0,dst_nodata=np.nan)
        out[k]=d
    return out
ep=sys.argv[1]; coll,yrs,plat=json.loads(sys.argv[2])
items=[]
for y in yrs:
    q={"eo:cloud_cover":{"lt":15}}
    if plat: q["platform"]={"in":plat}
    items+=list(c.search(collections=[coll],bbox=bbox,datetime=f"{y}-01-01/{y}-03-31",query=q,max_items=60).items())
from shapely.geometry import shape,box
items=[i for i in items if shape(i.geometry).contains(box(*bbox))]
items.sort(key=lambda i:i.properties["eo:cloud_cover"]); items=items[:int(__import__("os").environ.get("NI","4"))]
if coll=='landsat-c2-l2': B={'blue':'blue','green':'green','red':'red','nir':'nir08','swir':'swir16'}
else: B={'blue':'blue','green':'green','red':'red','nir':'nir','swir':'swir16'}
stk={k:[] for k in B}; used=[]
for i in items:
    try: g=grab(i,B)
    except Exception as e: print('skip',i.id,e); continue
    for k in B:
        v=g[k]
        if coll=='landsat-c2-l2': v=v*0.0000275-0.2
        else:
            off=0
            v=v/10000+off
        stk[k].append(v)
    used.append((i.id,i.datetime.strftime('%Y-%m-%d'),round(i.properties['eo:cloud_cover'],1)))
M={k:np.nanmedian(np.stack(v),0) for k,v in stk.items()}
with rasterio.open(f'epochs/{ep}.tif','w',driver='GTiff',width=W,height=H,count=5,dtype='float32',crs='EPSG:32643',transform=T,compress='deflate') as d:
    for j,k in enumerate(B): d.write(M[k].astype('float32'),j+1); d.set_band_description(j+1,k)
json.dump(used,open(f'epochs/{ep}.json','w')); print(ep,used)
