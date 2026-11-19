# Project PROSAIL values versus literature

Three ryegrass defaults fall outside the literature ranges retrieved for grassland: Cm, hspot and, against the Lolium-dominated measurements, Cab. Wheat values that could be re-checked agree with their sources. Ranges and locations are in prosail_parameters_lolium_triticum.csv.

## Ryegrass reference (ryegrass-params.yaml)

| Parameter | Project | Literature | Verdict |
|---|---|---|---|
| N | 1.5 | 1.5–1.9 LUT ([Darvishzadeh 2008](https://doi.org/10.1016/j.rse.2007.12.003); [Si 2012](https://doi.org/10.1016/j.rse.2012.02.011)) | in range (lower bound) |
| Cab | 40 | measured 14.6–37.3, mean 29.3 on Lolium/Poa-dominated grassland (Si 2012 T1); 17.1–49.7 on Mediterranean grassland (Darvishzadeh 2008 T1); LUT 15–55 | **above the Lolium-dominated measured maximum**; within the LUT range |
| Car | 8 | no grass source; Cab/Car ≈ 5 in wheat ([Jiang 2018](https://doi.org/10.1186/s13007-018-0291-x)) | assumption, cross-species |
| Cbrown | 0 | no grass source; crop LUT fixed at 0 ([Berger 2020](https://doi.org/10.1016/j.jag.2020.102174)) | unverified for grass |
| Cw | 0.01 | 0.01–0.02 LUT; no measured ryegrass EWT | in range (lower bound) |
| Cm | 0.009 | ryegrass measured 0.0047–0.0067 ([Beechey-Gradwell 2019](https://doi.org/10.1093/jxb/erz494), controlled environment); LUT 0.0025–0.005 (Si 2012); LUT 0.005–0.01 (Darvishzadeh 2008) | **outside measured ryegrass and Si 2012 ranges**; inside the Darvishzadeh LUT only |
| LAI | 2.5 | measured 0.35–6.77 (Si 2012); 0.39–7.34 (Darvishzadeh 2008) | in range |
| ALA (lidfa) | 60 | LUT 40–70 / 20–70; no measured ryegrass ALA retrieved | in LUT range; unverified |
| hspot | 0.01 | grassland LUT 0.05–0.1 (both studies); crop LUT 0.01–0.5 | **below the grassland range** |
| psoil | 0.5 | grassland studies use a 0.5–1.5 brightness scale, a different parameterisation; crop LUT α_soil 0–1 | parameterisation mismatch; not comparable |

## Wheat Zadoks table (growth_stages.csv)

Leaf angle values match [Hosoi et al. 2009](https://doi.org/10.2480/agrmet.65.3.6): 53.9, 45.3, 44.3 and 56.1° by stage. The 49.9° used for unmapped stages is their four-date mean. N = 1.62 matches the PROSPECT-5b inversion mean of Jiang et al. (2018, Table 4). The car = cab/5 rule matches the Cab:Car ≈ 5 they report. Cw = 0.02 sits at the upper bound of the crop LUT range of Berger et al. (2020, 0.001–0.02). The Z55 LAI maximum of 8.27 exceeds that LUT's upper limit of 7, but the LUT is a training range, not a measured limit. Values taken from [Danner et al. 2019](https://doi.org/10.3390/rs11101150) (Cab 44.8, Cw, Cm 0.0051, Cbrown 0), Xing et al. 2021, O'Leary et al. 2015, AHDB and Wang et al. 2022 could not be re-read this session and remain unverified here. psoil is blank for every stage; no wheat-specific soil value was found.
