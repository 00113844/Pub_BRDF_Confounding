! 09 22 2011
! This program allows modeling reflectance data from canopy
! - modeling leaf optical properties with PROSPECT-5 (feret et al. 2008)
! - modeling leaf inclination distribution function with the subroutine campbell
! (Ellipsoidal distribution function caracterised by the average leaf
! inclination angle in degree), or dladgen (2 parameters LIDF)
! - modeling canopy reflectance with 4SAIL (Verhoef et al., 2007)

! This version has been implemented by Jean-Baptiste Feret
! Jean-Baptiste Feret takes the entire responsibility for this version
! All comments, changes or questions should be sent to:
! jbferet@stanford.edu

! References:
! 	Verhoef et al. (2007) Unified Optical-Thermal Four-Stream Radiative
! 	Transfer Theory for Homogeneous Vegetation Canopies, IEEE TRANSACTIONS
! 	ON GEOSCIENCE AND REMOTE SENSING, VOL. 45, NO. 6, JUNE 2007
! 	Feret et al. (2008), PROSPECT-4 and 5: Advances in the Leaf Optical
! 	Properties Model Separating Photosynthetic Pigments, REMOTE SENSING OF
! 	ENVIRONMENT
! The specific absorption coefficient corresponding to brown pigment is
! provided by Frederic Baret (EMMAH, INRA Avignon, baret@avignon.inra.fr)
! and used with his autorization.
! the model PRO4SAIL is based on a version provided by
!	Wout Verhoef
!	NLR
!	April/May 2003

! The original 2-parameter LIDF model is developed by and described in:
! 	W. Verhoef, 1998, "Theory of radiative transfer models applied in
!	optical remote sensing of vegetation canopies", Wageningen Agricultural
!	University,	The Netherlands, 310 pp. (Ph. D. thesis)
! the Ellipsoidal LIDF is taken from:
!   Campbell (1990), Derivtion of an angle density function for canopies
!   with ellipsoidal leaf angle distribution, Agricultural and Forest
!   Meteorology, 49 173-176

! ---------------------------------------------------------------------------
! Patched for the perennial-ryegrass BRDF project (see ../../PATCHES.md):
!  - all four 4SAIL reflectance factors (rsot, rdot, rsdt, rddt) are returned
!    alongside the sky-light weighted resv, instead of resv only;
!  - optional user soil spectrum (use_soil = 1), ported from the hsdar
!    package (main_PROSAIL.f90); otherwise psoil mixes the built-in
!    dry (Rsoil1) and wet (Rsoil2) soils as before;
!  - deallocation guarded with allocated(), as in hsdar.
! The physics (PRO4SAIL, PROSPECT-5B, LIDF, volscatt, spectral data) is
! unchanged from upstream.
! ---------------------------------------------------------------------------

subroutine run(N, Cab, Car, Cbrown, Cw, Cm, psoil, LAI, hspot, tts, tto, psi, &
               TypeLidf, LIDFa, LIDFb, use_soil, rsoil_in, &
               resv_out, rsot_out, rdot_out, rsdt_out, rddt_out)
	USE MOD_ANGLE				! defines pi & rad conversion
	USE MOD_staticvar			! static variables kept in memory for optimization
	USE MOD_flag_util			! flags for optimization
	USE MOD_output_PROSPECT		! output variables of PROSPECT
	USE MOD_SAIL				! variables of SAIL
	USE MOD_dataSpec_P5B
	IMPLICIT NONE

REAL*8, intent(in) :: N,Cab, Car,Cbrown,Cw,Cm, psoil, LAI, hspot, tts, tto, psi, LIDFa,LIDFb
INTEGER, intent(in) :: TypeLidf, use_soil
REAL*8, intent(in) :: rsoil_in(nw)
! resv : sky-light weighted directional reflectance (original PyProSAIL output)
! rsot : bi-directional reflectance factor (direct sun only, includes hotspot)
! rdot : hemispherical-directional reflectance factor (diffuse sky only)
! rsdt : directional-hemispherical reflectance factor (direct sun)
! rddt : bi-hemispherical reflectance factor
REAL*8, intent(out) :: resv_out(nw), rsot_out(nw), rdot_out(nw), rsdt_out(nw), rddt_out(nw)

REAL*8 :: skyl
REAL*8,ALLOCATABLE,SAVE :: resh(:),resv(:)
REAL*8,ALLOCATABLE,SAVE :: rsoil0(:),PARdiro(:),PARdifo(:)

! ANGLE CONVERSION
pi=ATAN(1.)*4.
rd=pi/180.

! PROSPECT output
ALLOCATE (LRT(nw,2),rho(nw),tau(nw))
! SAIL
ALLOCATE (sb(nw),sf(nw),vb(nw),vf(nw),w(nw))
ALLOCATE (m(nw),m2(nw),att(nw),sigb(nw),rinf(nw))
ALLOCATE (PARdiro(nw),PARdifo(nw))
ALLOCATE(tsd(nw),tdd(nw),tdo(nw),rsd(nw),rdd(nw),rso(nw),rdo(nw))
ALLOCATE(rddt(nw),rsdt(nw),rdot(nw),rsodt(nw),rsost(nw),rsot(nw),rsos(nw),rsod(nw))
ALLOCATE(lidf(13))
! resh : hemispherical reflectance
! resv : directional reflectance
ALLOCATE (resh(nw),resv(nw))
ALLOCATE (rsoil_old(nw))

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!	Soil Reflectance Properties	!!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
	! rsoil1 = dry soil
	! rsoil2 = wet soil
	ALLOCATE (rsoil0(nw))
	IF (use_soil.EQ.1) THEN
		rsoil0=rsoil_in
	ELSE
		! psoil=0: wet soil / psoil=1: dry soil
		rsoil0=psoil*Rsoil1+(1-psoil)*Rsoil2
	ENDIF

	init_completed=.false.	! only at first call of PRO4SAIL

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!        CALL PRO4SAIL         !!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
	CALL PRO4SAIL(N,Cab,Car,Cbrown,Cw,Cm,LIDFa,LIDFb,TypeLIDF,LAI,hspot,tts,tto,psi,rsoil0)

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!	direct / diffuse light	!!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
	! the direct and diffuse light are taken into account as proposed by:
	! Francois et al. (2002) Conversion of 400-1100 nm vegetation albedo
	! measurements into total shortwave broadband albedo using a canopy
	! radiative transfer model, Agronomie
	skyl	=	0.847- 1.61*sin((90-tts)*rd)+ 1.04*sin((90-tts)*rd)*sin((90-tts)*rd) ! % diffuse radiation
	! Es = direct
	! Ed = diffuse
	! PAR direct
	PARdiro	=	(1-skyl)*Es
	! PAR diffus
	PARdifo	=	(skyl)*Ed
	! resv : directional reflectance
	resv	= (rdot*PARdifo+rsot*PARdiro)/(PARdiro+PARdifo)

	resv_out = resv
	rsot_out = rsot
	rdot_out = rdot
	rsdt_out = rsdt
	rddt_out = rddt

if (allocated(LRT)) deallocate(LRT)
if (allocated(rho)) deallocate(rho)
if (allocated(tau)) deallocate(tau)
if (allocated(sb)) deallocate(sb)
if (allocated(sf)) deallocate(sf)
if (allocated(vb)) deallocate(vb)
if (allocated(vf)) deallocate(vf)
if (allocated(w)) deallocate(w)
if (allocated(m)) deallocate(m)
if (allocated(m2)) deallocate(m2)
if (allocated(att)) deallocate(att)
if (allocated(sigb)) deallocate(sigb)
if (allocated(rinf)) deallocate(rinf)
if (allocated(PARdiro)) deallocate(PARdiro)
if (allocated(PARdifo)) deallocate(PARdifo)
if (allocated(tsd)) deallocate(tsd)
if (allocated(tdd)) deallocate(tdd)
if (allocated(tdo)) deallocate(tdo)
if (allocated(rsd)) deallocate(rsd)
if (allocated(rdd)) deallocate(rdd)
if (allocated(rso)) deallocate(rso)
if (allocated(rdo)) deallocate(rdo)
if (allocated(rddt)) deallocate(rddt)
if (allocated(rsdt)) deallocate(rsdt)
if (allocated(rdot)) deallocate(rdot)
if (allocated(rsodt)) deallocate(rsodt)
if (allocated(rsost)) deallocate(rsost)
if (allocated(rsot)) deallocate(rsot)
if (allocated(rsos)) deallocate(rsos)
if (allocated(rsod)) deallocate(rsod)
if (allocated(lidf)) deallocate(lidf)
if (allocated(resh)) deallocate(resh)
if (allocated(resv)) deallocate(resv)
if (allocated(rsoil_old)) deallocate(rsoil_old)
if (allocated(rsoil0)) deallocate(rsoil0)

END
