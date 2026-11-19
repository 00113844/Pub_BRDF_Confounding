# Sources for growth_stages.csv (wheat, PROSPECT-5B + 4SAIL)

Compiled 2026-11-06. Every DOI below was resolved through the Crossref API (`api.crossref.org/works/<doi>`), and the title, journal, volume and pages matched. Values were read from the full text (or the abstract, where stated) that was opened during compilation.

Flags used in the CSV `notes` column:
- **[CALC]**: the value was derived by calculation from sourced numbers. The formula is given in the notes.
- **[CROP-LEVEL]**: a season-wide or crop-wide value, not specific to the stage.
- **[STAGE-MAPPED]**: the source names the stage in words (e.g. "late jointing", "tillering") or by date, not by Zadoks code. The Zadoks assignment is my mapping.
- **[BRACKETED]** / **[DATE-MAPPED]**: taken from adjacent stages, or matched by calendar date.

---

## Stage codes

**Zadoks1974.** Zadoks, J.C., Chang, T.T., Konzak, C.F. (1974). A decimal code for the growth stages of cereals. *Weed Research* 14(6): 415-421. doi:10.1111/j.1365-3180.1974.tb01084.x
- Used for: the stage codes. Only the metadata was verified via Crossref; the paper itself is paywalled and was not opened.
- Stage names follow the task brief and agree with the Zadoks-based list in AHDB2018 (p. 36-38: "GS13 Three leaves unfolded…", "GS21 Main shoot and one tiller", "GS30 Ear at 1cm (pseudostem erect)", "GS32 Second node detectable", "GS39 Flag leaf blade all visible", "GS55 Half of ear emerged…", "GS65 Flowering halfway", "GS75 Medium milk", "GS85 Soft dough", "GS92 Grain hard (not dented by thumbnail)").

## LAI / green area

**Xing2021.** Xing, N., Huang, W., Ye, H., Dong, Y., Kong, W., Ren, Y., Xie, Q. (2021). Remote sensing retrieval of winter wheat leaf area index and canopy chlorophyll density at different growth stages. *Big Earth Data* 6(4): 580-602. doi:10.1080/20964471.2021.1918909 (open-access copy: https://opus.lib.uts.edu.au/bitstream/10453/150032/2/)
- Site: Shunyi, Beijing, China, 2016. Several cultivars; 24 samples per stage. LAI measured with an LAI-2200. Leaf chlorophyll was extracted in 80% acetone, read on a spectrophotometer, and converted to an area basis.
- From **Table 2** (LCD in µg/cm², LAI in m²/m²; min / max / mean / SD):
  - Early jointing (7-8 Apr): LCD 42.952 / 62.091 / 53.421 / 6.028; LAI 0.982 / 3.093 / 2.025 / 0.499 → used at **Z30**
  - Late jointing (20-21 Apr): LCD 36.972 / 60.415 / 49.026 / 5.532; LAI 2.248 / 5.627 / 3.710 / 1.067 → used at **Z32**
  - Head emergence (3-5 May): LCD 49.088 / 82.885 / 60.055 / 7.972; LAI 3.354 / 8.270 / 5.791 / 1.327 → used at **Z55**
  - Filling (18-19 May): LCD 67.800 / 101.230 / 82.662 / 10.790; LAI 3.899 / 7.751 / 5.426 / 1.121 → **not used**, because the stage is ambiguous (see Z65 notes)
  - Milk development (6-8 Jun): LCD 14.080 / 66.974 / 42.354 / 14.542; LAI 2.678 / 6.329 / 4.618 / 0.879 → used at **Z75**
- Caveat: the LAI-2200 measures effective plant area (stems and ears included), and this is an irrigated, high-input North China Plain system.

**OLeary2015 (AGFACE).** O'Leary, G.J., Christy, B., Nuttall, J., Huth, N., Cammarano, D., Stöckle, C., Basso, B., Shcherbak, I., Fitzgerald, G., Luo, Q., Farre-Codina, I., Palta, J., Asseng, S. (2015). Response of wheat growth, grain yield and water use to elevated CO2 under a Free-Air CO2 Enrichment (FACE) experiment and modelling in a semi-arid environment. *Global Change Biology* 21(7): 2670-2686. doi:10.1111/gcb.12830
- Site: Horsham, Victoria, Australia, 2007-2009. cv. Yitpi. Leaf area measured with a planimeter on destructive samples at DC31 / DC65 / DC90.
- **Table 3**, LAI at DC65 under ambient CO2: normal sowing 1.7 (rain-fed) and 2.1 (irrigated); late sowing 0.6 (rain-fed) and 0.8 (irrigated). **Table 2**: pooled LAI65 at ambient CO2 is 1.3, and PAI65 is 2.0. Used for **Z65** lai_min = 0.6 and lai_typ = 1.7.
- Methods text: "Mean sowing plant density measured by plant counts about 3 weeks after the emergence was 120 plants m−2 and ranged from 60 to 175 plants m−2." This is given in the notes only.

**AHDB2018.** AHDB (2018). *Wheat growth guide*. Agriculture and Horticulture Development Board, UK. PDF copy used: https://farmpep.net/sites/default/files/2021-07/Wheat%20growth%20guide.pdf. The same benchmarks appear on the AHDB knowledge-library pages: https://ahdb.org.uk/knowledge-library/management-of-canopy-expansion-and-senescence-in-winter-wheat and https://ahdb.org.uk/knowledge-library/how-to-measure-growth-area-index-gai-in-cereals
- These are benchmarks for a UK crop yielding 11 t/ha. GAI is the "total area of all green tissues, one side only", not leaf-blade LAI.
- Values used:
  - Reference-photo GAI: 0.5 at GS24 and 0.9 at GS26 → bracket for **Z25**
  - GAI at GS30 = 1.6 (photo 1.4), and 941 shoots/m² → **Z30** notes
  - GAI at GS31 = 2.0, and 902 shoots/m² → **Z32** notes
  - GAI at GS39 = 6.2 → **Z39** lai_max
  - GAI at GS59 = 6.4 (maximum 6.9 in late May) → **Z55** notes
  - GAI at GS61 = 6.3 → **Z65** lai_max
  - GAI at GS71 = 5.7 → **Z75** notes
  - GAI at GS87 = 1.3, "All greenness will be lost in the next few days" → **Z85** notes
  - Figure 18 monthly GAI, August = 0.1, with a harvest-ripe benchmark date of 9 Aug → **Z92** lai_typ (DATE-MAPPED)
- Plant population: "70% of seeds sown established; 260 plants/m2". The minimum target is "about 150 plants/m2 in the thinnest areas". Given in the notes only.
- Heights:
  - Height to top ligule: 9 cm at GS31 and 34 cm at GS39
  - Height to ear collar: 53 cm at GS59, and 69 cm "final" at GS61 ("benchmark final height is 69cm to the base of the ear"; without PGRs crops "can be as much as 20cm taller")
  - These heights were used for hspot (see below).

## Leaf angle (Campbell ellipsoidal, lidfa = mean leaf inclination from horizontal)

**Hosoi2009.** Hosoi, F., Nakai, Y., Omasa, K. (2009). Estimating the leaf inclination angle distribution of the wheat canopy using a portable scanning lidar. *Journal of Agricultural Meteorology* 65(3): 297-302. doi:10.2480/agrmet.65.3.6
- Material: cv. Norin 61, Japan. The angle is that of the leaf normal from zenith, which equals the leaf inclination from horizontal and therefore matches the PROSAIL ALA convention. The lidar was validated against clinometer readings.
- Reported mean ± SD (Results text and Fig. 3):
  - 6 Apr "tillering": 53.9 ± 19.6° → **Z21**, **Z25**
  - 26 Apr "stem elongation": 45.3 ± 22.2° → **Z30**, **Z32**
  - 16 May "flowering": 44.3 ± 21.7° → **Z65**
  - 5 Jun "ripening" (20 days after the flowering date): 56.1 ± 19.5° → **Z75**
- [CALC][CROP-LEVEL] The mean of these four values, 49.9°, fills Z13, Z39, Z55, Z85 and Z92.

**Danner2019.** Danner, M., Berger, K., Wocher, M., Mauser, W., Hank, T. (2019). Fitted PROSAIL parameterization of leaf inclinations, water content and brown pigment content for winter wheat and maize canopies. *Remote Sensing* 11(10): 1150. doi:10.3390/rs11101150
- Site: Munich-North Isar, Germany. Winter wheat in 2014, 2015, 2017 and 2018. ALIA measured with a Suunto clinometer (±8°). LAI from an LAI-2200C. Cab from a SPAD-502 with an instrument-specific calibration against Lichtenthaler in vitro extraction; the calibration equation is not given in the paper. EWT and Cm measured gravimetrically.
- **Table 3**, winter wheat by year (range, mean):

  | Variable | 2014 | 2015 | 2017 | 2018 |
  |---|---|---|---|---|
  | LAI | 0.08-6.27 | 0.33-6.20 | 0.76-6.20 | 0.01-5.98 |
  | ALIA (°) | 25-75, mean 52 | 35-77, mean 60 | 45-78, mean 68 | 45-76, mean 64 |
  | Ccab (µg/cm²) | 13.4-49.1, mean 42.7 | 14.3-53.3, mean 43.2 | 18.2-59.5, mean 50.0 | 11.6-53.2, mean 43.2 |
  | Cbrown | 0-0.98 | 0-0.90 | 0-0.80 | 0-1.0 |
  | EWT (cm) | 0.012-0.035, mean 0.027 | 0.008-0.034, mean 0.026 | 0.003-0.020, mean 0.015 | 0.001-0.019, mean 0.013 |
  | Cm (g/cm²) | 0.0047-0.0075, mean 0.0063 | 0.0036-0.0061, mean 0.0046 | 0.0031-0.0059, mean 0.0047 | 0.0043-0.0066, mean 0.0049 |

- Text: "N parameter, as derived from Cm, ranges between 1.4 and 4.4 for wheat … average of 2.2". "In situ estimations of Cbrown were 0.0 during the vegetative stages of winter wheat. Canopies showed no senescent spots on leaves until beginning of ripening." "Young wheat leaves hold highest water contents but then continuously desiccate … When approaching late senescence, leaf water drops <0.01 cm." ALIA: "After high inclinations at the beginning of the growing period, leaves tend to bend down … which again results in increasing angles for senescent stages."
- Values used:
  - **cab [CROP-LEVEL][CALC]** = 44.8, the mean of the four seasonal means. Used at Z13, Z21, Z25, Z39 and Z65.
  - **cw [CROP-LEVEL][CALC]** = 0.020 cm, the mean of 0.027, 0.026, 0.015 and 0.013. Used from Z13 to Z75.
  - **cm [CROP-LEVEL][CALC]** = 0.0051 g/cm², the mean of 0.0063, 0.0046, 0.0047 and 0.0049. Used at all stages.
  - **cbrown = 0** from Z13 to Z75, from the in situ statement above.
- The per-date (stage-specific) in situ table is in the Supplement, Table S1. I could not download it because automated access to the MDPI supplement link was blocked. **It is the single best source for filling the remaining blanks, so it is worth retrieving manually.**

## Leaf biochemistry and structure (N, Car)

**Jiang2018.** Jiang, J., Comar, A., Burger, P., Bancal, P., Weiss, M., Baret, F. (2018). Estimation of leaf traits from reflectance measurements: comparison between methods based on vegetation indices and several versions of the PROSPECT model. *Plant Methods* 14: 23. doi:10.1186/s13007-018-0291-x
- Material: six wheat cultivars, Toulouse, France, 2012. Leaves were sampled at "two nodes" (April, Z32) and during grain filling (June). Pigments were extracted in acetone.
- **N = 1.62**: the mean retrieved N for PROSPECT-5 with brown pigment ("P5b"), from Table 4 (P5 gives 1.64). Applied at all stages as [CROP-LEVEL].
- **Car**: Results text, "The strongest correlation was observed between chlorophyll and carotenoid pigments (r2 = 0.91 with a ratio of Cab/Cc ≈ 5, when the offset is neglected)", plus "a lower offset for the carotenoid content (≈1 µg/cm2)". I therefore set **car = cab/5 [CALC]** in every row that has a cab value.

## Hotspot

**Wang2022.** Wang, Y., Qiao, L., Yang, C., Li, X., Zhao, J., Wu, B., Zheng, X., Li, P., Zheng, J. (2022). Identification of genetic loci for flag-leaf-related traits in wheat (Triticum aestivum L.) and their effects on grain yield. *Frontiers in Plant Science* 13: 990287. doi:10.3389/fpls.2022.990287
- Flag-leaf width was measured at the widest point. Table 2 gives parental BLUPs of 1.90 cm (Jinchun 7) and 2.05 cm (Jinmai 919); the DH population ranged from 1.06 to 2.83 cm.
- **hspot [CALC]** = flag-leaf width / canopy height, using width = mean of the parental BLUPs = 1.98 cm and AHDB2018 heights:
  - Z39: 1.98 / 34 = 0.058
  - Z55: 1.98 / 53 = 0.037 (GS59 height used)
  - Z65, Z75, Z85, Z92: 1.98 / 69 = 0.029
- Caveats:
  - The width is from Chinese genotypes and the heights from a UK benchmark crop with PGRs, so they come from different sources.
  - The AHDB heights exclude the ear, so the true canopy-top height is larger and hspot is slightly overestimated.
  - With the full DH width range, Z65 hspot would span 0.015 to 0.041.
  - Z13 to Z32 are blank because no lower-leaf width source was found.

## Plant population (agronomic metadata, not a PROSAIL input)

**GRDC2015.** GRDC (2015). *GrowNotes: Wheat, Western Region* (August 2015), Section 9.2 Plant establishment, 9.2.2 Seeding rate. Grains Research and Development Corporation. https://grdc.com.au/__data/assets/pdf_file/0021/240717/GRDC-GrowNotes-Wheat-Western.pdf
- "For each tonne of grain per hectare the rule of thumb target is 40-50 plants/m2 and about 100 heads/m2." The worked example uses a "target plant density is 100 plants/m2" for a yield potential of about 2 t/ha. Figure 8, citing Anderson and Garlinge (2000), plots optimum populations for WA trials between about 28 and 195 plants/m².
- Used: **plant_pop_per_m2 = 100** in every row. Establishment is set once, so the value is constant across stages.

**Anderson2004.** Anderson, W.K., Sharma, D.L., Shackley, B.J., D'Antuono, M.F. (2004). Rainfall, sowing time, soil type, and cultivar influence optimum plant population for wheat in Western Australia. *Australian Journal of Agricultural Research* 55(9): 921-930. doi:10.1071/AR03248
- Abstract: "The optimum plant population varied from 35 to 175 plants/m2 … the optimum plant population increased at about 40 plants/m2 for each tonne of grain yield up to about 3.0 t/ha." This is the range quoted in the notes. It is based on 32 experiments in the WA rain-fed zone, 1996-2001.

Tiller and shoot numbers given in the notes come from AHDB2018: 941 shoots/m² at GS30, 902 at GS31, 655 fertile at GS39, 495 at GS59, and 460 at GS61 and harvest.

## Consulted but no values used
- Siddique, K.H.M., Belford, R.K., Perry, M.W., Tennant, D. (1989). *Aust. J. Agric. Res.* 40(3): 473-487. doi:10.1071/AR9890473. This is a Merredin, WA study of green area index. Only the abstract was available; it has no numeric GAI values, and the full text is paywalled. **Recommended next source for WA-specific stage-wise GAI.**
- Li, H. et al. (2018). Retrieval of winter wheat LAI from Chinese GF-1 data using the PROSAIL model. *Sensors* 18(4): 1120. doi:10.3390/s18041120. It provides a SPAD-to-Cab calibration for wheat, Cab = 5.6351·exp(SPAD·0.0287 + 0.8095), R² = 0.97 with n = 72. Its per-stage tables could not be extracted.
- Zhang, C. et al. (2024). *Agriculture* 14(10): 1685. doi:10.3390/agriculture14101685. Vertical LCC by stage is shown in figures only, so it was not used.

## Blank cells and why
| Row | Blank columns | Reason |
|---|---|---|
| Z13 | lai_min/typ/max, hspot, psoil | No sourced LAI at 3-leaf stage; no seedling leaf width or height |
| Z21 | lai_min/typ/max, hspot, psoil | No sourced LAI at Z21; no leaf width or height |
| Z25 | lai_typ, hspot, psoil | Only bracketing values from GS24/GS26 are available |
| Z30, Z32 | hspot, psoil | No width for the leaves present at this stage |
| Z39 | lai_min, lai_typ, psoil | Only the AHDB high-yield benchmark is available |
| Z85 | lai_min/typ/max, cab, car, cw, cbrown, psoil | No stage-specific values; Danner2019 Table S1 (supplement) not accessible |
| Z92 | lai_min, lai_max, cab, car, cw, cbrown, psoil | Same as Z85; green LAI is effectively 0 |
| all | psoil | Left blank as instructed |

## Known limitations
1. **The LAI data mixes measurement types.** AHDB GAI, Xing's LAI-2200 effective PAI-like values, and AGFACE planimeter green-leaf LAI are not strictly comparable. Only AGFACE gives green leaf-blade LAI.
2. **lai_min is dryland/Australian only at Z65.** At the other stages, min and max come from a single irrigated Chinese dataset or a UK benchmark. Western Australian crops will usually sit near or below the minimum (see AGFACE Z65 values of 0.6 to 2.1).
3. **cw, cm, N and car are crop-level or calculated, not stage-specific.**
4. **Leaf-angle values come from one cultivar (Hosoi2009, lidar).** Danner2019 clinometer means were systematically higher (52 to 68°).
