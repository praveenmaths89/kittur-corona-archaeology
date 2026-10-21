import cv2,numpy as np,json,rasterio,sys
from PIL import Image; Image.MAX_IMAGE_PIXELS=None
from rasterio.warp import transform
from rasterio.windows import from_bounds
from rasterio.transform import from_origin
big=Image.open('DS1045-1102DA224_b.tif')
s2=rasterio.open('../qgis/rasters/s2_dry_20260217_truecolour.tif')
sites={'kittur':(74.7911,15.6004,74.79107,15.60044),'nandagad':(74.5737,15.5789,74.57366,15.57888)}
for site,(wlon,wlat,clon,clat) in sites.items():
  J=json.load(open('gcp_%s.json'%site)); An=np.array(J['An'])
  x,y=transform('EPSG:4326','EPSG:32643',[wlon],[wlat]); w=from_bounds(x[0]-6000,y[0]-6000,x[0]+6000,y[0]+6000,s2.transform)
  st=s2.window_transform(w)   # s-window px -> UTM
  cx,cy=transform('EPSG:4326','EPSG:32643',[clon],[clat]); cx,cy=cx[0],cy[0]
  res=2.0; n=2500; X0=round(cx-2500); Y0=round(cy+2500)
  jj,ii=np.meshgrid(np.arange(n)+0.5,np.arange(n)+0.5)
  E=X0+jj*res; N=Y0-ii*res
  inv=~st; sx=(E-st.c)/st.a; sy=(N-st.f)/st.e
  Ai=cv2.invertAffineTransform(An)
  u=Ai[0,0]*sx+Ai[0,1]*sy+Ai[0,2]; v=Ai[1,0]*sx+Ai[1,1]*sy+Ai[1,2]
  x0,y0=int(u.min())-5,int(v.min())-5; x1,y1=int(u.max())+5,int(v.max())+5
  cr=np.array(big.crop((x0,y0,x1,y1)))
  out=cv2.remap(cr,(u-x0).astype(np.float32),(v-y0).astype(np.float32),cv2.INTER_AREA if False else cv2.INTER_LINEAR,borderValue=0)
  t=from_origin(X0,Y0,res,res)
  o='../qgis/rasters/corona_1968_%s.tif'%site
  with rasterio.open(o,'w',driver='GTiff',width=n,height=n,count=1,dtype='uint8',crs='EPSG:32643',transform=t,compress='deflate',tiled=True,nodata=0) as d:
    d.write(out,1); d.update_tags(SOURCE='USGS EarthExplorer CORONA KH-4A DS1045-1102DA224 (mission 1045-1, aft, 31 Jan 1968), piece b',METHOD='affine, chained SIFT-free patch NCC vs Sentinel-2 20260217 + manual checks')
  print(o, 'fullres px size m ~', res/np.sqrt(abs(np.linalg.det(Ai[:,:2]))*1/100) )
  cl=cv2.createCLAHE(2,(16,16)); cv2.imwrite('../previews/corona_1968_%s.png'%site,cl.apply(cv2.resize(out,(1250,1250),interpolation=cv2.INTER_AREA)))
