# Task A: viewsheds, commanding-ground test, least-cost approaches, candidate siege zones (Copernicus GLO-30 + CORONA 1968)
import numpy as np,rasterio,json,cv2
from rasterio.warp import transform
from scipy.ndimage import map_coordinates
from skimage.graph import route_through_array
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt

from shapely.geometry import shape,Point,LineString
R='../qgis/rasters/'
d=rasterio.open(R+'cop_dem30_elevation.tif'); Z=d.read(1).astype(float); T=d.transform
from shapely import wkt; feats=[wkt.loads(l) for l in open('feats_utm.wkt')]
fort=feats[0]; ring=feats[5]; core=feats[7]
def rc(x,y): c,r=~T*(x,y); return r-0.5,c-0.5
def zat(x,y): r,c=rc(x,y); return float(map_coordinates(Z,[[r],[c]],order=1)[0])
# summit = highest DEM cell inside ring outer; lower fort observer = highest cell in main enclosure
def top(poly):
    best=(-1e9,None)
    for r in range(Z.shape[0]):
        pass
    xs,ys=np.meshgrid(np.arange(Z.shape[1]),np.arange(Z.shape[0])); X,Y=T*(xs+0.5,ys+0.5)
    b=poly.bounds; m=(X>b[0])&(X<b[2])&(Y>b[1])&(Y<b[3])
    idx=[(Z[i,j],X[i,j],Y[i,j]) for i,j in zip(*np.where(m)) if poly.contains(Point(X[i,j],Y[i,j]))]
    if not idx: c=poly.centroid; return zat(c.x,c.y),c.x,c.y
    return max(idx)
cit=top(ring); low=top(fort); lowc=fort.centroid; lowz=zat(lowc.x,lowc.y)
print('citadel top',cit,'lower fort top',low,'lower centroid z',lowz)
def viewshed(x0,y0,h=10,maxd=25000,nr=2880,step=10):
    z0=zat(x0,y0)+h; vis=np.zeros(Z.shape,bool)
    ds=np.arange(step,maxd,step); k=0.13; Re=6371000
    for a in np.linspace(0,2*np.pi,nr,endpoint=False):
        xs=x0+ds*np.sin(a); ys=y0+ds*np.cos(a); r,c=rc(xs,ys)
        ok=(r>=0)&(c>=0)&(r<Z.shape[0]-1)&(c<Z.shape[1]-1); r,c,dd=r[ok],c[ok],ds[ok]
        zz=map_coordinates(Z,[r,c],order=1)-dd**2*(1-k)/(2*Re)
        ang=(zz-z0)/dd; mx=np.maximum.accumulate(np.r_[-1e9,ang[:-1]])
        v=ang>=mx; vis[np.round(r).astype(int)[v],np.round(c).astype(int)[v]]=True
    return vis,z0
out={}
for nm,(z,x,y) in {'citadel':cit,'lower_fort':(low[0],lowc.x,lowc.y)}.items():
    v,z0=viewshed(x,y); out[nm]=v
    xs,ys=np.meshgrid(np.arange(Z.shape[1]),np.arange(Z.shape[0])); X,Y=T*(xs+0.5,ys+0.5); D=np.hypot(X-x,Y-y)
    res={'obs_x':x,'obs_y':y,'ground_z':zat(x,y),'eye_z':z0,'visible_km2_25km':v.sum()*900/1e6,
         'visible_km2_5km':(v&(D<5000)).sum()*900/1e6,'frac_5km':float((v&(D<5000)).sum()/(D<5000).sum()),
         'frac_10km':float((v&(D<10000)).sum()/(D<10000).sum()),'max_vis_dist_km':float(D[v].max()/1000),
         'p95_vis_dist_km':float(np.percentile(D[v],95)/1000)}
    # commanding ground: cells within 1.5 km higher than observer ground
    zg=zat(x,y)
    for rr in (1000,1500):
        m=(D<rr)&(D>60)&(Z>zg); res[f'higher_cells_within_{rr}m']=int(m.sum())
        res[f'max_z_within_{rr}m']=float(Z[(D<rr)&(D>60)].max())
    out[nm+'_s']=res; print(nm,json.dumps(res,indent=0))
np.save('vis_citadel.npy',out['citadel']); np.save('vis_lower.npy',out['lower_fort'])
# commanded test from any ground within 1.5 km: can an observer on ground there see inside the lower fort from above citadel?
xs,ys=np.meshgrid(np.arange(Z.shape[1]),np.arange(Z.shape[0])); X,Y=T*(xs+0.5,ys+0.5)
Dc=np.hypot(X-cit[1],Y-cit[2])
ann=[(float(Z[(Dc>=a)&(Dc<b)].max()),a,b) for a,b in [(0,250),(250,500),(500,1000),(1000,1500),(1500,2000),(2000,3000),(3000,5000)]]
print('max z by annulus from citadel',ann)
# ---- least cost
sl=np.degrees(np.arctan(np.hypot(*np.gradient(Z,30))))
cost=1+(sl/4.0)**2
# CORONA 1968 land cover inside crop: dark tone (trees/scrub/wet) x2 ; ponds/moat x25
c68=rasterio.open(R+'corona_1968_kittur.tif'); A=c68.read(1).astype(float)
Ab=cv2.resize(cv2.GaussianBlur(A,(0,0),5),None,fx=1,fy=1)
r_,c_=np.mgrid[0:Z.shape[0],0:Z.shape[1]]
cc,rr=~c68.transform*(X,Y); inside=(cc>=0)&(rr>=0)&(cc<A.shape[1])&(rr<A.shape[0])
tone=np.full(Z.shape,np.nan); tone[inside]=Ab[rr[inside].astype(int),cc[inside].astype(int)]
p25=np.nanpercentile(tone,25); dark=inside&(tone<p25)
cost[dark]*=2.0
for i in (3,4): 
    p=feats[i]; m=np.array([p.contains(Point(a,b)) for a,b in zip(X[inside],Y[inside])]); ii=np.where(inside); cost[ii[0][m],ii[1][m]]=50
moat=feats[1].buffer(15)
m=np.array([moat.contains(Point(a,b)) for a,b in zip(X[inside],Y[inside])]); ii=np.where(inside); cost[ii[0][m],ii[1][m]]=25
# walls impassable except at east gate (target outside the east face)
ex=fort.bounds[2]; gate=(ex+25,lowc.y)   # point 25 m outside east face midline (tentative East Gate)
def cell(x,y): c,r=~T*(x,y); return int(r),int(c)
starts={'Belgaum_NW':None,'Dharwad_SE':None}
for nm,(lon,lat) in {'Belgaum_NW':(74.5000,15.8670),'Dharwad_SE':(75.0100,15.4580)}.items():
    x,y=transform('EPSG:4326','EPSG:32643',[lon],[lat]); x,y=x[0],y[0]
    # clamp along the bearing to DEM edge minus 1 km
    vx,vy=x-gate[0],y-gate[1]; L=np.hypot(vx,vy); t=1.0
    while True:
        px,py=gate[0]+vx*t,gate[1]+vy*t; r,c=cell(px,py)
        if 30<r<Z.shape[0]-30 and 30<c<Z.shape[1]-30: break
        t-=0.01
    starts[nm]=(px,py,L)
paths={}
for nm,(px,py,L) in starts.items():
    pth,cst=route_through_array(cost,cell(px,py),cell(*gate),fully_connected=True,geometric=True)
    pts=[T*(c+0.5,r+0.5) for r,c in pth]; ls=LineString(pts)
    # arrival bearing over last 1.5 km
    last=[p for p in pts if np.hypot(p[0]-gate[0],p[1]-gate[1])<1500][0]
    brg=(np.degrees(np.arctan2(last[0]-gate[0],last[1]-gate[1]))+360)%360
    vis_frac=np.mean([out['citadel'][r,c] for r,c in pth])
    vis_last2=np.mean([out['citadel'][r,c] for (r,c),p in zip(pth,pts) if np.hypot(p[0]-gate[0],p[1]-gate[1])<2000])
    paths[nm]=dict(start=(px,py),length_km=ls.length/1000,straight_km=np.hypot(px-gate[0],py-gate[1])/1000,cost=float(cst),
       arrival_bearing_deg=float(brg),frac_visible_from_citadel=float(vis_frac),frac_visible_last2km=float(vis_last2),coords=pts)
    print(nm,{k:v for k,v in paths[nm].items() if k!='coords'})
json.dump({'citadel':out['citadel_s'],'lower_fort':out['lower_fort_s'],'annulus_maxz':ann,'gate':gate,
           'paths':{k:{kk:vv for kk,vv in v.items() if kk!='coords'} for k,v in paths.items()}},open('battle_results.json','w'),indent=1,default=float)
# candidate zones (tentative)
from shapely.ops import unary_union
from shapely.geometry import box
east=LineString([(ex,lowc.y-120),(ex,lowc.y+120)])
zones={
 'battery_close_12yd': Point(gate).buffer(1).buffer(0).union(east.buffer(0)).buffer(12).difference(fort),
 'glacis_crest_30_100m': fort.buffer(100).difference(fort.buffer(30)).intersection(box(ex-10,lowc.y-200,ex+200,lowc.y+200)),
 'advanced_post_east_gate': Point(gate).buffer(150).difference(fort.buffer(12)),
 'escalade_gap_lower_upper': fort.buffer(170).intersection(ring.buffer(170)).difference(fort).difference(ring),
}
# camp: 1.2-3 km from fort, slope<3deg, not visible from citadel, along approaches
Df=np.hypot(X-lowc.x,Y-lowc.y)
camp=(Df>1200)&(Df<3000)&(sl<3)&(~out['citadel'])&(~out['lower_fort'])
np.save('camp_mask.npy',camp)
import geopandas as gp
g=gp.GeoDataFrame({'zone':list(zones)+list(paths),'kind':['siege_zone']*len(zones)+['least_cost_path']*len(paths)},
  geometry=list(zones.values())+[LineString(p['coords']) for p in paths.values()],crs='EPSG:32643') if False else None
import pickle; pickle.dump(dict(zones=zones,paths=paths,cit=cit,low=(low[0],lowc.x,lowc.y),gate=gate,camp_cells=int(camp.sum())),open('battle.pkl','wb'))
print('camp km2',camp.sum()*900/1e6)
