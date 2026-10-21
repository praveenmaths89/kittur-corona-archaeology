import rasterio,numpy as np
from PIL import Image
from rasterio.transform import from_gcps
from rasterio.control import GroundControlPoint as G
Image.MAX_IMAGE_PIXELS=None
for f,dw,(x0,y0,x1,y1),(lon0,lat1) in [("48_I_10_Belgaum_District__1924__c.jpg",708,(53,75,667,692),(74.5,15.75)),
                                     ("48_I_09_Belgaum_District__1924__c.jpg",830,(57,95,775,832),(74.5,16.0))]:
    im=Image.open("historical_maps/raw/"+f).convert("RGB"); s=im.size[0]/dw; a=np.array(im).transpose(2,0,1)
    X0,Y0,X1,Y1=[v*s for v in (x0,y0,x1,y1)]
    t=from_gcps([G(Y0,X0,lon0,lat1),G(Y0,X1,lon0+.25,lat1),G(Y1,X0,lon0,lat1-.25),G(Y1,X1,lon0+.25,lat1-.25)])
    o="qgis/rasters/SoI_"+f.replace(".jpg","_roughgeoref.tif")
    with rasterio.open(o,"w",driver="GTiff",width=a.shape[2],height=a.shape[1],count=3,dtype="uint8",crs="EPSG:4326",transform=t,compress="jpeg",photometric="YCBCR",tiled=True) as d: d.write(a)
    print(o)
