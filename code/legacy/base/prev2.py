import rasterio,numpy as np,matplotlib,sys;matplotlib.use("Agg");import matplotlib.pyplot as plt
from rasterio.warp import transform_bounds
from rasterio.windows import from_bounds
import pandas as pd
R="qgis/rasters/"
gz=pd.read_csv("gazetteer.csv").dropna(subset=["lat"])
def panel(name,lat,lon,soi,out):
    d=0.0233; bb=(lon-d,lat-d,lon+d,lat+d)
    P=[("S2 true colour 17 Feb 2026 (dry)","s2_dry_20260217_truecolour",None),("S2 false colour 10 Oct 2026","s2_newestlowcloud_20261010_falsecolour",None),
    ("S2 NDVI dry 17 Feb 2026","s2_dry_20260217_ndvi","RdYlGn"),("DEM hillshade (GLO-30)","cop_dem30_hillshade","gray"),
    ("DEM local relief, 500 m (m)","cop_dem30_localrelief_500m","RdBu_r"),(f"Survey of India {soi[0]}, 1924 (rough georef)",soi[1],None)]
    fig,ax=plt.subplots(2,3,figsize=(18,12))
    for a,(t,f,cmap) in zip(ax.flat,P):
        with rasterio.open(R+f+".tif") as s:
            b=transform_bounds("EPSG:4326",s.crs,*bb); w=from_bounds(*b,transform=s.transform); x=s.read(window=w,boundless=True).astype("float32")
        ext=[bb[0],bb[2],bb[1],bb[3]]
        if x.shape[0]==3: a.imshow(x.transpose(1,2,0).astype("uint8"),extent=ext)
        else:
            kw=dict(vmin=-0.1,vmax=0.8) if "ndvi" in f else (dict(vmin=-8,vmax=8) if "relief" in f else {})
            im=a.imshow(np.where(x[0]==-9999,np.nan,x[0]),cmap=cmap,extent=ext,**kw); plt.colorbar(im,ax=a,shrink=.7)
        sub=gz[(gz.lat.between(bb[1],bb[3]))&(gz.lon.between(bb[0],bb[2]))]
        for _,r in sub.iterrows(): a.plot(r.lon,r.lat,"c+" if r.confidence=="confident" else "yx",ms=14,mew=2)
        a.set_xlim(bb[0],bb[2]);a.set_ylim(bb[1],bb[3]);a.set_title(t)
    fig.suptitle(f"{name} (~5 x 5 km). cyan + = confident gazetteer point, yellow x = approximate");plt.tight_layout();plt.savefig(out,dpi=110);plt.close()
panel("Sangolli",15.71708,74.83373,("48 I/14","SoI_48_I_14_Belgaum_District__1924__roughgeoref"),"previews/sangolli_panel.png")
panel("Nandagad",15.57888,74.57366,("48 I/10","SoI_48_I_10_Belgaum_District__1924__c_roughgeoref"),"previews/nandagad_panel.png")
