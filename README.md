# Kittur desk-only base map (built 20 Oct 2026)
Area: 74.45–74.95 E, 15.45–15.90 N (~54 x 50 km; Kittur, Sangolli, Bailhongal, Belagavi, Khanapur, Nandagad). All data free, no login.

Open `kittur_basemap.html` in a browser (keep the `web/` folder next to it). QGIS: drag `qgis/rasters/*.tif` and `qgis/kittur_vectors.gpkg` (no .qgz built; QGIS not installed on the box).

## Layers and acquisition dates (UTC)
| Layer | Source | Date |
|---|---|---|
| Sentinel-2 L2A, newest (41% cloud) | Earth Search STAC, S2B_43PDT_20261015_0_L2A | 15 Oct 2026 05:44 |
| Sentinel-2 L2A, newest low-cloud | S2C_43PDT_20261010_0_L2A (12.5%) | 10 Oct 2026 |
| Sentinel-2 L2A, monsoon | S2B_43PDT_20260915_0_L2A (21.6%) | 15 Sep 2026 |
| Sentinel-2 L2A, dry season | S2B_43PDT_20260217_0_L2A (0%) | 17 Feb 2026 |
| Sentinel-1 RTC (from GRD), VV/VH dB + RGB (VV, VH, VV-VH) | Microsoft Planetary Computer (anonymous SAS), S1D ..._20261019T0055.._0099B3 x2 frames | 19 Oct 2026 00:55 |
| Landsat 5 TM C2 L2 | Planetary Computer, LT05_L2SP_146049_19990304 | 4 Mar 1999 |
| Copernicus DEM GLO-30 | s3 copernicus-dem-30m (N15 E074) | DEM epoch 2011–2015 |
| Survey of India 1" sheets 48 I/13, I/14 (1924), plus I/09, I/10 raw | Zenodo 10.5281/zenodo.18133392 ("Old Survey of India Maps") | surveyed 1922–23, publ. 1924 |
| OSM features | Overpass (kumi mirror) | 20 Oct 2026 |
| Basemaps (view only) | Esri World Imagery, Google Satellite tiles | date varies, not analysed |

Note: Sentinel-2 passes at 05:34 UTC (e.g. 12, 17 Oct) only cover the eastern strip (east of ~74.79 E); only the 05:44 passes cover the whole box.

## Derived products
NDVI = (B08-B04)/(B08+B04). Hillshade az 315/alt 45. Local relief = DEM minus 510 m moving mean (17x17 px). Composites are 2–98% stretched (visual only, not reflectance).

## Caveats
- SoI sheets georeferenced from the 4 neatline corners only, in WGS84 (sheets are on Everest/Indian datum) — expect errors of a few hundred metres.
- GLO-30 is a surface model (includes trees/buildings); 30 m cannot resolve small mounds.
- gazetteer.csv: "approximate" points are proxies (e.g. Thackeray's death site = fort centroid; Bailhongal = town point, not the fort/samadhi).
- 1884 Bombay Gazetteer vol XXI Belgaum: https://archive.org/details/in.ernet.dli.2015.35167 (cited, not parsed).
- CORONA: not downloaded (USGS EarthExplorer needs a free login).

## Added 20 Oct 2026 (afternoon)
- SoI 48 I/09 and I/10 (1924) rough-georeferenced (I/10 covers Nandagad/Khanapur; I/06 was downloaded but covers 74.25-74.5E, west of Nandagad).
- previews/sangolli_panel.png, previews/nandagad_panel.png.
- Gazetteer: Rayanna samadhi Nandagad (Wikipedia SPM list), Chennamma samadhi (address only, approx), Sangolli points; original Sangolli was submerged by the Malaprabha project (The Hindu, 2015).
