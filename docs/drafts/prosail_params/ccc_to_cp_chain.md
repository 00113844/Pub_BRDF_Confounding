# Canopy chlorophyll to crude protein: equation chain

Canopy chlorophyll content (CCC) can be turned into crude protein (CP, % of dry matter) only through three links: CCC to canopy nitrogen, nitrogen to protein, and canopy nitrogen to a herbage-mass basis. Only the second link is well constrained, and it is generic. The first link has no retrieved canopy-scale equation for *Lolium perenne* and is unstable for wheat after flowering. The third link needs an independent estimate of herbage dry mass, which CCC does not supply.

## Equation chain

**Step 1. Canopy chlorophyll.** CCC = Cab × LAI. With Cab in µg cm⁻² leaf, CCC [g m⁻²] = Cab × LAI × 10⁻². Both grassland PROSAIL studies report CCC this way ([Darvishzadeh et al. 2008](https://doi.org/10.1016/j.rse.2007.12.003), Table 1; [Si et al. 2012](https://doi.org/10.1016/j.rse.2012.02.011), Table 1). This step is definitional and generic.

**Step 2a. Chlorophyll to nitrogen (empirical route).** N_area = f(CCC). This link is species- and stage-specific, and no ryegrass canopy-scale f was retrieved. The closest ryegrass evidence is at leaf scale. [Gáborčík (2003)](https://doi.org/10.1023/b:phot.0000011963.43628.15) found close within-cut SPAD–leaf N relationships across *Festuca*/*Lolium* cultivars (r² = 0.491–0.938 by cut, p. 285). The regression slopes differed between cuts, so the relation depends on sward development stage (p. 286). Two cautions apply. The pooled regression printed on p. 286 (y = −0.90105 + 0.868x) does not reproduce the Table 1 means in either axis order, so it should not be used. SPAD is not converted to Cab in that paper. For wheat, the leaf-level evidence is the flag-leaf study of [Evans (1983)](https://doi.org/10.1104/pp.72.2.297), which reports chlorophyll approximately proportional to leaf N. Only its abstract was available, so no coefficient is taken from it. The review by [Berger et al. (2020)](https://doi.org/10.1016/j.rse.2020.111758) sets the limits of this route (HAL postprint p. 5). The CCC–N_area correlation in winter wheat and maize decreases once flowers, fruits or senescence appear, as N is reallocated to reproductive organs. Across LOPEX species, N and chlorophyll correlated only weakly (R² = 0.14). The same review notes that only a small part of plant N is bound in chlorophyll, and that the N–chlorophyll relationship is species-specific. The canopy-scale chlorophyll–nitrogen relations of [Clevers & Kooistra (2012)](https://doi.org/10.1109/jstars.2011.2176468) and [Clevers & Gitelson (2013)](https://doi.org/10.1016/j.jag.2012.10.008) could not be read: both full texts were behind access controls. Their coefficients are therefore left blank here.

**Step 2b. Protein route (physically based alternative).** PROSPECT-PRO splits LMA into protein (Cp) and carbon-based constituents (CBC): LMA = Cp + CBC ([Féret et al. 2021](https://doi.org/10.1016/j.rse.2020.112173), Eq. 5 and abstract). [Berger et al. (2020)](https://doi.org/10.1016/j.jag.2020.102174) (Eq. 1, p. 14) derive canopy N directly from simulated protein:

N_area [g m⁻²] = LAI × Cp [g cm⁻²] × 10⁴ / 4.43

That study fitted the route on winter wheat and maize. It avoids Step 2a entirely but requires PROSPECT-PRO rather than PROSPECT-5B.

**Step 3. Nitrogen to protein.** Feed analysis defines crude protein as CP = N × 6.25. The factor assumes proteins contain 16% N ([Mariotti et al. 2008](https://doi.org/10.1080/10408390701279749), postprint p. 4). True leaf protein is lower. Mariotti et al. give 4.4 for vegetables, mushrooms and leaf proteins (Table 5). Féret et al. (2021, p. 33) report 4.43 ± 0.40 (range 3.28–5.16) after [Yeoh & Wee (1994)](https://doi.org/10.1016/0308-8146%2894%2990167-8), who analysed 90 species; the primary paper was not read. The choice matters. Pasture-quality benchmarks are N × 6.25, whereas PROSPECT-PRO Cp is calibrated with 4.43. Converting PROSPECT-PRO protein to feed-convention CP therefore needs a factor of 6.25/4.43 = 1.411 [CALC]:

CP_feed (% DM, leaf basis) = 100 × 1.411 × Cp / (Cp + CBC)

Both factors are generic, not species-specific. No grass-specific factor was found in the sources retrieved.

**Step 4. Herbage-mass basis.** CP (% DM) = 100 × 6.25 × N_area / W, where W is herbage dry mass in g m⁻². Three bases are available, and they answer different questions.

1. Leaf-blade basis from PROSAIL itself: W_leaf = LAI × Cm × 10⁴ g m⁻². This is internally consistent with the simulation but excludes sheath and stem.
2. Critical-N dilution for temperate grasses: %Nc = 4.8 W^−0.32 (W in t ha⁻¹). The curve is from Lemaire & Gastal (1997), as quoted and applied by [Reyes et al. (2015)](https://doi.org/10.1007/s13593-015-0321-2) (pp. 3, 5); the 1997 chapter itself was not read. It is generic for C3 forage grasses, not ryegrass-specific, and describes N-non-limited swards.
3. Wheat, South Australia: %Nc = 6.75 W^−0.66 (Fig. 4A). Stage means of critical N are 4.7, 4.4, 2.9, 2.1 and 1.8% for Z30–34, 35–39, 40–49, 50–59 and 60–69 ([Hoogmoed & Sadras 2018](https://doi.org/10.3389/fpls.2018.00406), Table 1). These are equivalent to 29.4, 27.5, 18.1, 13.1 and 11.2% CP at ×6.25 [CALC]. [Lemaire & Sinclair (2019)](https://doi.org/10.1007/s13593-019-0570-6) give 39 kg N ha⁻¹ per unit LAI for dense wheat under non-limiting N (Table 1). That figure links N_area to LAI without using chlorophyll.

## Worked check with the project ryegrass reference

The project reference is Cab = 40 µg cm⁻², LAI = 2.5 and Cm = 0.009 g cm⁻². These give CCC = 1.0 g m⁻² and W_leaf = 225 g m⁻². Using the measured ryegrass leaf N of 27.3 g kg⁻¹ (cv. Mustang mean; Gáborčík 2003, Table 1) gives N_area = 6.14 g m⁻². The resulting CP is 17.1% DM [CALC]. In this calculation CP comes only from the assumed leaf N concentration; CCC does not enter it. CP becomes a function of CCC only once a ryegrass CCC–N_area slope is supplied (Step 2a), and no such slope has been retrieved. The simulation's CP should therefore be framed in one of two ways: as an N_area retrieval with a stated generic conversion, or as a sensitivity analysis over a documented range of Chl:N ratios.

## Species-specific versus generic links

| Link | Ryegrass | Wheat | Basis |
|---|---|---|---|
| CCC = Cab × LAI | generic | generic | definition |
| CCC → N_area | not found at canopy scale; leaf-scale SPAD–N only (Gáborčík 2003) | stage-dependent; weakens after flowering (Berger et al. 2020 review) | empirical |
| Cp → N_area (factor 4.43) | generic | generic; fitted on wheat and maize (Berger et al. 2020 JAG) | PROSPECT-PRO |
| N → CP (6.25) | generic feed convention | generic feed convention | Mariotti et al. 2008 |
| Dilution curve | generic C3 grass (4.8, 0.32) | Australian wheat (6.75, 0.66) | allometric |

## Open gaps

Four gaps remain. First, no canopy-scale CCC–N_area or CCC–CP regression for *L. perenne* was obtained. Second, Australian ryegrass CP by regrowth stage exists (Turner et al. 2006, doi:10.1111/j.1365-2494.2006.00524.x; Fulkerson et al. 2007, doi:10.1016/j.livsci.2006.09.029). Only abstracts were reachable, so no values were taken from either paper. Third, the leaf-to-herbage mass ratio needed to move from a leaf-blade to a whole-herbage basis was not sourced. Fourth, the Clevers grass relations are blank, as noted under Step 2a.
