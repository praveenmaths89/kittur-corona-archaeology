# Kittur, Sangolli and the 1824 landscape: tentative findings from 1924-2026 imagery

Status: desk-based and unverified on the ground. Every finding below is tentative. Positional errors are stated per dataset.
Figures are in `previews/`. Vectors are in `qgis/kittur_vectors.gpkg`, layer `corona1968_features`.

## Data and georeferencing
| Epoch | Source | Georeferencing / accuracy |
|---|---|---|
| 1924 | Survey of India 1-inch sheets 48 I/14, 48 I/10 (Zenodo scans) | rough 4-corner georef, errors of 100s of m |
| 11 Nov 1967 | CORONA KH-4A DS1044-2134DA217 (aft) and DF217 (forward), USGS EarthExplorer | co-registered to the 1968 Kittur crop by SIFT + 2nd-order polynomial, 22 and 52 GCPs, RMS 1.7 and 2.9 m relative to 1968 |
| 31 Jan 1968 | CORONA KH-4A DS1045-1102DA224 (aft) | Kittur: chained patch matching to Sentinel-2 plus a manual fort/hillock check, est. 50-100 m absolute; Nandagad: 98 checkpoints, RMS 21 m |
| 31 Jan 1968 | CORONA KH-4A DS1045-1102DF224 (forward) | Sangolli: transferred from DA224 overlap (294 GCPs, 16 m) and refined against Sentinel-2 (75 checkpoints, RMS 26 m) |
| 1990-91, 1999-2001, 2009 | Landsat 5/7 Collection 2 L2, Jan-Mar, median of the 4 least-cloudy scenes (Planetary Computer) | native, 30 m |
| 2016-17, 2020, 2026 | Sentinel-2 L2A, Jan-Mar, median of 3-4 scenes (Planetary Computer, Earth Search) | native, 10 m |
| 2026 | Sentinel-1 RTC 19 Oct 2026, Copernicus DEM GLO-30 | native |

Scene IDs per epoch are in `epochs/*.json`; metrics are in `epochs/metrics.csv`.

## Temporal sampling design
Why these years:
1. Epochs bracket the known drivers of landscape change, not arbitrary dates.
   - 1924 SoI: the earliest systematic survey available to us, about a century after the 1824 siege.
   - 1967-68 CORONA: the last imagery before the Malaprabha (Navilutheertha / Renuka Sagar) dam. India-WRIS lists the dam's completion year as 1972 (archived record "Malaprabha Dam D05454"); CIFRI's reservoir database gives "Date of Commissioned 1972"; CWC's DRIP list gives 1973. The reservoir drowned the riverine landscape around Sangolli.
   - CORONA also predates the reservoir's canal command (Renuka Sagara irrigates about 1,961 km2 according to its Wikipedia entry). Using it as a pre-irrigation baseline is an inference from the dam date, not a separately sourced claim.
2. Roughly decadal sampling after the dam (1990, 2000, 2009/10, 2016/17, 2020, 2026) captures reservoir operation and town growth. Kittur grew from 6,300 people in 1881 (Gazetteer of the Bombay Presidency, vol. XXI, Belgaum, 1884, p. 576) to 16,144 in 2011 (Census 2011 via Wikipedia "Kittur").
3. Every optical epoch is dry season (Jan-Mar), matching the CORONA dates (Nov 1967, Jan 1968). Seasonal crop and water differences are kept as small as the archive allows. Multi-scene medians cut cloud and SLC-off gaps; Landsat 7 2009 is SLC-off.
4. Two dates from CORONA (Nov 1967 and Jan 1968) give a short-baseline check that the 1968 features are real ground features, not artefacts of one scan.
5. A 1975 KH-9 frame was NOT checked. I could not verify from here whether a D3C1209 frame centred near 75.25E reaches 74.78E. Check the footprint in EarthExplorer; the epoch is noted as a gap.

## Numbered findings (tentative)

1. Kittur fort in 1968 had two parts: a low polygonal enclosure and a separate fortified hillock 530 m to its SSW (`findings_fort1968.png`, `findings_ring.png`).
   - Main enclosure: about 360 m E-W by 400 m N-S, 13.4 ha to my digitised outer wall line. The OSM outline (way/97204879) gives 10.4 ha. The ground level is about 730 m.
   - A dark moat band wraps it on the north and west, and a tree-lined outer line with bastions runs on the east. Round ponds sit inside the NW corner (about 55 m across) and outside the east wall (about 80 m).
   - The SW structure has three concentric rings: outer 280 x 316 m (6.9 ha), middle 208 x 232 m (3.8 ha), inner dark core 132 x 160 m (1.7 ha).
   - The rings appear in both 11 Nov 1967 and 31 Jan 1968, which rules out a single-scan artefact.

2. The concentric structure is a hillock about 28 m high, and the stereo pair suggests the core is raised.
   - In the Copernicus DEM the summit is 769 m against about 740 m around it, with symmetric W-E and N-S profiles. Local relief inside the outer ring is +11.8 m, against +0.3 m in an 80-100 m buffer around it.
   - The 1967 DA/DF stereo pair (`findings_anaglyph_1967_fort.png`) shows a coherent high-pass parallax anomaly over the core of about -4.9 px. Trees show the same sign, which is consistent with raised ground.
   - Calibrating the parallax to absolute height needs proper photogrammetric modelling; I did not attempt this.
   - It is the highest ground within 1.5 km (see Finding 9). Higher ground (787-806 m) lies 1.7-2.7 km to the SW.

3. The two-part plan matches Lieutenant Lawe's 1825 description, quoted in the 1884 Belgaum Gazetteer (pp. 577-578), of a "lower fort and a citadel".
   - Lawe put the lower fort at one-sixth of Belgaum fort's area and the citadel at one-tenth. Using Belgaum fort's OSM outline (way/138292670, 51.8 ha), that gives about 8.6 ha and about 5.2 ha.
   - Measured: lower enclosure 10.4-13.4 ha; hillock rings 3.8 ha (middle) to 6.9 ha (outer). Lawe's citadel/lower ratio is 0.6; the measured ratio is 0.28-0.66.
   - Col. Welsh (1828, in the same Gazetteer) called the "upper battery" a strong citadel, "nowhere commanded though conspicuous for many miles". That fits a 28 m hillock that is the local high point within about 1 km.
   - Lawe's "deep quarry in its centre" is a candidate for the dark core seen in 1968. However, the 30 m DEM shows a summit there, not a pit, so a central quarry would have to be smaller than the DEM resolves. This point is unresolved.
   - Caveats: the Belgaum outline may include its moat, and my digitising may overstate the walls. So this is a consistency check, not a proof.

4. The ditch evidence fits only partly.
   - The Gazetteer (p. 578) describes, as of 1882: a ditch about 16 ft deep near the gateway where Thackeray fell; a second ditch and walls about 80 yards (73 m) further on; and the palace ruins about 150 yards east of a temple.
   - In 1968 there are two dark linear bands on the N and W sides: the outer moat band, and the band just outside the inner wall line. They are about 50-130 m apart, which is the same order as 73 m.
   - The gateway itself cannot be identified at 2 m resolution with 50-100 m georeferencing error.
   - The 1824 "advanced fortified post" that was carried on 3 Dec, and the battery raised on it (Gazetteer p. 403), cannot be located from the text.
   - The hillock is one candidate for that post, because a battery 530 m from the lower fort could "effect a practicable breach". The citadel reading in Finding 3 competes with this. Both are untested hypotheses for the National Archives files to settle: Foreign Political 3 Dec 1824 Nos. 8-10; Foreign Secret 7 Jan 1825 No. 17, on property captured at the Fort of Kittoor and Lt Col Deacon.

5. Since 1968 the town has spread over the area around the hillock, but the hillock itself survives as a green island.
   - In 1968 open ground and fields surrounded the hillock rings. By 2016-2026 Sentinel-2 shows continuous built-up area around it.
   - Inside the outer ring, dry-season NDVI is 0.50, against 0.28 in the 80-100 m buffer around it (Feb 2026). The NDVI contrast grew from +0.03 (1990) to +0.17 (2020-26), so the hillock is now vegetation fenced in by houses.
   - An indicative bare/built index inside the fort enclosure rises from 0.02 (1990) to 0.18 (2026). This index is unreliable on dry fallow soil and should be read as a trend only.
   - The N/W moat band now shows almost no NDVI, SAR or DEM contrast (NDVI 0.34 vs 0.33; relief -1.6 vs -0.6 m). It looks largely infilled or built over, except where OSM still maps water bodies near the fort.

6. Old Sangoli, as mapped in 1924, stood on the Malaprabha's south bank about 3.3 km north of present Sangolli, and it is now at the reservoir edge (`findings_sangolli.png`, `compare_sangolli.png`).
   - The 1924 SoI sheet 48 I/14 labels "Sangoli" on the south bank, with a Thursday market.
   - The 1968 forward frame shows a dense nucleated village at about 15.7466N 74.8337E (±30 m) beside the pre-dam river.
   - At the present village (15.7172N) there were only fields in 1968.
   - The 1968 village centre lies inside the OSM reservoir outline, 14 m from its edge.
   - This supports reports that the original village was relocated because of the Malaprabha project (The Hindu, 2015, cited in `gazetteer.csv`). Whether this is Rayanna's birthplace village remains a historical identification, not something the imagery shows.

7. The old Sangoli site is exposed or flooded depending on reservoir storage (`findings_timeline.png`).
   - Dry-season open water (MNDWI > 0.1) within 600 m of the old village: 0 ha in 1990-91 and 2000, about 11 ha in 2009 and 2016-17, 99 ha in 2020, 47 ha in 2026.
   - Low-storage years therefore expose the old village footprint. Those years are the best targets for very-high-resolution archive imagery, or for any future drone or field visit.

8. A 1967 stereo-parallax DEM independently confirms the hillock but cannot resolve a central quarry (`findings_dem1967.png`, `qgis/rasters/corona1967_dem_kittur.tif`).
   - Method: SGBM N-S parallax on the co-registered DA217/DF217 pair at 2 m, with a linear height scale plus a quadratic trend fitted to Copernicus GLO-30 over the 5 x 5 km crop. The fitted scale is 0.31 px per m of height (B/H about 0.6, as expected for the 30 deg convergence); height noise is about 10 m (1 sigma at 30 m blocks).
   - Result: citadel core minus the 220-320 m annulus is +27 m in the 1967 stereo DEM and +30 m in Copernicus. The lower fort is +2 m (stereo) and +8 m (Copernicus).
   - The height scale is calibrated to Copernicus over the whole crop, not on the hill, so the stereo value is semi-independent.
   - Within the core, the centre is about 3 m HIGHER than the 30-70 m rim. No depression is detected at this noise level, so Lawe's "deep quarry in its centre" is not shown. It may be smaller than about 20 m, filled after 1825, or not this feature.
   - A rigorous DEM would need ASP (Ames Stereo Pipeline) with a proper KH-4A camera model. I did not install it, as it is a large download.

9. Viewsheds support Welsh's "conspicuous for many miles", and "nowhere commanded" holds within about 1.5 km (`findings_viewshed.png`). Copernicus GLO-30, eye height 10 m, refraction k = 0.13.
   - Citadel summit (769.4 m): 35.8 km² visible within 5 km (46%), 153 km² within 25 km. Visible cells reach the 25 km analysis limit.
   - Lower-fort centre (731.9 m): 23.3 km² within 5 km (30%), 38 km² within 25 km. It is overlooked by the citadel, and by 738 DEM cells higher than itself within 1 km.
   - Commanding-ground test (no ground higher than the citadel within cannon range, 1-1.5 km): passes, with one marginal case.
     - The highest cell within 1.5 km is 769.5 m, at 0.59 km WSW. That is a 0.1 m tie, well inside DSM error and possibly trees.
     - The highest cell at 1.0-1.5 km is 766.8 m.
     - Clearly higher ground starts 1.6-1.7 km SW (786.7 m at 1.74 km) and reaches 806.4 m at 2.71 km. That is beyond effective 1824 field-gun range but within long range of siege guns (tentative).

10. Least-cost approaches converge on the east side of the lower fort (`findings_approaches.png`). Cost = 1 + (slope/4°)²; ×2 on dark 1968 tone (trees/wet ground); ×25-50 on ponds and the moat. Starts are clipped to the DEM edge on the Belgaum and Dharwad bearings.
   - From Belgaum (NW): 46.9 km (straight line 43.1 km). It skirts the moat and arrives from 338°, i.e. from the N. 98% of the last 2 km is visible from the citadel.
   - From Dharwad (SE): 20.6 km (straight line 19.1 km). It arrives from 133°, i.e. from the SE. 100% of the last 2 km is visible.
   - Both routes end at the target I assumed: an East Gate 25 m outside the midpoint of the east face. So the convergence is partly built in. The real finding is that no covered final approach exists, because the last 2 km of both routes is in view of the citadel.

11. Siege zones consistent with Trewman's letter of 8 Dec 1824 are mapped as TENTATIVE polygons (NAI Foreign Political, Cons. 7 Jan 1825 No. 17; `findings_approaches.png`). None is located by evidence.
   - "Most advanced Post, nearest to the East Gate": within 150 m of the assumed gate, 4.0 ha.
   - "Crest of the Glacis": a band 30-100 m outside the east face, 2.8 ha.
   - Battery "close within 12 [yards?]": 12 m from the east face, 0.05 ha. That is a point-blank position, which is consistent with threatening to blow in the gates.
   - "Escalade between the lower, and the Upper Fort": the 4.9 ha gap where 170 m buffers of the two works overlap. It lies on the SSW side, opposite the east gate. This fits Conry's corps entering there and "penetrating to the Gates" from inside.
   - "Principal Street ... enfiladed": not locatable. The 1968 street grid lies E and S of the fort, but its 1824 layout is unknown.
   - Candidate camps: dead ground 1.2-3 km from the fort, slope < 3°, hidden from both the summit and the lower fort. This totals 3.6 km² of scattered patches.

12. Regional survey of the Gazetteer's forts of the Kittur country (`findings_regional.png`, `release/data/regional_forts.csv`). DA223 placement is coarse (±100-200 m).
   - Kittur: visible in 1968; partly surviving today.
   - Sangoli small fort (given as a British post in 1803): the 1968 village is clear on DA223 too, but no fort is resolved. The site is now submerged or at the reservoir edge, so LOST.
   - Sampgaon (taken by Prince Muazzam in 1683): a possible curvilinear enclosure trace S of the village core in 1968. None is identifiable in 2026.
   - Bail-Hongal fort (where Chennamma was held): no fort outline identified in 1968. The town's W tank survives.
   - Tigdi earthen fort: a compact village with straight W/S edges about 450 m long, a possible perimeter (uncertain). A reservoir of about 2 km² has formed NW of the village since 1968.
   - Pratapgad, Murgod (built 1809): outside my frames.

13. Tanks within 15 km of Kittur, OSM 2026 vs a 1968 CORONA mosaic (`analysis/osm_tanks_vs_1968.json`). The mosaic is DF224 north plus DA224 south at 10 m, using extrapolated affines.
   - Of 29 OSM water bodies ≥ 1 ha: 0 are dark in 1968 (pre-1968 tanks, including Ranagatti Kere by the fort); 3 are intermediate; 10 show no water signature (new, enlarged or dry in Jan 1968; tentative); 9 are outside coverage.
   - The largest, 134 ha at 15.703N 74.720E, is not a water body in 1968.
   - 1968 tanks that are lost by 2026 were not inventoried systematically. The automatic dark-blob test confuses tanks with tree clumps and irrigated fields.

14. Monte Carlo uncertainty: N = 1000, seed 1824.
   - Error model: 25 m RMS translation at the fort; a random linear term giving 50-100 m at 2.5 km; 10 m per feature local residual; 4 m vertex noise; vertical noise of 2 m (Copernicus) and 10 m (stereo).
   - 95% intervals:
     - Lower-fort enclosure: 13.37 (95%: 12.53-14.26) ha.
     - Rings: outer 6.92 (95%: 6.51-7.38), middle 3.78 (95%: 3.55-4.02), core 1.65 (95%: 1.54-1.77) ha.
     - Ponds: NW 0.23 (95%: 0.20-0.26), E 0.48 (95%: 0.43-0.52) ha.
     - N/W moat line: 1061 (95%: 1025-1096) m.
     - Fort-citadel distance: 533 (95%: 497-568) m.
   - Heights (summit minus the median at 300-600 m; a different baseline from Finding 8):
     - Citadel: 36.9 (95%: 33.0-40.7) m (Copernicus), 35.8 (95%: 16.9-55.4) m (1967 stereo).
     - Lower fort above its 450 m surroundings: 8.8 (95%: 6.5-11.3) m (Copernicus), 6.3 (95%: -3.9-16.5) m (stereo).
   - Lawe's ratio test (Finding 3) is robust to georeferencing: the lower-fort interval stays above his implied 8.6 ha.

15. Schematic 3D reconstruction c.1824 (`previews/findings_3d.png`, `kittur_3d_rotate.mp4`). Illustrative only.
   - Terrain: Copernicus GLO-30, bicubic to 5 m, 2× vertical exaggeration.
   - Drape: CORONA 31 Jan 1968.
   - ASSUMPTIONS:
     - Lower-fort ramparts 6 m high (5 m earth plus a 1 m parapet; Lawe gives a mud rampart and a 3 ft parapet, not heights), drawn 6 m wide.
     - East outer line 4.2 m.
     - Each citadel ring wall 4 m.
     - N/W moat 4.9 m deep (16 ft, the Gazetteer as of 1882) and 10 m wide (assumed).
     - Ponds 2 m deep.
     - The DSM's modern trees and buildings are left in the terrain.
     - Gates, bastion shapes and the palace are not modelled.

## Transferability (other sites, 20 Oct 2026; tentative)
Cross-site table: `sites/sites_summary.csv`; figure: `previews/sites_overview.png`. Each site has its own `raw/` (with sha256), `PROVENANCE.csv`, `LOG.md` and `code/` under `sites/<name>/`.

| Site | CORONA used | Georef | RMS | 2026 built / veg / water (%) | 1960s tone water / dark veg (%) |
|---|---|---|---|---|---|
| Kittur | DA224, DA217/DF217 | chained local affines | ~25 m near fort | see Finding 5 | - |
| Srirangapatna | DS1040-1039DA028, 2 Apr 1967 | patch-NCC + RANSAC affine, 11 of 46 ties | 22 m LOO (fit 17 m) | 14 / 68 / 1.7 | 4.6 / 25 |
| Hampi | DS1025-1071DA077, 10 Oct 1965 | same, 21 of 45 ties, PROVISIONAL | 20 m LOO (fit 18 m) | 33* / 44 / 0.3 | 12.0 / 18 |
| Belgaum fort | none covers it | - | - | - | - |

\* At Hampi, bare granite outcrop falls in the NDBI "built" class, so this value is not a built-up measure. The 1960s classes are panchromatic tone thresholds and are crude. An RMS from ≤ 21 automatic ties is optimistic.

What transferred:
- The pipeline (S2 subset, coarse NCC, patch ties, affine, panel, metrics) ran unchanged.
- Fully automatic frame finding (thumbnail NCC, SIFT) failed at both new sites, as it did in Kittur's farmland. I had to place the frames by hand from rivers and reservoirs.
- KH-4B DA028 gives about 2.8 m/px at Srirangapatna, near the frame end. KH-4 DA077 gives about 2.5 m/px.
- The Zenodo SoI collection (10.5281/zenodo.18133392, CC-BY-4.0) holds only 3 files for the Belgaum area. There is no 1924 sheet for Srirangapatna or Hampi there.

Observations (tentative):
- S1. Srirangapatna, 1967: a bastioned, polygonal fort outline with a light outer band (glacis/ditch) is clear at the W end of the Kaveri island, with the town grid inside (`sites/srirangapatna/previews/compare_srirangapatna.png`). Its NW face lies next to the north arm of the Kaveri.
  - Contemporary accounts put the 4 May 1799 breach in the NW face, approached by fording the river: Beatson, *A View of the Origin and Conduct of the War with Tippoo Sultaun* (1800); Baird's storming column. B. L. Rice, *Mysore Gazetteer* (1897), vol. II, Srirangapatna entry.
  - The imagery shows where that geometry lies; at about 20 m it cannot resolve the breach itself.
- S2. Srirangapatna, 2026: built-up land covers the fort interior and the E (Ganjam) side. The rail and highway corridor crosses the island E of the fort, and none of it shows in 1967. The two river arms keep their 1967 planform.
- H1. Hampi, 1965 vs 2026: the E-W granite ridges and the valley line up in both images. In Oct 1965 the river band is wide (post-monsoon flow below Tungabhadra dam, completed 1953), against a narrow channel in Mar 2026.
  - Monuments (the Group of Monuments at Hampi, UNESCO WHS no. 241, inscribed 1986) and the Vijayanagara-era canals (e.g. the Turtha/Raya canals) are NOT resolved or checked at this placement. That needs a confirmed georeference.
- B1. Belgaum fort (1818 siege, moat): no coverage. Best free candidate: DS1045-1102DA222, plus DF223 for stereo, 31 Jan 1968, the same mission as the Kittur frames. DS1025-2087DA105 does not cover the fort: its N edge is about 15.80N at 74.52E.

### Belgaum fort (added 20 Oct 2026, evening)
- Frame: DS1045-1102DA222 (KH-4A aft, 31 Jan 1968), piece b, rotated 180°. Placed by coarse NCC plus patch-NCC ties and a RANSAC affine: 14 of 40 ties kept, fit RMS 15 m, **leave-one-out RMS 20 m**. A visual overlay on S2 2026 matches the moat ring and Kote Kere tank to about 1-2 S2 pixels.
- Panels: `sites/belgaum/previews/compare_belgaum.png` (SoI 48 I/09 1924 | CORONA 1968 | S2 2026) and `compare_belgaum_metrics.png`.
- Digitized on the 1968 frame (`sites/belgaum/analysis/fort_digitized.json`, `code_digitize.py`):
  - The moat is traced by eye. The moat width is set to 24 m, which matches the Gazetteer's 72 ft (22 m).
  - Inner wall line: **58.0 ha**. Moat centre-line: 61.3 ha. Moat outer edge: 64.8 ha.
  - Extent 876 × 846 m; centre-line perimeter 2831 m.
  - OSM way/138292670 gives 51.8 ha, about 6 ha (11%) less than my inner line.
- Belgaum Gazetteer 1884 (pp. 534-535, `sources/belgaum1884.txt` lines ~39915-39950), as of the 1880s:
  - "about 1000 yards long and 800 yards broad", i.e. 914 × 732 m.
  - "an irregular oval of 2900 yards perimeter", i.e. 2652 m.
  - "occupies an area of about 100 acres", i.e. 40.5 ha.
  - The ditch is "forty to fifty feet deep and about seventy-two feet wide"; the walls average 34 ft.
  - The esplanade is 600 yards broad.

Observations (tentative):
- B1. The 1968 moat ring is continuous all round and water- or vegetation-dark, with a light glacis or esplanade band outside. In 2026 the ring survives intact, but the built-up town now reaches the outer bank on the W and S.
  - The 600-yard esplanade the Gazetteer reports (pp. 398, 534) is gone in 2026.
  - In 1968 an open strip about 100-250 m wide survived on the E and N. The N side was the Kote Kere tank and fields.
- B2. My extent and perimeter agree with the Gazetteer: 876 × 846 m against 914 × 732 m, and 2831 m against 2652 m (7% longer). My area, however, is larger than its "about 100 acres" (58 against 40.5 ha). The 100 acres is probably a rounded or interior-only figure.
- B2 consequence for Kittur Finding 3: Lawe's 1/6 and 1/10 ratios give the following Kittur expectations.

  | Belgaum base area | Kittur lower fort | Kittur citadel |
  |---|---|---|
  | 40.5 ha (Gazetteer) | 6.8 ha | 4.1 ha |
  | 51.8 ha (OSM) | 8.6 ha | 5.2 ha |
  | 58.0 ha (this study) | 9.7 ha | 5.8 ha |

  The measured Kittur lower fort (12.5-14.3 ha, 95% interval) is above all three, so the ratio test stays a loose consistency check.
- B3. 1818 siege (Gazetteer pp. 398-399, citing Gleig's *Life of Munro*):
  - Munro arrived on 20 Mar 1818 and occupied the town (petha).
  - The first battery of three 12-pounders was "at a mosque opposite the north face", opening on 21 Mar "within eight hundred yards" (730 m). An enfilading battery in the town "swept the north face and the gateway".
  - The approach was dug in stages of 100-140 yards. A breaching battery of two 18-pounders, "within 550 yards" (500 m), opened on 3 Apr "on the left of the gateway". The fort surrendered on 11-12 Apr (p. 399 and line ~30333).
  - A dargah "bears marks of shot directed from Belgaum fort at General Munro's first battery" (line ~39365).
  - On the 1968 frame, the zone 500-730 m N and NW of the moat is the old town and the Kote Kere tank edge (map layer). I did not locate the mosque or dargah; identifying them would need the place descriptions plus a field check.
  - The Gazetteer names Munro. It mentions Pritzler only as commanding a separate force (p. 398, "unable to join the detachment of his corps with Brigadier-General Pritzler").
- B4. In 1826 Welsh built a causeway over the ditch on the western face (Gazetteer p. 535). I have not verified on the imagery whether a W crossing is visible; it is an open check.
- No stereo DEM: I could not locate the fort in DF223 by automatic matching (no consistent fit; the fort sits about 0.013° from the film edge).

### Second epochs and stereo (status)
- Srirangapatna DS1025-1071DA094 (10 Oct 1965): extracted, but a grid search over all 4 pieces and both orientations gave at most 6 inliers (LOO RMS ≥ 69 m). Not georeferenced, so there is no 1965 epoch.
- Hampi DS1025-1071DF071: same result (≤ 6 inliers). No stereo DEM. DA077 remains provisional.

### Older maps openly available (checked 20 Oct 2026)
- Belgaum: SoI 1" sheet 48 I/09 (surveyed 1922-23, published 1924), Zenodo 10.5281/zenodo.18133392, CC-BY-4.0. It is used in the panel; its corner-only georeference is good to about 100 m or more.
- Srirangapatna:
  - Wikimedia Commons category "Maps of Srirangapatna Fort" includes "Plan of the attack upon the NW angle of Seringapatam, 1799", "Plan of Fort Seringapatam", "Seringapatam 1801" and the 1792 siege plans from Dirom's *Narrative* (IA dli.venugopal.389).
  - Beatson (1800), *A View of the Origin and Conduct of the War with Tippoo Sultaun*: Internet Archive dli.granth.117032 and pli.kerala.rare.11817, public domain.
  - SoI half-inch sheet 57 D/N.E. (1928), AGS Library, UW-Milwaukee (via DPLA). Rights are per UWM's statement.
  - I have not downloaded or georeferenced any of these.
- Hampi:
  - SOAS Special Collections, "Map showing ruins of Hampi [Vijayanagar], Hospet Taluk, Bellary District", Madras Survey (archives.soas.ac.uk, F_MAP_D_30_40_Hampi). Access terms not checked.
  - NLS hosts georeferenced SoI one-inch sheets for parts of South India (maps.nls.uk/india/survey-of-india), but I have not verified that they cover Hampi.

## Georeferencing check (Kittur, 1968)
- Patch-correlation and SIFT GCP picking against Sentinel-2 (10 m) produced no consistent matches over Kittur farmland, and field boundaries are not resolvable at 10 m. I applied no TPS: there were too few reliable GCPs to fit one, and fitting one anyway would overfit.
- Independent checkpoints (not used in the fit):
  - Copernicus DEM summit centroid vs the CORONA citadel core centre: dE +2 m, dN -11 m.
  - East round pond vs the Sentinel-2 dark pond: about 10 m E, 30 m N.
  - Citadel hill vs the Sentinel-2 vegetated hill: about 20 m E, 30 m N.
  - Checkpoint RMS is about 25 m. That applies near the fort only; the crop margins remain at about 50-100 m.
- Because no correction was applied, the corona1968_features areas are unchanged.
- Reaching about 20 m across the full 5 km crop would need high-resolution GCPs (e.g. viewing Esri imagery and picking junctions by hand) or field GNSS.

## Limits
- Kittur's absolute georeferencing (50-100 m) is the weakest link. The 1924 sheets are only roughly placed.
- Digitising was done by eye, with about 10 m precision.
- Built-up mapping from Landsat/Sentinel indices is unreliable in this dry, bare-soil landscape.
- DS1045-1102DA223 is placed by a single coarse frame match plus a visual check (about 100-200 m); its crops are for presence/absence only.
- The 15 km 1968 mosaic extrapolates the local DF224 and DA224 affines (expect 100-300 m at the margins); it covers about 72% of the 32 x 32 km square.
- Copernicus GLO-30 is a surface model: trees and buildings raise heights, which affects the viewsheds and the commanding-ground test.
- Tank status uses Jan 1968 tone. Tanks dry in that season look like fields, so 'no water signature' does not prove a tank is new.
- Sources: Gazetteer of the Bombay Presidency vol. XXI, Belgaum (1884), archive.org item wbsl.17016, pp. 402-404 and 576-578 (text saved in `sources/belgaum1884.txt`); India-WRIS archived dam page; CIFRI reservoir database; CWC DRIP list; USGS EarthExplorer CORONA entity IDs above.

### Epoch timeline (Landsat 1990/2000/2010, S2 2016/2020/2026; Jan–Apr medians, r=1500 m)
See sites_epoch_metrics.csv and previews/sites_timeline.png. Landsat-vs-S2 values are not strictly comparable (sensor/resolution); trends tentative. Belgaum L2010 uses Landsat-7 (SLC-off gaps, median-filled).
