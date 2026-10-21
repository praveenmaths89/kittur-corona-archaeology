import rasterio,numpy as np,geopandas as gpd,pandas as pd,folium,glob,os
from rasterio.warp import calculate_default_transform,reproject,Resampling
from PIL import Image
import matplotlib; matplotlib.use("Agg"); import matplotlib.cm as cm
R="qgis/rasters/"
def to_png(path,name,mode="rgb",maxw=2200):
    with rasterio.open(path) as s:
        t,W,H=calculate_default_transform(s.crs,"EPSG:4326",s.width,s.height,*s.bounds)
        f=max(1,W/maxw); W2,H2=int(W/f),int(H/f); t2=t*t.scale(W/W2,H/H2)
        n=3 if mode=="rgb" else 1
        d=np.zeros((n,H2,W2),"float32")
        for b in range(n): reproject(rasterio.band(s,b+1),d[b],dst_transform=t2,dst_crs="EPSG:4326",resampling=Resampling.average,dst_nodata=0 if mode=="rgb" else np.nan)
    if mode=="rgb":
        img=d.transpose(1,2,0).astype("uint8"); a=(img.sum(2)>0)*255; img=np.dstack([img,a]).astype("uint8")
    else:
        x=d[0]; x[x==-9999]=np.nan
        if mode=="ndvi": c=cm.RdYlGn((np.clip(x,-0.1,0.8)+0.1)/0.9)
        elif mode=="gray": c=cm.gray(np.nan_to_num(x)/255)
        else: c=cm.RdBu_r((np.clip(x,-8,8)+8)/16)
        c[np.isnan(x)]=0; img=(c*255).astype("uint8")
    Image.fromarray(img).save(f"web/{name}.png")
    w,s_,e,n_=t2.c,t2.f+t2.e*H2,t2.c+t2.a*W2,t2.f
    return f"web/{name}.png",[[s_,w],[n_,e]]
layers=[("S2 NEWEST 15 Oct 2026 (41% cloud) true colour","s2_newest_20261015_truecolour","rgb",True),
("S2 15 Oct 2026 false colour","s2_newest_20261015_falsecolour","rgb",False),
("S2 newest low-cloud 10 Oct 2026 true colour","s2_newestlowcloud_20261010_truecolour","rgb",False),
("S2 10 Oct 2026 false colour (NIR)","s2_newestlowcloud_20261010_falsecolour","rgb",False),
("S2 10 Oct 2026 NDVI","s2_newestlowcloud_20261010_ndvi","ndvi",False),
("S2 dry 17 Feb 2026 true colour","s2_dry_20260217_truecolour","rgb",False),
("S2 dry 17 Feb 2026 false colour","s2_dry_20260217_falsecolour","rgb",False),
("S2 dry 17 Feb 2026 NDVI","s2_dry_20260217_ndvi","ndvi",False),
("S2 monsoon 15 Sep 2026 true colour","s2_monsoon_20260915_truecolour","rgb",False),
("S2 monsoon 15 Sep 2026 NDVI","s2_monsoon_20260915_ndvi","ndvi",False),
("Sentinel-1 RTC 19 Oct 2026 VV/VH/ratio","s1_rtc_20261019_composite_VV_VH_ratio","rgb",False),
("Landsat 5 4 Mar 1999 true colour","landsat5_19990304_truecolour","rgb",False),
("Landsat 5 4 Mar 1999 false colour","landsat5_19990304_falsecolour","rgb",False),
("Copernicus DEM hillshade","cop_dem30_hillshade","gray",False),
("Copernicus DEM local relief (500 m)","cop_dem30_localrelief_500m","lrm",False),
("Survey of India 48 I/14 (1924) rough georef","SoI_48_I_14_Belgaum_District__1924__roughgeoref","rgb",False),
("Survey of India 48 I/10 (1924, Nandagad/Khanapur) rough georef","SoI_48_I_10_Belgaum_District__1924__c_roughgeoref","rgb",False),
("Survey of India 48 I/09 (1924, Belgaum) rough georef","SoI_48_I_09_Belgaum_District__1924__c_roughgeoref","rgb",False),
("Survey of India 48 I/13 (1924) rough georef","SoI_48_I_13_Belgaum_District__1924__roughgeoref","rgb",False)]
m=folium.Map(location=[15.65,74.70],zoom_start=11,tiles=None,control_scale=True)
folium.TileLayer("OpenStreetMap",name="OSM basemap").add_to(m)
folium.TileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",attr="Tiles &copy; Esri &mdash; Source: Esri, Maxar, Earthstar Geographics, and the GIS User Community",name="Esri World Imagery (view only, date varies)").add_to(m)
folium.TileLayer("https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",attr="Imagery &copy; Google",name="Google Satellite (view only, date varies)",max_zoom=21).add_to(m)
for lab,f,mode,show in layers:
    p,b=to_png(R+f+".tif",f,mode); ov=folium.raster_layers.ImageOverlay(np.zeros((2,2,4)),bounds=b,name=lab,opacity=0.9,show=show); ov.url=p; ov.add_to(m)
osm=gpd.read_file("osm_raw.gpkg")
sty={"historic":"#8b0000","water":"#1f78b4","waterway":"#1f78b4","road":"#ff7f00","worship":"#6a3d9a","place":"#333"}
for cat in ["road","waterway","water","historic","worship","place"]:
    sub=osm[osm.category==cat]
    fg=folium.FeatureGroup(name=f"OSM {cat} ({len(sub)})",show=cat in("historic","water"))
    pts=sub[sub.geom_type=="Point"]; oth=sub[sub.geom_type!="Point"]
    if len(oth): folium.GeoJson(oth[["name","category","osm_id","geometry"]],style_function=lambda x,c=sty[cat]:{"color":c,"weight":2,"fillOpacity":0.3},tooltip=folium.GeoJsonTooltip(["name","osm_id"])).add_to(fg)
    for _,r in pts.iterrows(): folium.CircleMarker([r.geometry.y,r.geometry.x],radius=3,color=sty[cat],tooltip=f"{r['name']} ({r.osm_id})").add_to(fg)
    fg.add_to(m)
gz=pd.read_csv("gazetteer.csv").dropna(subset=["lat"]); fg=folium.FeatureGroup(name="Historical gazetteer (Kittur 1824)")
for _,r in gz.iterrows():
    html=f"<b>{r['name']}</b><br>{r.role_in_history}<br><i>Location: {r.confidence}</i><br>Coords: {r.lat}, {r.lon}<br>Source: {r.coord_source}<br>{'' if pd.isna(r.history_source) or r.history_source=='' else '<a href='+r.history_source+' target=_blank>history ref</a>'}"
    folium.Marker([r.lat,r.lon],popup=folium.Popup(html,max_width=320),tooltip=r["name"],icon=folium.Icon(color="red" if r.confidence=="confident" else "orange",icon="star")).add_to(fg)
fg.add_to(m); folium.LayerControl(collapsed=False).add_to(m)
m.get_root().html.add_child(folium.Element('<div style="position:fixed;bottom:10px;left:10px;z-index:9999;background:white;padding:6px;font-size:12px;border:1px solid #888">Newest Sentinel-2: 15 Oct 2026 (41% tile cloud) &middot; newest low-cloud: 10 Oct 2026 (12.5%) &middot; dry: 17 Feb 2026 &middot; monsoon: 15 Sep 2026 (21.6%) &middot; Sentinel-1: 19 Oct 2026 &middot; Landsat 5: 4 Mar 1999 &middot; SoI sheets 1924 (rough georef, ~100s m error)<br>Red star = confident location, orange = approximate</div>'))
m.save("kittur_basemap.html")
g=gpd.GeoDataFrame(gz,geometry=gpd.points_from_xy(gz.lon,gz.lat),crs=4326)
g.to_file("qgis/kittur_vectors.gpkg",layer="historical_gazetteer")
for cat in osm.category.unique():
    s=osm[osm.category==cat]
    for gt in s.geom_type.unique(): s[s.geom_type==gt].to_file("qgis/kittur_vectors.gpkg",layer=f"osm_{cat}_{gt.lower()}")
print("done")
