# hampi processing log (IST)
## 2026-10-20
- ~19:28-19:31 raw CORONA .tgz copied from ~/Downloads to raw/corona/ (sha256 of original and copy identical; raw/corona/SHA256.txt), extracted into corona/<entity>/.
- ~19:35-20:00 Sentinel-2 L2A 2026 dry-season 16x16 km subset fetched (code/fetch_s2.py; Hampi merges tiles 43PFS+43PFT of 2026-03-06 because the site lies at the tile edge).
- ~20:00-20:15 frame location: automatic thumbnail NCC (locate.py) and SIFT (sift_locate.py, sift_local.py) FAILED (no consistent matches across 60 years). Sites were found by hand from rivers/reservoirs (KRS reservoir and the Kaveri island; Tungabhadra), then refine.py (coarse NCC over scale/angle + patch-NCC ties + RANSAC affine + leave-one-out RMS), warp.py (5x5 km at 2 m), panel_metrics.py.
- DS1025-1071DF071 extracted, not located; stereo DEM not attempted. DA077 fit (21 inliers, LOO RMS ~20 m) is PROVISIONAL: visual check inconclusive (Oct 1965 river in spate vs Mar 2026 dry channel).
