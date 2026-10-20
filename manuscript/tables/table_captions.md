# Table captions and notes

**Table 1.** Data sources.  
*File:* `Table1_data_sources.csv`; sheet `Table1` of `tables.xlsx`; `tables.docx` page 1.  
Note: CORONA dates are acquisition dates; scan pieces are USGS 7 µm scans. Scene identifiers of the median composites are listed in the epoch JSON files (raw/landsat, raw/sentinel, sites/*/raw/epochs).  

**Table 2.** Georeferencing and co-registration accuracy.  
*File:* `Table2_georeferencing_accuracy.csv`; sheet `Table2` of `tables.xlsx`; `tables.docx` page 2.  
Note: Automatic check: 500 m patches at 10 m, normalised cross-correlation (NCC) > 0.45 against Sentinel-2 (17 February 2026 at Kittur), offsets beyond 3 median absolute deviations removed. Its RMS includes matching noise over changed farmland as well as georeferencing error.  
Note: Checkpoints were not used in the fits.  

**Table 3.** Dimensions of the Kittur fort features digitised on CORONA DA224 (31 January 1968).  
*File:* `Table3_dimensions.csv`; sheet `Table3` of `tables.xlsx`; `tables.docx` page 3.  
Note: Monte Carlo: N = 1000, seed 1824; 25 m RMS translation, linear term 50-100 m at 2.5 km, 10 m local residual, 4 m vertex noise; vertical noise 2.0 m (Copernicus) and 10.0 m (stereo).  
Note: Relief: citadel = maximum within 30 m of the core minus the median on 300-600 m circles; lower fort = interior median minus the median on a 450 m circle.  
Note: Viewsheds from Copernicus GLO-30 (a surface model), observer 10 m above ground, refraction coefficient 0.13.  

**Table 4.** Archival descriptions of Kittur and Belgaum forts compared with the image measurements.  
*File:* `Table4_archival_vs_measured.csv`; sheet `Table4` of `tables.xlsx`; `tables.docx` page 4.  
Note: Quotations follow the 1884 Gazetteer text and the NAI viewer transcription (OCR, not visually proofread). Implied areas apply Lawe's fractions to Belgaum fort taken as 40.5 ha (Gazetteer, 100 acres), 51.8 ha (OpenStreetMap way 138292670) or 58.0 ha (inner wall line traced on CORONA DA222). Zones from Trewman's letter are geometric constructions, not located positions. [?] marks an uncertain reading in the transcription.  

**Table 5.** Forts of the Kittur country named in the 1884 Gazetteer: evidence in 1968 and 2026.  
*File:* `Table5_regional_forts.csv`; sheet `Table5` of `tables.xlsx`; `tables.docx` page 5.  
Note: DA223 placements are coarse (positional uncertainty about 100-200 m) and support presence/absence statements only.  

**Table 6.** Dry-season change metrics at Kittur and Old Sangoli, 1968-2026.  
*File:* `Table6_temporal_metrics.csv`; sheet `Table6` of `tables.xlsx`; `tables.docx` page 6.  
Note: January-March median composites; water MNDWI > 0.1; bare/built NDBI > -0.05 and NDVI < 0.25 (confuses bare soil with built surfaces); NDVI contrast = feature minus an 80 m outer buffer.  

**Table 7.** Cross-site summary of the workflow.  
*File:* `Table7_cross_site.csv`; sheet `Table7` of `tables.xlsx`; `tables.docx` page 7.  
Note: 2026 classes in the 5 x 5 km crop (Kittur: 2026 dry-season median; others: single scene; see Fig. 9). 1960s classes are panchromatic tone thresholds and are crude. At Hampi bare granite falls in the built/bare class.  
Note: Epoch metrics within 1.5 km of each fort centre (Fig. 10).  
