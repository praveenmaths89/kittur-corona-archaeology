# usage: epoch_fetch.py <site_dir> <lat> <lon> <epoch> '<json [collection, [years], platforms|null]>' [months=01-01/04-30]
# Dry-season median composite on a 6x6 km UTM 10 m grid. Landsat via Planetary Computer (signed), Sentinel-2 via Earth Search.
import rasterio, numpy as np, sys, json, os
from pystac_client import Client
from rasterio.warp import reproject, Resampling, transform
from rasterio.transform import from_origin
from shapely.geometry import shape,box
site,la,lo,ep=sys.argv[1],float(sys.argv[2]),float(sys.argv[3]),sys.argv[4]; coll,yrs,plat=json.loads(sys.argv[5])
mon=sys.argv[6] if len(sys.argv)>6 else '01-01/04-30'
x,y=[v[0] for v in transform('EPSG:4326','EPSG:32643',[lo],[la])]
H=3000; X0,Y0=x-H,y+H; W=Hh=int(2*H/10); T=from_origin(X0,Y0,10,10)
bbox=(lo-0.03,la-0.03,lo+0.03,la+0.03)
if coll=='landsat-c2-l2':
    import planetary_computer as pc; c=Client.open("https://planetarycomputer.microsoft.com/api/stac/v1",modifier=pc.sign_inplace)
    B={'blue':'blue','green':'green','red':'red','nir':'nir08','swir':'swir16'}
else:
    c=Client.open("https://earth-search.aws.element84.com/v1"); B={'blue':'blue','green':'green','red':'red','nir':'nir','swir':'swir16'}
items=[]
for yy in yrs:
    a,b=mon.split('/')
    q={"eo:cloud_cover":{"lt":15}}
    if plat: q["platform"]={"in":plat}
    items+=list(c.search(collections=[coll],bbox=bbox,datetime=f"{yy}-{a}/{yy}-{b}",query=q,max_items=60).items())
items=[i for i in items if shape(i.geometry).contains(box(*bbox))]
items.sort(key=lambda i:i.properties["eo:cloud_cover"]); items=items[:int(os.environ.get("NI","4"))]
stk={k:[] for k in B}; used=[]
for i in items:
    try:
        g={}
        for k,a in B.items():
            d=np.full((Hh,W),np.nan,'float32')
            with rasterio.open(i.assets[a].href) as s:
                reproject(rasterio.band(s,1),d,dst_transform=T,dst_crs='EPSG:32643',resampling=Resampling.bilinear,src_nodata=0,dst_nodata=np.nan)
            g[k]=d
    except Exception as e: print('skip',i.id,e); continue
    for k in B:
        v=g[k]; v=v*0.0000275-0.2 if coll=='landsat-c2-l2' else v/10000
        stk[k].append(v)
    used.append((i.id,i.datetime.strftime('%Y-%m-%d'),round(i.properties['eo:cloud_cover'],1)))
os.makedirs(f'{site}/raw/epochs',exist_ok=True)
if not used: print(ep,'NO SCENES'); sys.exit(0)
M={k:np.nanmedian(np.stack(v),0) for k,v in stk.items()}
with rasterio.open(f'{site}/raw/epochs/{ep}.tif','w',driver='GTiff',width=W,height=Hh,count=5,dtype='float32',crs='EPSG:32643',transform=T,compress='deflate') as d:
    for j,k in enumerate(B): d.write(M[k].astype('float32'),j+1); d.set_band_description(j+1,k)
json.dump(dict(collection=coll,items=used,stac='Planetary Computer' if coll=='landsat-c2-l2' else 'Earth Search'),open(f'{site}/raw/epochs/{ep}.json','w')); print(ep,used)
