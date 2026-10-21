import rasterio,numpy as np,cv2,json,matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from rasterio.warp import reproject,Resampling,transform
from rasterio.transform import from_origin
from shapely.geometry import shape
D=json.load(open('analysis/fort_digitized.json'))
x,y=[v[0] for v in transform('EPSG:4326','EPSG:32643',[74.5222],[15.8634])]; H=1500; g=4
T=from_origin(x-H,y+H,g,g); N=int(2*H/g)
def get(f,bands,res=Resampling.bilinear):
    s=rasterio.open(f); out=np.zeros((len(bands),N,N),np.float32)
    for k,b in enumerate(bands): reproject(rasterio.band(s,b),out[k],dst_transform=T,dst_crs='EPSG:32643',resampling=res)
    return out
soi=get('raw/SoI_48_I_09_Belgaum_District__1924__c_roughgeoref.tif',[1,2,3]).transpose(1,2,0)
co=get('qgis/corona_1968_DA222_belgaum.tif',[1])[0]
import glob; s2=get(glob.glob('raw/sentinel/*5band.tif')[0],[3,2,1]).transpose(1,2,0)
fig,ax=plt.subplots(1,3,figsize=(18,6.4))
ax[0].imshow(np.clip(soi/255,0,1)); ax[0].set_title('Survey of India 48 I/09 (1924), corner georef only (~100s m)',fontsize=10)
ax[1].imshow(cv2.createCLAHE(2,(8,8)).apply(np.clip(co,0,255).astype('uint8')),cmap='gray'); ax[1].set_title('CORONA DA222 31 Jan 1968 (LOO RMS 20 m)',fontsize=10)
ax[2].imshow(np.clip(s2/np.percentile(s2,99),0,1)**0.8); ax[2].set_title('Sentinel-2 L2A 2026',fontsize=10)
for a in ax:
    for k,c in [('inner','y'),('outer','r')]:
        xs,ys=zip(*shape(D[k]).exterior.coords); a.plot([(v-(x-H))/g for v in xs],[((y+H)-v)/g for v in ys],c,lw=1)
    a.set_xlim(0,N);a.set_ylim(N,0);a.set_xticks([]);a.set_yticks([])
r=D['res']; fig.suptitle(f"Belgaum fort: moat (digitized on 1968) inner line {r['inner_wall_line_ha']:.1f} ha, outer edge {r['moat_outer_edge_ha']:.1f} ha (OSM 51.8 ha); 3x3 km",fontsize=12)
plt.tight_layout(); plt.savefig('previews/compare_belgaum.png',dpi=110)
