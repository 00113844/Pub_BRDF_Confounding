"""Methods schematic: the simulated scene (leaf, canopy, soil, sun and sensor geometry).

Writes docs/drafts/figures/scene_schematic.svg and, with Inkscape (headless), .pdf and .png.
Every symbol on the figure is a PROSAIL input or output used in the paper; the angle convention
is the project's (RAA = 0 deg is the hotspot: sensor on the sun's side, looking away from the sun).

    python docs/drafts/scripts/scene_schematic.py
"""

from __future__ import annotations

import math
import random
import shutil
import subprocess
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "figures"
AUTHOR = "Gustavo Togeiro de Alckmin"

W, H = 1000, 600
OX, OY, R = 345, 405, 250       # scene origin (target point) on screen, hemisphere radius (px)
ELEV = math.radians(24)         # elevation of the drawing's viewpoint
CE, SE = math.cos(ELEV), math.sin(ELEV)

INK, MUTED = "#1f1f1d", "#6b6a66"
SUN, SENSOR, LEAF, SOIL, SKY = "#d9541e", "#2a78d6", "#1b8f5f", "#8a6a4a", "#8fb8e8"
FONT = "Arial, Helvetica, sans-serif"

SZA, SAA = 40.0, 300.0          # sun zenith / azimuth (deg, clockwise from north)
VZA, VAA = 32.0, 75.0           # sensor zenith / azimuth of the sensor position seen from the target
RC, HC = 0.42, 0.24             # canopy slab radius and height (hemisphere units)


def proj(x: float, y: float, z: float, r: float = R) -> tuple[float, float]:
    """Oblique projection: x east (right), y north (into the page), z up."""
    return OX + r * x, OY - r * (z * CE + y * SE)


def direction(zen: float, az: float) -> tuple[float, float, float]:
    t, a = math.radians(zen), math.radians(az)
    return math.sin(t) * math.sin(a), math.sin(t) * math.cos(a), math.cos(t)


def path(points) -> str:
    return "M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in points)


def text(x, y, s, size=13, color=INK, anchor="start", weight="normal", style="normal") -> str:
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{FONT}" font-size="{size}" fill="{color}" '
            f'text-anchor="{anchor}" font-weight="{weight}" font-style="{style}">{s}</text>')


def line(points, color, width=1.2, dash=None, marker=None, marker_start=None) -> str:
    extra = f' stroke-dasharray="{dash}"' if dash else ""
    extra += f' marker-end="url(#{marker})"' if marker else ""
    extra += f' marker-start="url(#{marker_start})"' if marker_start else ""
    return f'<path d="{path(points)}" fill="none" stroke="{color}" stroke-width="{width}"{extra}/>'


def zenith_arc(zen, az, r, z0=0.0):
    a = math.radians(az)
    pts = []
    for i in range(41):
        t = math.radians(zen) * i / 40
        x, y = proj(math.sin(t) * math.sin(a), math.sin(t) * math.cos(a), math.cos(t), r)
        pts.append((x, y - R * z0 * CE))
    return pts


def azimuth_arc(a0, a1, r, z=0.0):
    pts = []
    for i in range(73):
        a = math.radians(a0 + (a1 - a0) * i / 72)
        x, y = proj(math.sin(a), math.cos(a), 0, r)
        pts.append((x, y - R * z * CE))
    return pts


def build() -> str:
    s: list[str] = []
    s.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">')
    s.append("<title>Simulated scene and PROSAIL parameters</title>")
    s.append(f'<metadata><rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" '
             f'xmlns:dc="http://purl.org/dc/elements/1.1/"><rdf:Description><dc:creator>{AUTHOR}'
             f'</dc:creator></rdf:Description></rdf:RDF></metadata>')
    defs = []
    for mid, col, size in (("arr", INK, 7), ("arrM", MUTED, 7), ("arrS", SUN, 7), ("arrV", SENSOR, 7),
                           ("arrK", SKY, 6)):
        defs.append(f'<marker id="{mid}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="{size}" '
                    f'markerHeight="{size}" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" '
                    f'fill="{col}"/></marker>')
    s.append("<defs>" + "".join(defs) + "</defs>")
    s.append(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')

    sd, vd = direction(SZA, SAA), direction(VZA, VAA)
    top_dy = R * HC * CE                       # screen height of the canopy slab

    # ---- ground (soil) disc and north arrow
    s.append(f'<path d="{path(azimuth_arc(0, 360, R))} Z" fill="#efe6da" stroke="{SOIL}" stroke-width="1.2"/>')
    s.append(line([proj(0, 1.0, 0), proj(0, 1.2, 0)], MUTED, 1.4, marker="arrM"))
    nx, ny = proj(0, 1.2, 0)
    s.append(text(nx + 9, ny + 8, "N", 12, MUTED, "start", "bold"))
    s.append(text(OX, OY + R * SE + 24,
                  "Soil background: brightness / moisture factor psoil (0 wet – 1 dry)", 12, SOIL, "middle"))

    # ---- relative azimuth arc on the ground (drawn before the canopy, which hides its middle)
    s.append(line(azimuth_arc(VAA, SAA - 360, R * 0.86), INK, 1.4, marker="arr", marker_start="arr"))
    a30 = math.radians(30)
    mx, my = proj(0.86 * math.sin(a30), 0.86 * math.cos(a30), 0)
    s.append(text(mx + 6, my + 16, "RAA", 13, INK, "start", style="italic"))

    # ---- azimuth projections on the ground
    gs = proj(math.sin(math.radians(SAA)), math.cos(math.radians(SAA)), 0)
    gv = proj(math.sin(math.radians(VAA)), math.cos(math.radians(VAA)), 0)
    s.append(line([proj(0, 0, 0), gs], SUN, 1.1, "5 3"))
    s.append(line([proj(0, 0, 0), gv], SENSOR, 1.1, "5 3"))
    s.append(line([proj(*sd, r=R * 0.98), gs], SUN, 0.8, "2 3"))
    s.append(line([proj(*vd, r=R * 0.95), gv], SENSOR, 0.8, "2 3"))
    s.append(text(gs[0] - 8, gs[1] + 4, "φs (sun azimuth)", 12, SUN, "end", style="italic"))
    s.append(text(gv[0] - 4, gv[1] + 20, "φv (view azimuth)", 12, SENSOR, "end", style="italic"))

    # ---- canopy: turbid-medium slab with leaves at several inclinations
    bottom = azimuth_arc(0, 360, R * RC)
    top = azimuth_arc(0, 360, R * RC, HC)
    left, right = proj(-RC, 0, 0), proj(RC, 0, 0)
    front = sorted([p for p in bottom if p[1] >= OY - 0.5], key=lambda p: p[0])
    body = [left] + front + [right, (right[0], right[1] - top_dy), (left[0], left[1] - top_dy)]
    s.append(f'<path d="{path(body)} Z" fill="#e3f2ea" stroke="{LEAF}" stroke-width="1.2" stroke-dasharray="4 3"/>')
    s.append(f'<path d="{path(top)} Z" fill="#d7eee1" stroke="{LEAF}" stroke-width="1.2" stroke-dasharray="4 3"/>')
    rng = random.Random(3)
    for _ in range(60):
        a = rng.random() * 2 * math.pi
        rr = math.sqrt(rng.random()) * RC * 0.9
        x0, y0 = proj(rr * math.sin(a), rr * math.cos(a), 0)
        y = y0 - rng.uniform(0.15, 0.95) * top_dy
        ang = rng.choice([-70, -55, -40, -25, 25, 40, 55, 70]) + rng.uniform(-8, 8)
        s.append(f'<ellipse cx="{x0:.1f}" cy="{y:.1f}" rx="9" ry="2.6" fill="{LEAF}" fill-opacity="0.85" '
                 f'transform="rotate({ang:.0f} {x0:.1f} {y:.1f})"/>')
    lx0, ly0 = 18, 40
    for i, t in enumerate(["Canopy (4SAIL)", "LAI (m² m⁻²)", "Leaf angles: ellipsoidal LIDF,",
                           "   mean leaf angle (ALA)", "Hotspot parameter hspot",
                           "   (leaf size / canopy height)"]):
        s.append(text(lx0, ly0 + i * 16, t, 13 if i == 0 else 12.5, LEAF, "start", "bold" if i == 0 else "normal"))

    # ---- zenith axis (from the canopy top)
    zx, zy = proj(0, 0, 1.14)
    s.append(line([proj(0, 0, HC), proj(0, 0, 1.12)], MUTED, 1.2, "5 4", marker="arrM"))
    s.append(text(zx, zy - 4, "Zenith", 12, MUTED, "middle"))

    # ---- diffuse sky light: short arrows from the upper hemisphere
    for az, zen in ((340, 48), (20, 48), (205, 30), (150, 34)):
        d = direction(zen, az)
        s.append(line([proj(*[c * 0.98 for c in d]), proj(*[c * 0.80 for c in d])], SKY, 1.8, "3 3", marker="arrK"))
    kx, ky = proj(*direction(48, 340), r=R * 0.98)
    s.append(text(kx, ky - 12, "Diffuse sky light", 11.5, "#4a7fbf", "middle"))

    # ---- sun ray, sun symbol, solar zenith arc
    target = proj(0, 0, HC + 0.02)
    sx, sy = proj(*sd, r=R * 1.06)
    s.append(line([proj(*sd, r=R * 0.98), target], SUN, 2.4, marker="arrS"))
    s.append(f'<circle cx="{sx:.1f}" cy="{sy:.1f}" r="17" fill="#f6b26b" stroke="{SUN}" stroke-width="2"/>')
    for k in range(8):
        a = math.radians(k * 45)
        s.append(f'<path d="M {sx + 21 * math.cos(a):.1f},{sy + 21 * math.sin(a):.1f} '
                 f'L {sx + 28 * math.cos(a):.1f},{sy + 28 * math.sin(a):.1f}" stroke="{SUN}" stroke-width="2"/>')
    s.append(text(sx, sy - 36, "Sun", 13, SUN, "middle", "bold"))
    arc = zenith_arc(SZA, SAA, R * 0.46, HC)
    s.append(line(arc, SUN, 1.4))
    ax_, ay_ = zenith_arc(SZA, SAA, R * 0.36, HC)[20]
    s.append(text(ax_ + 2, ay_ + 4, "θs", 14, SUN, "middle", style="italic"))

    # ---- sensor, view ray, view zenith arc
    vx, vy = proj(*vd, r=R * 1.05)
    s.append(line([target, proj(*vd, r=R * 0.95)], SENSOR, 2.4, marker="arrV"))
    s.append(f'<g transform="translate({vx:.1f},{vy:.1f}) rotate(-35)">'
             f'<rect x="-16" y="-10" width="32" height="20" rx="3" fill="#d5e5f8" stroke="{SENSOR}" stroke-width="2"/>'
             f'<rect x="-7" y="10" width="14" height="7" fill="{SENSOR}"/></g>')
    s.append(text(vx + 4, vy - 40, "Sensor", 13, SENSOR, "middle", "bold"))
    s.append(text(vx + 4, vy - 24, "handheld · UAV · Sentinel-2", 11, SENSOR, "middle"))
    arc = zenith_arc(VZA, VAA, R * 0.52, HC)
    s.append(line(arc, SENSOR, 1.4))
    ax_, ay_ = zenith_arc(VZA, VAA, R * 0.42, HC)[20]
    s.append(text(ax_ + 2, ay_ + 4, "θv", 14, SENSOR, "middle", style="italic"))

    # ---- hotspot direction (sensor on the sun's side): marker on the sun ray
    hx = target[0] + 0.72 * (proj(*sd, r=R * 0.98)[0] - target[0])
    hy = target[1] + 0.72 * (proj(*sd, r=R * 0.98)[1] - target[1])
    s.append(f'<circle cx="{hx:.1f}" cy="{hy:.1f}" r="6" fill="#ffffff" stroke="{INK}" stroke-width="1.4"/>')
    s.append(text(hx - 12, hy - 4, "Hotspot view:", 11.5, INK, "end"))
    s.append(text(hx - 12, hy + 11, "θv = θs, RAA = 0°", 11.5, INK, "end"))

    # ---- leaf inset (PROSPECT-5B)
    lx, ly = 690, 40
    s.append(f'<rect x="{lx}" y="{ly}" width="290" height="208" rx="8" fill="#f6faf7" stroke="{LEAF}" '
             f'stroke-width="1.2"/>')
    s.append(text(lx + 14, ly + 24, "Leaf (PROSPECT-5B)", 13, LEAF, "start", "bold"))
    cx0, cy0 = lx + 62, ly + 112
    s.append(f'<path d="M {cx0 - 42},{cy0} C {cx0 - 20},{cy0 - 58} {cx0 + 30},{cy0 - 58} {cx0 + 46},{cy0 - 4} '
             f'C {cx0 + 20},{cy0 + 40} {cx0 - 20},{cy0 + 40} {cx0 - 42},{cy0} Z" fill="{LEAF}" fill-opacity="0.85"/>')
    s.append(f'<path d="M {cx0 - 42},{cy0} C {cx0 - 5},{cy0 - 10} {cx0 + 20},{cy0 - 8} {cx0 + 46},{cy0 - 4}" '
             f'stroke="#e3f2ea" stroke-width="1.5" fill="none"/>')
    for i, t in enumerate(["N: mesophyll structure", "Cab: chlorophyll a+b (µg cm⁻²)", "Car: carotenoids (= Cab/5)",
                           "Cbrown: brown pigments", "Cw: equivalent water (cm)", "Cm: dry matter (g cm⁻²)"]):
        s.append(text(lx + 118, ly + 52 + i * 24, t, 12, INK))
    rx_, ry_ = proj(RC * 0.75, 0, 0)
    s.append(f'<path d="M {lx},{ly + 160} C {lx - 90},{ly + 230} {rx_ + 40:.1f},{ry_ - 130:.1f} '
             f'{rx_:.1f},{ry_ - top_dy * 0.6:.1f}" fill="none" stroke="{LEAF}" stroke-width="1" stroke-dasharray="3 3"/>')

    # ---- outputs box
    ox_, oy_ = 690, 270
    s.append(f'<rect x="{ox_}" y="{oy_}" width="290" height="150" rx="8" fill="#f4f7fc" stroke="{SENSOR}" '
             f'stroke-width="1.2"/>')
    s.append(text(ox_ + 14, oy_ + 24, "Simulated outputs (400–2500 nm)", 13, SENSOR, "start", "bold"))
    for i, t in enumerate(["rsot: bidirectional reflectance factor,", "   direct sun (primary)",
                           "resv: directional reflectance,", "   sun + sky (secondary)",
                           "→ NDVI, NDRE, GNDVI, EVI, SAVI, MTCI"]):
        s.append(text(ox_ + 14, oy_ + 48 + i * 19, t, 12, INK))

    # ---- traits box
    tx, ty = 690, 440
    s.append(f'<rect x="{tx}" y="{ty}" width="290" height="104" rx="8" fill="#fbf8f2" stroke="{MUTED}" '
             f'stroke-width="1.2"/>')
    s.append(text(tx + 14, ty + 24, "Traits derived from the inputs", 13, INK, "start", "bold"))
    for i, t in enumerate(["LAI", "Green-leaf biomass = LAI × Cm × 10⁴ (g m⁻²)", "CCC = LAI × Cab × 0.01 (g m⁻²)"]):
        s.append(text(tx + 14, ty + 46 + i * 19, t, 12, INK))

    s.append("</svg>")
    return "\n".join(s)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    svg = OUT / "scene_schematic.svg"
    svg.write_text(build(), encoding="utf-8")
    inkscape = shutil.which("inkscape") or r"C:\Program Files\Inkscape\bin\inkscape.com"
    for kind, extra in (("pdf", ["--export-text-to-path"]),
                        ("png", ["--export-dpi=300", "--export-background=#ffffff"])):
        subprocess.run([inkscape, str(svg), f"--export-type={kind}",
                        f"--export-filename={OUT / f'scene_schematic.{kind}'}", *extra], check=True)
    set_pdf_author(svg.with_suffix(".pdf"))
    print("wrote", svg.with_suffix(".pdf"), svg.with_suffix(".png"))


def set_pdf_author(pdf: Path) -> None:
    """Replace the exporter's metadata (Inkscape/cairo) with the author's name."""
    from pypdf import PdfReader, PdfWriter
    writer = PdfWriter(clone_from=PdfReader(pdf))
    writer.metadata = None
    writer.add_metadata({"/Author": AUTHOR, "/Creator": AUTHOR, "/Producer": AUTHOR,
                         "/Title": "Simulated scene and PROSAIL parameters"})
    with open(pdf, "wb") as fh:
        writer.write(fh)


if __name__ == "__main__":
    main()
