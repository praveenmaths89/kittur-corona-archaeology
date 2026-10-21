import rasterio,numpy as np,matplotlib;matplotlib.use("Agg");import matplotlib.pyplot as plt
from rasterio.warp import transform_bounds
from rasterio.windows import from_bounds
R="qgis/rasters/";bb=(74.765,15.578,74.815,15.622)
P=[("S2 true colour 17 Feb 2026 (dry)","s2_dry_20260217_truecolour",None),("S2 false colour 17 Feb 2026","s2_dry_20260217_falsecolour",None),
("S2 NDVI dry 17 Feb 2026","s2_dry_20260217_ndvi","RdYlGn"),("DEM hillshade (GLO-30)","cop_dem30_hillshade","gray"),
("DEM local relief, 500 m (m)","cop_dem30_localrelief_500m","RdBu_r"),("Survey of India 48 I/14, 1924 (rough)","SoI_48_I_14_Belgaum_District__1924__roughgeoref",None)]
fig,ax=plt.subplots(2,3,figsize=(18,12))
for a,(t,f,cmap) in zip(ax.flat,P):
    with rasterio.open(R+f+".tif") as s:
        b=transform_bounds("EPSG:4326",s.crs,*bb); w=from_bounds(*b,transform=s.transform)
        x=s.read(window=w,boundless=True).astype("float32")
    if x.shape[0]==3: a.imshow(x.transpose(1,2,0).astype("uint8"),extent=[bb[0],bb[2],bb[1],bb[3]])
    else:
        kw=dict(vmin=-0.1,vmax=0.8) if "ndvi" in f else (dict(vmin=-8,vmax=8) if "relief" in f else {})
        im=a.imshow(np.where(x[0]==-9999,np.nan,x[0]),cmap=cmap,extent=[bb[0],bb[2],bb[1],bb[3]],**kw); plt.colorbar(im,ax=a,shrink=.7)
    a.plot(74.79107,15.60044,"c+",ms=18,mew=2); a.set_title(t)
fig.suptitle("Kittur fort area (cyan + = OSM fort centroid), ~5.4 x 4.9 km");plt.tight_layout();plt.savefig("previews/kittur_fort_panel.png",dpi=110)
