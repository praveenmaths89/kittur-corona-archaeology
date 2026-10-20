# Task C: Monte Carlo propagation of georeferencing + digitizing error (N=1000, seed 1824)
import numpy as np,rasterio,json
from shapely import wkt
from shapely.affinity import affine_transform
from scipy.ndimage import map_coordinates
rng=np.random.default_rng(1824); N=1000
feats=[wkt.loads(l) for l in open('feats_utm.wkt')]
names=['main enclosure (lower fort)','N/W moat line','east outer line','NW pond','E pond','ring outer','ring middle','ring core']
x0,y0=feats[0].centroid.x,feats[0].centroid.y  # error model centred on fort
R='../qgis/rasters/'
dems={'Copernicus GLO-30':rasterio.open(R+'cop_dem30_elevation.tif'),'CORONA 1967 stereo':rasterio.open(R+'corona1967_dem_kittur_smooth16m.tif')}
DZ={k:(v.read(1).astype(float),v.transform) for k,v in dems.items()}
def zs(k,xs,ys):
    Z,T=DZ[k]; c,r=~T*(np.asarray(xs),np.asarray(ys)); return map_coordinates(Z,[r-0.5,c-0.5],order=1,cval=np.nan)
def relief(k,core,cx,cy):
    b=core.bounds; xs,ys=np.meshgrid(np.arange(b[0],b[2],5),np.arange(b[1],b[3],5))
    top=np.nanmax(zs(k,xs.ravel(),ys.ravel()))
    a=np.linspace(0,2*np.pi,72,endpoint=False); rr=np.arange(300,601,50)
    A,Rr=np.meshgrid(a,rr); base=np.nanmedian(zs(k,cx+Rr*np.sin(A),cy+Rr*np.cos(A)))
    return top-base
res={n:[] for n in names}; dist=[]; hts={k:{'citadel':[],'lower':[]} for k in DZ}
for i in range(N):
    edge=rng.uniform(50,100); se=np.sqrt(max(edge**2-25**2,0)/(2*2500**2))
    E=rng.normal(0,se,(2,2)); t=rng.normal(0,25/np.sqrt(2),2)
    def g(geom,loc):
        a,b,c,d=1+E[0,0],E[0,1],E[1,0],1+E[1,1]
        xo=x0-(a*x0+b*y0)+t[0]+loc[0]; yo=y0-(c*x0+d*y0)+t[1]+loc[1]
        G=affine_transform(geom,[a,b,c,d,xo,yo])
        # vertex digitizing noise 4 m (2 px)
        if G.geom_type=='Polygon':
            co=np.array(G.exterior.coords); co[:-1]+=rng.normal(0,4,(len(co)-1,2)); co[-1]=co[0]
            from shapely.geometry import Polygon; return Polygon(co).buffer(0)
        from shapely.geometry import LineString; co=np.array(G.coords)+rng.normal(0,4,(len(G.coords),2)); return LineString(co)
    locs=[rng.normal(0,10,2) for _ in feats]   # independent local (non-affine) residual per feature
    gs=[g(f,l) for f,l in zip(feats,locs)]
    for n,G in zip(names,gs): res[n].append(G.area/1e4 if G.geom_type in ('Polygon','MultiPolygon') else G.length)
    dist.append(gs[0].centroid.distance(gs[7].centroid))
    for k in DZ:
        sv=2.0 if k.startswith('Cop') else 10.0
        hts[k]['citadel'].append(relief(k,gs[7].buffer(30),gs[7].centroid.x,gs[7].centroid.y)+rng.normal(0,sv))
        hts[k]['lower'].append(relief(k,gs[0].buffer(-60),gs[0].centroid.x,gs[0].centroid.y)) if False else None
        c=gs[0].centroid; inner=np.nanmedian(zs(k,c.x+rng.normal(0,80,200),c.y+rng.normal(0,80,200)))
        a=np.linspace(0,2*np.pi,72,endpoint=False); ring=np.nanmedian(zs(k,c.x+450*np.sin(a),c.y+450*np.cos(a)))
        hts[k]['lower'].append(inner-ring+rng.normal(0,sv/2))
def ci(v): v=np.array(v,float); v=v[np.isfinite(v)]; return dict(median=float(np.median(v)),lo95=float(np.percentile(v,2.5)),hi95=float(np.percentile(v,97.5)))
out={'N':N,'model':'vertical noise 2 m (Copernicus) / 10 m (CORONA stereo) on summit, half that on lower-fort means; citadel relief = max inside ring core+30 m minus median at 300-600 m; lower-fort relief = median within ~80 m of centroid minus median on 450 m circle; translation 25 m RMS at fort; random linear term giving 50-100 m RMS at 2.5 km (crop edge); 10 m/axis local residual per feature; 4 m vertex digitizing noise',
 'areas_ha_or_length_m':{n:ci(v) for n,v in res.items()},'fort_citadel_distance_m':ci(dist),
 'heights_m':{k:{kk:ci(vv) for kk,vv in v.items()} for k,v in hts.items()},
 'nominal':{'fort_citadel_m':feats[0].centroid.distance(feats[7].centroid)}}
json.dump(out,open('montecarlo_results.json','w'),indent=1)
for n,v in out['areas_ha_or_length_m'].items(): print(n,{k:round(x,2) for k,x in v.items()})
print('dist',out['fort_citadel_distance_m']); print(json.dumps(out['heights_m'],indent=0))
