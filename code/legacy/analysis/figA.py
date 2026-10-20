import numpy as np,rasterio,pickle,json,matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.colors import LightSource
from shapely import wkt
R='../qgis/rasters/'; d=rasterio.open(R+'cop_dem30_elevation.tif'); Z=d.read(1).astype(float); T=d.transform
P=pickle.load(open('battle.pkl','rb')); J=json.load(open('battle_results.json'))
vc=np.load('vis_citadel.npy'); vl=np.load('vis_lower.npy'); camp=np.load('camp_mask.npy')
feats=[wkt.loads(l) for l in open('feats_utm.wkt')]
ext=[T.c,T.c+T.a*Z.shape[1],T.f+T.e*Z.shape[0],T.f]
hs=LightSource(315,45).hillshade(Z,vert_exag=3,dx=30,dy=30)
cx,cy=P['cit'][1],P['cit'][2]
def base(ax,half):
    ax.imshow(hs,cmap='gray',extent=ext,alpha=1); ax.set_xlim(cx-half,cx+half); ax.set_ylim(cy-half,cy+half)
    for g in [feats[0],feats[5]]: x,y=g.exterior.xy; ax.plot(x,y,'k',lw=.8)
    ax.set_xticks([]);ax.set_yticks([])
fig,axs=plt.subplots(1,3,figsize=(18,6.4))
for ax,(v,nm,col) in zip(axs[:2],[(vc,'Citadel summit (eye 10 m)','Reds'),(vl,'Lower fort centre (eye 10 m)','Blues')]):
    base(ax,8000); m=np.ma.masked_where(~v,v.astype(float)); ax.imshow(m,cmap=col,vmin=0,vmax=1.3,alpha=.55,extent=ext)
    for r in (1000,1500,5000): ax.add_patch(plt.Circle((cx,cy),r,fill=False,ls='--',lw=.7,color='k'))
    s=J['citadel' if 'Citadel' in nm else 'lower_fort']
    ax.set_title(f"{nm}\nvisible {s['visible_km2_5km']:.1f} km² within 5 km ({100*s['frac_5km']:.0f}%), {s['visible_km2_25km']:.0f} km² within 25 km",fontsize=10)
ax=axs[2]; base(ax,3200)
im=ax.imshow(np.ma.masked_where(np.hypot(*np.meshgrid(np.arange(Z.shape[1])*30+ext[0]-cx,ext[3]-np.arange(Z.shape[0])*30-cy))>3200,Z),cmap='terrain',extent=ext,alpha=.55,vmin=720,vmax=810)
plt.colorbar(im,ax=ax,fraction=.04,label='Copernicus GLO-30 surface height (m)')
for r in (1000,1500): ax.add_patch(plt.Circle((cx,cy),r,fill=False,ls='--',lw=.8,color='k')); ax.text(cx+r*0.71,cy+r*0.71,f'{r/1000:g} km',fontsize=8)
for (z,a,b) in J['annulus_maxz']: pass
pts=[(15.5929,74.78416,'769.5 m @0.59 km'),(15.58475,74.77717,'786.7 m @1.74 km'),(15.58284,74.76738,'806.4 m @2.71 km')]
from rasterio.warp import transform
for la,lo,t in pts:
    x,y=transform('EPSG:4326','EPSG:32643',[lo],[la]); ax.plot(x,y,'^',color='m'); ax.text(x[0]+60,y[0],t,fontsize=8,color='m')
ax.plot(cx,cy,'r*',ms=12); ax.set_title('"Nowhere commanded"? Citadel summit 769.4 m.\nNo higher ground within 1.5 km (tie at 0.59 km, within DSM error);\nhigher ground begins ~1.6–1.7 km SW',fontsize=10)
plt.tight_layout(); plt.savefig('../previews/findings_viewshed.png',dpi=130)
# approaches
fig,axs=plt.subplots(1,2,figsize=(16,8))
ax=axs[0]; ax.imshow(hs,cmap='gray',extent=ext)
for nm,p in P['paths'].items():
    x,y=zip(*p['coords']); ax.plot(x,y,lw=2,label=f"from {nm.replace('_',' ')}: {p['length_km']:.1f} km, arrives from {p['arrival_bearing_deg']:.0f}°")
ax.plot(cx,cy,'r*',ms=10); ax.legend(loc='lower left',fontsize=9); ax.set_title('Least-cost approaches (cost = slope; ×2 dark 1968 tone; ponds/moat ×25–50)\nstarts clipped to DEM edge on the Belgaum (NW) and Dharwad (SE) bearings',fontsize=10); ax.set_xticks([]);ax.set_yticks([])
ax=axs[1]; c=rasterio.open(R+'corona_1968_kittur.tif'); A=c.read(1); t=c.transform
ax.imshow(A,cmap='gray',extent=[t.c,t.c+2*A.shape[1],t.f-2*A.shape[0],t.f])
lx,ly=P['low'][1],P['low'][2]; ax.set_xlim(lx-900,lx+900); ax.set_ylim(cy-450,ly+650)
cols={'battery_close_12yd':'red','glacis_crest_30_100m':'orange','advanced_post_east_gate':'yellow','escalade_gap_lower_upper':'cyan'}
from shapely.geometry import MultiPolygon
for k,g in P['zones'].items():
    gs=g.geoms if hasattr(g,'geoms') else [g]
    for i,gg in enumerate(gs):
        if gg.geom_type!='Polygon': continue
        x,y=gg.exterior.xy; ax.fill(x,y,color=cols[k],alpha=.35,label=k.replace('_',' ') if i==0 else None)
for nm,p in P['paths'].items():
    x,y=zip(*p['coords']); ax.plot(x,y,lw=1.5)
cm=np.ma.masked_where(~camp,camp.astype(float)); ax.imshow(cm,cmap='Greens',vmin=0,vmax=1.5,alpha=.5,extent=ext)
for g in feats[:8]:
    if g.geom_type=='Polygon': x,y=g.exterior.xy
    else: x,y=g.xy
    ax.plot(x,y,'w',lw=.6)
ax.plot(*P['gate'],'r^',ms=8); ax.text(P['gate'][0]+15,P['gate'][1],'assumed East Gate',color='r',fontsize=8)
ax.legend(loc='lower right',fontsize=8); ax.set_title('TENTATIVE siege zones vs Trewman, 8 Dec 1824, on CORONA 31 Jan 1968\n(green = dead ground 1.2–3 km, slope<3°, hidden from both forts: candidate camp)',fontsize=10); ax.set_xticks([]);ax.set_yticks([])
plt.tight_layout(); plt.savefig('../previews/findings_approaches.png',dpi=130)
