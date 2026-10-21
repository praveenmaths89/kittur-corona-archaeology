# per-site epoch metrics (same index thresholds as Kittur epochs/metrics.py) + timeline figure; then cross-site figure
import rasterio,numpy as np,json,os,sys,glob,csv,matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from rasterio.features import geometry_mask
from rasterio.warp import transform
from shapely.geometry import Point,shape
SITES={'srirangapatna':(12.4216,76.6930),'hampi':(15.3350,76.4600),'belgaum':(15.8634,74.5222)}
EP=['L1990','L2000','L2010','S2016','S2020','S2026']; YR={'L1990':1990,'L2000':2000,'L2010':2010,'S2016':2016.5,'S2020':2020,'S2026':2026}
allr=[]
for s,(la,lo) in SITES.items():
    x,y=[v[0] for v in transform('EPSG:4326','EPSG:32643',[lo],[la])]
    aois={'r1500m':Point(x,y).buffer(1500),'r2500m':Point(x,y).buffer(2500)}
    if s=='belgaum': aois['fort_inner']=shape(json.load(open('belgaum/analysis/fort_digitized.json'))['inner'])
    rows=[]
    for ep in EP:
        f=f'{s}/raw/epochs/{ep}.tif'
        if not os.path.exists(f): continue
        r=rasterio.open(f); bl,g,rd,n,sw=r.read()
        ndvi=(n-rd)/(n+rd+1e-6); ndbi=(sw-n)/(sw+n+1e-6); mndwi=(g-sw)/(g+sw+1e-6)
        water=mndwi>0.1; built=(ndbi>-0.05)&(ndvi<0.25)&~water
        meta=json.load(open(f'{s}/raw/epochs/{ep}.json'))
        for k,G in aois.items():
            m=geometry_mask([G],out_shape=ndvi.shape,transform=r.transform,invert=True)&np.isfinite(ndvi)
            rows.append(dict(site=s,epoch=ep,year=YR[ep],aoi=k,scenes=';'.join(d for _,d,_ in meta['items']),built_frac=round(float(built[m].mean()),3),water_frac=round(float(water[m].mean()),3),ndvi=round(float(np.nanmean(ndvi[m])),3)))
    mj=f'{s}/analysis/metrics.json'
    if os.path.exists(mj):
        M=json.load(open(mj)); rows.append(dict(site=s,epoch='CORONA',year=None,aoi='5x5km_tone',scenes=os.path.basename(M['corona']),built_frac=None,water_frac=round(M['water_1960s_pct']/100,3),ndvi=None))
    if not rows: continue
    with open(f'{s}/analysis/epoch_metrics.csv','w',newline='') as fo:
        w=csv.DictWriter(fo,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    allr+=rows
    d=[r_ for r_ in rows if r_['aoi']=='r1500m']
    fig,ax=plt.subplots(1,3,figsize=(15,4))
    for a,k in zip(ax,['built_frac','water_frac','ndvi']):
        a.plot([r_['year'] for r_ in d],[r_[k] for r_ in d],'o-'); a.set_title(k); a.set_xlim(1985,2028); a.grid(alpha=.3)
        for i,r_ in enumerate(d): a.annotate(r_['epoch'],(r_['year'],r_[k]),fontsize=7)
    fig.suptitle(f'{s}: dry-season composites, 1.5 km radius (index thresholds as Kittur; built index unreliable on bare soil/rock)')
    plt.tight_layout(); plt.savefig(f'{s}/previews/timeline_{s}.png',dpi=100); plt.close()
# cross-site incl. Kittur
k=list(csv.DictReader(open('../epochs/metrics.csv')))
kk=[dict(site='kittur',epoch=r['epoch'],year=YR[r['epoch']],built_frac=float(r['built_frac']),water_frac=float(r['water_frac']),ndvi=float(r['ndvi'])) for r in k if r['aoi']=='kittur_1.5km']
fig,ax=plt.subplots(1,3,figsize=(16,4.5))
for s in ['kittur']+list(SITES):
    d=kk if s=='kittur' else [r_ for r_ in allr if r_['site']==s and r_['aoi']=='r1500m']
    if not d: continue
    for a,kv in zip(ax,['built_frac','water_frac','ndvi']): a.plot([r_['year'] for r_ in d],[r_[kv] for r_ in d],'o-',label=s); a.set_title(kv); a.grid(alpha=.3)
ax[0].legend(); fig.suptitle('Cross-site timeline, 1.5 km radius around each fort/site centre (dry season, Landsat 5/7 → Sentinel-2)')
plt.tight_layout(); plt.savefig('../previews/sites_timeline.png',dpi=100)
with open('sites_epoch_metrics.csv','w',newline='') as fo:
    w=csv.DictWriter(fo,fieldnames=list(allr[0])); w.writeheader(); w.writerows(allr)
print(len(allr))
