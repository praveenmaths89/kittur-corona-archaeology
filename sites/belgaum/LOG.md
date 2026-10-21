# belgaum_fort processing log (IST)
## 2026-10-20
- ~19:28-19:31 raw CORONA .tgz copied from ~/Downloads to raw/corona/ (sha256 of original and copy identical; raw/corona/SHA256.txt), extracted into corona/<entity>/.
- ~19:35-20:00 Sentinel-2 L2A 2026 dry-season 16x16 km subset fetched (code/fetch_s2.py; Hampi merges tiles 43PFS+43PFT of 2026-03-06 because the site lies at the tile edge).
- ~20:00-20:15 frame location: automatic thumbnail NCC (locate.py) and SIFT (sift_locate.py, sift_local.py) FAILED (no consistent matches across 60 years). Sites were found by hand from rivers/reservoirs (KRS reservoir and the Kaveri island; Tungabhadra), then refine.py (coarse NCC over scale/angle + patch-NCC ties + RANSAC affine + leave-one-out RMS), warp.py (5x5 km at 2 m), panel_metrics.py.
- No existing frame covers Belgaum fort (corner test in ../../analysis/corona_footprints.csv). Candidate to download: DS1045-1102DA222 (+DS1045-1102DF223 stereo), 31 Jan 1968. Only the S2 2026 subset is fetched.
## 2026-10-20 evening (IST)
- 20:13 folder renamed belgaum_fort -> belgaum. DA222 and DF223 .tgz copied to raw/corona (sha256 identical, raw/corona/SHA256.txt) and extracted.
- ~20:20 refine.py grid over DA222 pieces a/b: best piece b, rot 180, centre col 19000: 14 inliers / LOO RMS 19.6 m -> corona/DA222_fit.json; warp.py -> qgis/corona_1968_DA222_belgaum.tif (5x5 km, 2 m).
- code_digitize.py: moat traced by eye (automatic dark-ring extraction failed: interior trees darker than moat); code_panel.py: SoI 1924 | 1968 | 2026 panel.
- DF223: no consistent fit (<=4 inliers) -> no stereo DEM.
- Dry-season epochs via ../common/epoch_fetch.py (raw/epochs/*.tif + item JSON); metrics ../common/timeline.py.
