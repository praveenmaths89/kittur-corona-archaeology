import rasterio,numpy as np
from PIL import Image
from rasterio.transform import from_gcps
from rasterio.control import GroundControlPoint as G
Image.MAX_IMAGE_PIXELS=None
for f,s,(x0,y0,x1,y1),(lon0,lat1) in [("48_I_14_Belgaum_District__1924_.jpg",5736/840,(60,105,785,858),(74.75,15.75)),
                                     ("48_I_13_Belgaum_District__1924_.jpg",5928/848,(47,88,800,842),(74.75,16.0))]:
    a=np.array(Image.open("historical_maps/"+f).convert("RGB")).transpose(2,0,1)
    X0,Y0,X1,Y1=[v*s for v in (x0,y0,x1,y1)]
    g=[G(Y0,X0,lon0,lat1),G(Y0,X1,lon0+.25,lat1),G(Y1,X0,lon0,lat1-.25),G(Y1,X1,lon0+.25,lat1-.25)]
    t=from_gcps(g)
    o="qgis/rasters/SoI_"+f.replace(".jpg","_roughgeoref.tif")
    with rasterio.open(o,"w",driver="GTiff",width=a.shape[2],height=a.shape[1],count=3,dtype="uint8",crs="EPSG:4326",transform=t,compress="jpeg",photometric="YCBCR",tiled=True) as d: d.write(a)
    print(o)
