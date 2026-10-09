"""
ORNATE HAND CANNON  --  reconstructed from /app/hand-cannon.png
FreeCAD 1.1.0 Python script.

Builds a single PartDesign Body whose feature tree produces one solid:
  1. "Barrel"  : PartDesign::Revolution of the measured half-section
                 (muzzle bell, waist, ring, grooved collar, stepped tail,
                 conical mouth and Ø21 blind bore) about the X axis.
  2. "Handle"  : PartDesign::Pad of the flat grip bar (30 deg from vertical).
  3. "Cap"     : PartDesign::Pad of the pommel plate.

All dimensions are read/measured from the drawing (mm):
  overall length 162, muzzle Ø58/Ø62, bell stations x=4/9/18/30/49 with
  Ø62/Ø44/Ø36/Ø32, waist Ø32, ring Ø42 (x=98-107, w=9), groove Ø34 (x=107-117),
  ring Ø38 (x=117-125, w=8), tail Ø22 (x=125-140), tail Ø28 (x=140-162),
  mouth Ø50 -> Ø21 cone over 30 mm, blind bore Ø21, depth 88,
  handle: 30 deg, horizontal width 16, cap 22x12 (z-width 28), axis-to-cap
  bottom 82, cap right-edge overhang 3.36, handle z-width 22.
"""

import math

import FreeCAD as App
import Part
import Sketcher
from FreeCAD import Vector

OUT_FILE = "/app/answer.FCStd"

# ---------------------------------------------------------------- parameters
# barrel half-section, polyline points (x = axis from muzzle face, y = radius)
PROFILE = [
    (0.0, 29.0),   # muzzle face, rim Ø58
    (4.0, 31.0),   # bell crest Ø62
    (9.0, 29.0),   # bell station
    (18.0, 22.0),  # Ø44
    (30.0, 18.0),  # Ø36
    (49.0, 16.0),  # waist Ø32 start
    (98.0, 16.0),  # waist Ø32 end
    (98.0, 21.0),  # ring Ø42 (x = 98..107, width 9)
    (107.0, 21.0),
    (107.0, 17.0), # groove Ø34 (x = 107..117)
    (117.0, 17.0),
    (117.0, 19.0), # ring Ø38 (x = 117..125, width 8)
    (125.0, 19.0),
    (125.0, 11.0), # tail Ø22 (x = 125..140)
    (140.0, 11.0),
    (140.0, 14.0), # tail Ø28 (x = 140..162)
    (162.0, 14.0),
    (162.0, 0.0),  # breech end face
    (88.0, 0.0),   # along axis to bore bottom
    (88.0, 10.5),  # blind end of Ø21 bore (depth 88)
    (30.0, 10.5),  # Ø21 bore
    (0.0, 25.0),   # conical mouth, Ø50 at the face
]

# handle (grip bar): side-view parallelogram, edges at 30 deg from vertical.
# At cap-top level (y = -70) the edges sit at x = 142.64 and x = 158.64 so the
# horizontal width is 16 and the cap right edge (x=162) overhangs by 3.36.
TAN30 = math.tan(math.radians(30.0))
HANDLE_LEFT_X70 = 142.64
HANDLE_RIGHT_X70 = 158.64
HANDLE_TOP_Y = 5.0      # inside the barrel (invisible after fusion)
HANDLE_BOTTOM_Y = -75.0 # inside the cap (invisible after fusion)
HANDLE_Z = 22.0         # measured bar width (from the end view)

def _edge_x(x70, y):
    return x70 - (y + 70.0) * TAN30

HANDLE_PROFILE = [
    (_edge_x(HANDLE_LEFT_X70, HANDLE_TOP_Y), HANDLE_TOP_Y),
    (_edge_x(HANDLE_RIGHT_X70, HANDLE_TOP_Y), HANDLE_TOP_Y),
    (_edge_x(HANDLE_RIGHT_X70, HANDLE_BOTTOM_Y), HANDLE_BOTTOM_Y),
    (_edge_x(HANDLE_LEFT_X70, HANDLE_BOTTOM_Y), HANDLE_BOTTOM_Y),
]

# pommel cap: x = 140..162 (width 22), y = -82..-70 (height 12)
CAP_PROFILE = [
    (140.0, -82.0),
    (162.0, -82.0),
    (162.0, -70.0),
    (140.0, -70.0),
]
CAP_Z = 28.0            # measured cap width (from the end view)


def _wire_polygon(sketch, points):
    n = len(points)
    for i in range(n):
        x1, y1 = points[i]
        x2, y2 = points[(i + 1) % n]
        sketch.addGeometry(
            Part.LineSegment(Vector(x1, y1, 0.0), Vector(x2, y2, 0.0))
        )


def main():
    doc = App.newDocument("HandCannon")

    body = doc.addObject("PartDesign::Body", "Body")
    body.Label = "HandCannon"

    # ---- base feature: revolved barrel -------------------------------------
    sk = doc.addObject("Sketcher::SketchObject", "BarrelProfile")
    body.addObject(sk)
    sk.MapMode = "Deactivated"
    _wire_polygon(sk, PROFILE)
    doc.recompute()

    rev = doc.addObject("PartDesign::Revolution", "Barrel")
    body.addObject(rev)
    rev.Profile = sk
    x_axis = doc.getObject("X_Axis")
    if x_axis is not None:
        rev.ReferenceAxis = (x_axis, [""])
    else:  # fallback: use the global X axis directly
        rev.Axis = Vector(1.0, 0.0, 0.0)
        rev.Base = Vector(0.0, 0.0, 0.0)
    rev.Angle = 360.0
    doc.recompute()

    # ---- grip bar -----------------------------------------------------------
    sk_h = doc.addObject("Sketcher::SketchObject", "HandleProfile")
    body.addObject(sk_h)
    sk_h.MapMode = "Deactivated"
    _wire_polygon(sk_h, HANDLE_PROFILE)
    doc.recompute()

    pad_h = doc.addObject("PartDesign::Pad", "Handle")
    body.addObject(pad_h)
    pad_h.Profile = sk_h
    pad_h.Length = HANDLE_Z
    pad_h.SideType = "Symmetric"
    doc.recompute()

    # ---- pommel cap ---------------------------------------------------------
    sk_c = doc.addObject("Sketcher::SketchObject", "CapProfile")
    body.addObject(sk_c)
    sk_c.MapMode = "Deactivated"
    _wire_polygon(sk_c, CAP_PROFILE)
    doc.recompute()

    pad_c = doc.addObject("PartDesign::Pad", "Cap")
    body.addObject(pad_c)
    pad_c.Profile = sk_c
    pad_c.Length = CAP_Z
    pad_c.SideType = "Symmetric"
    doc.recompute()

    body.Tip = pad_c
    doc.recompute()

    shape = body.Shape
    print("solids:", len(shape.Solids))
    print("volume: %.2f mm^3" % shape.Volume)
    print("bbox:", shape.BoundBox)

    doc.saveAs(OUT_FILE)
    print("saved:", OUT_FILE)


main()
