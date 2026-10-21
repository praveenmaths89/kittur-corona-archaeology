import numpy as np,rasterio,cv2,json,csv,matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from rasterio.warp import transform
from rasterio.windows import from_bounds
R='../qgis/rasters/'
S=[('Kittur fort','corona_1968_kittur.tif','DA224 31 Jan 1968',15.5995,74.7880,1300),
   ('Old Sangoli','corona_1968DA223_oldsangoli.tif','DA223 31 Jan 1968',15.7466,74.8337,1400),
   ('Sampgaon','corona_1968DA223_sampgaon.tif','DA223 31 Jan 1968',15.7954,74.7585,1400),
   ('Bail-Hongal','corona_1968DA223_bailhongal.tif','DA223 31 Jan 1968',15.8164,74.8569,1400),
   ('Tigadi (Tigdi?)','corona_1968DA223_tigadi.tif','DA223 31 Jan 1968',15.7958,74.7165,1400)]
s2=rasterio.open(R+'s2_dry_20260217_truecolour.tif')
fig,axs=plt.subplots(2,5,figsize=(20,8.6))
cl=cv2.createCLAHE(2,(8,8))
for j,(nm,f,lab,la,lo,w) in enumerate(S):
    x,y=[v[0] for v in transform('EPSG:4326','EPSG:32643',[lo],[la])]
    r=rasterio.open(R+f); a=r.read(1,window=from_bounds(x-w/2,y-w/2,x+w/2,y+w/2,r.transform),boundless=True)
    axs[0,j].imshow(cl.apply(a),cmap='gray'); axs[0,j].set_title(f'{nm}\nCORONA {lab}',fontsize=10)
    b=s2.read([1,2,3],window=from_bounds(x-w/2,y-w/2,x+w/2,y+w/2,s2.transform),boundless=True).astype(float).transpose(1,2,0)
    b=np.clip(b/np.percentile(b,99),0,1)**0.8; axs[1,j].imshow(b); axs[1,j].set_title('Sentinel-2 L2A 17 Feb 2026',fontsize=10)
    for k in (0,1): axs[k,j].set_xticks([]);axs[k,j].set_yticks([])
fig.suptitle(f'Gazetteer (1884) forts of the Kittur country on CORONA 1968 vs 2026 — panels {S[1][5]/1000:.1f} km wide (Kittur {S[0][5]/1000:.1f} km); DA223 placement ±100–200 m (coarse)',fontsize=12)
plt.tight_layout(); plt.savefig('../previews/findings_regional.png',dpi=110)
T=[dict(site='Kittur fort',gazetteer='Lower fort and citadel; Lawe 1825 "weak and ruined"; Welsh: citadel "nowhere commanded though conspicuous for many miles" (Gaz. pp. 577-578)',ref_line=43108,frames='DA224, DA217, DF217 (DF224 at film edge)',in_1968='visible: lower-fort enclosure, moat, 3-ring citadel',in_2026='surviving in part (citadel mound, enclosure lines partly overbuilt)',status='surviving (partly)'),
 dict(site='Sangoli small fort',gazetteer='Kittur desai "consented to give a small fort at Sangoli to serve as a post" (1803, Wellesley campaign) (Gaz. ~p. 580)',ref_line=43388,frames='DA223, DF224',in_1968='compact village on S bank of Malaprabha; rectilinear block possible (fort not resolved)',in_2026='site inside/at edge of Malaprabha (Navilutirtha) reservoir outline; dry-season water 47-99 ha within 600 m (2020-26)',status='lost (submerged/abandoned village site)'),
 dict(site='Sampgaon fort',gazetteer='Besieged and taken in 1683 by Prince Muhammad Muazzam after a two-day attack; earliest seat of the Kittur desais (Gaz. p. ~600)',ref_line=44961,frames='DA223 (DF224 edge)',in_1968='village visible; curvilinear road/field line S of the core is a possible enclosure trace (tentative)',in_2026='village core extant; no enclosure identifiable at 10 m',status='not identified (possible trace 1968)'),
 dict(site='Bail-Hongal fort',gazetteer='Rani Chennamma and the ladies "kept under watch in Bail-Hongal fort" after Dec 1824',ref_line=29700,frames='DA223',in_1968='town and large tank (W of town) visible; no clear fort outline',in_2026='town much expanded; tank survives',status='not identified'),
 dict(site='Tigdi earthen fort',gazetteer='"Tigdi, a small town defended by an earthen fort" (17th-c. itinerary quoted in Gaz.); identification with Tigadi, Bailhongal tq. is tentative',ref_line=27760,frames='DA223',in_1968='compact village with straight W and S edges ~450 m (possible fort perimeter, tentative); tank in village',in_2026='village extant; a ~2 sq km reservoir NW of the village did not exist in 1968',status='uncertain'),
 dict(site='Pratapgad, Murgod',gazetteer='Ruined fort built 1809 by Malla Sarja desai of Kittur (Gaz. p. ~585)',ref_line=44184,frames='none (outside DA223/DF224 footprints)',in_1968='not covered',in_2026='not assessed',status='not covered')]
with open('regional_forts.csv','w',newline='') as f:
    wr=csv.DictWriter(f,fieldnames=list(T[0])); wr.writeheader(); wr.writerows(T)
