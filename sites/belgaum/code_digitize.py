# Belgaum fort, CORONA DA222 31 Jan 1968, 2 m grid. Moat centre-line digitized by eye on the 900x900 px zoom (offset row 1100, col 1000).
# Moat half-width 12 m and glacis band 50 m are measured by eye from the same zoom (assumptions, +-5 m).
import json,rasterio
from shapely.geometry import Polygon,mapping
from rasterio.transform import xy
r=rasterio.open('qgis/corona_1968_DA222_belgaum.tif'); oy,ox=1100,1000
P=[(300,235),(400,230),(480,240),(540,265),(585,320),(610,400),(625,480),(630,560),(610,620),(560,650),(480,665),(400,665),(320,660),(260,640),(215,590),(190,520),(180,450),(200,380),(230,310),(260,265)]
C=Polygon([xy(r.transform,y+oy,x+ox) for x,y in P])
C0=C; C=C0.buffer(-12); inner=C0.buffer(-24); outer=C0; glacis=C0.buffer(50)  # traced line sits on the outer moat bank (checked on overlay)
res=dict(moat_centreline_ha=C.area/1e4,inner_wall_line_ha=inner.area/1e4,moat_outer_edge_ha=outer.area/1e4,with_glacis_ha=glacis.area/1e4,moat_area_ha=(outer.area-inner.area)/1e4,perimeter_centreline_m=C.length,
 osm_way_138292670_ha=51.8)
b=C.bounds; res['ew_m']=b[2]-b[0]; res['ns_m']=b[3]-b[1]
json.dump(dict(res=res,crs=str(r.crs),centreline=mapping(C),inner=mapping(inner),outer=mapping(outer)),open('analysis/fort_digitized.json','w'))
print(res)
import numpy as np,cv2
A=r.read(1)[oy:oy+900,ox:ox+900]; vis=cv2.cvtColor(cv2.createCLAHE(2,(8,8)).apply(A),cv2.COLOR_GRAY2BGR)
inv=~r.transform
for g,col in [(inner,(0,255,255)),(outer,(0,0,255))]:
    pts=np.array([[(inv*(x,y))[0]-ox,(inv*(x,y))[1]-oy] for x,y in g.exterior.coords],np.int32); cv2.polylines(vis,[pts],True,col,2)
cv2.imwrite('previews/fort_digitized_1968.png',vis)
