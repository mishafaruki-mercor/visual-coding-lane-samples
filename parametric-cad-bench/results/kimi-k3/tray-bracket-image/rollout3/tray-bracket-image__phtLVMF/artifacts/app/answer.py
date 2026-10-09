# -*- coding: utf-8 -*-
"""
Perforated Tray Mounting Bracket - FreeCAD 1.1.0 script.
Rebuilt from the engineering drawing (perforated-tray-bracket.png).

Coordinate system used in the drawing (mm):
  X : 0 .. 160  (left -> right, along the long walls)
  Y : 0 .. 112  (back -> front, tall wall at Y=0)
  Z : 0 .. 43   (bottom -> top)

Part summary (read off the drawing):
  - Base plate 160 x 112 x 3 (floor top at Z=3)
  - Front wall (Y 109-112) H=25, with 11 slots 5x14 (Z 8-22), pitch 13.8, first centre X=11
  - Back wall (Y 0-3) H=25, same 11 slots; two corner tabs (22 wide, Z 25-43)
    with horizontal slots 14x5 (centre Z=34); ledge 116 long (X 22-138),
    protrudes 9 from the wall face (Y 3-12), Z 23-27
  - Right side wall (X 157-160, Y 3-109) H=8
  - Two corner pads on the front wall (16x18, Z 24-27), each 2x holes 3.6
  - Centre boss on the tray floor: rib (house-shaped outline, 8 tall) carrying
    two rectangular pads (35x18 and 33x18, 11 tall), each with 2 holes 4.8
"""

import math
import FreeCAD as App
import Part
import Sketcher

V = App.Vector

# ----------------------------------------------------------------- helpers
def add_rect(sk, x0, y0, x1, y1):
    """Add a rectangle (4 lines + coincidence constraints) to a sketch."""
    pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    ids = []
    for i in range(4):
        p1 = pts[i]
        p2 = pts[(i + 1) % 4]
        ids.append(sk.addGeometry(
            Part.LineSegment(V(p1[0], p1[1], 0), V(p2[0], p2[1], 0))))
    for i in range(4):
        sk.addConstraint(Sketcher.Constraint(
            'Coincident', ids[i], 2, ids[(i + 1) % 4], 1))
    return ids

def add_stadium_v(sk, cx, cz, w=5.0, h=14.0):
    """Vertical slot: width w along sketch-x, height h along sketch-y,
    semicircular caps (radius w/2) top and bottom."""
    r = w / 2.0
    s = (h - w) / 2.0            # half of the straight section
    lt = (cx - r, cz + s); lb = (cx - r, cz - s)
    rt = (cx + r, cz + s); rb = (cx + r, cz - s)
    i0 = sk.addGeometry(Part.LineSegment(V(*lt, 0), V(*lb, 0)))
    i1 = sk.addGeometry(Part.ArcOfCircle(
        Part.Circle(V(cx, cz - s, 0), V(0, 0, 1), r), math.pi, 2 * math.pi))
    i2 = sk.addGeometry(Part.LineSegment(V(*rb, 0), V(*rt, 0)))
    i3 = sk.addGeometry(Part.ArcOfCircle(
        Part.Circle(V(cx, cz + s, 0), V(0, 0, 1), r), 0.0, math.pi))
    for a, b in ((i0, i1), (i1, i2), (i2, i3), (i3, i0)):
        sk.addConstraint(Sketcher.Constraint('Coincident', a, 2, b, 1))

def add_stadium_h(sk, cx, cz, l=14.0, w=5.0):
    """Horizontal slot: length l along sketch-x, height w along sketch-y,
    semicircular caps (radius w/2) left and right."""
    r = w / 2.0
    s = (l - w) / 2.0
    tl = (cx - s, cz + r); tr = (cx + s, cz + r)
    bl = (cx - s, cz - r); br = (cx + s, cz - r)
    i0 = sk.addGeometry(Part.LineSegment(V(*bl, 0), V(*br, 0)))
    i1 = sk.addGeometry(Part.ArcOfCircle(
        Part.Circle(V(cx + s, cz, 0), V(0, 0, 1), r),
        math.radians(270), math.radians(450)))
    i2 = sk.addGeometry(Part.LineSegment(V(*tr, 0), V(*tl, 0)))
    i3 = sk.addGeometry(Part.ArcOfCircle(
        Part.Circle(V(cx - s, cz, 0), V(0, 0, 1), r),
        math.radians(90), math.radians(270)))
    for a, b in ((i0, i1), (i1, i2), (i2, i3), (i3, i0)):
        sk.addConstraint(Sketcher.Constraint('Coincident', a, 2, b, 1))

def add_poly(sk, pts):
    """Closed polygon from a list of (x, y) points."""
    n = len(pts)
    ids = []
    for i in range(n):
        p1 = pts[i]
        p2 = pts[(i + 1) % n]
        ids.append(sk.addGeometry(
            Part.LineSegment(V(p1[0], p1[1], 0), V(p2[0], p2[1], 0))))
    for i in range(n):
        sk.addConstraint(Sketcher.Constraint(
            'Coincident', ids[i], 2, ids[(i + 1) % n], 1))
    return ids

def add_circle(sk, x, y, d):
    return sk.addGeometry(Part.Circle(V(x, y, 0), V(0, 0, 1), d / 2.0))

# ----------------------------------------------------------------- document
doc = App.newDocument("PerforatedTrayBracket")
body = doc.addObject("PartDesign::Body", "BracketBody")

def make_pad(name, sk_name, z0, height, build):
    sk = body.newObject("Sketcher::SketchObject", sk_name)
    sk.Placement = App.Placement(V(0, 0, z0), App.Rotation())
    build(sk)
    pad = body.newObject("PartDesign::Pad", name)
    pad.Profile = sk
    pad.Length = height
    pad.Reversed = False
    pad.Midplane = False
    return sk, pad

# 1 ------------------------------------------------------------- base plate
make_pad("Pad_BasePlate", "Sketch_BasePlate", 0.0, 3.0,
         lambda sk: add_rect(sk, 0.0, 0.0, 160.0, 112.0))

# 2 ------------------------------------------------------------ front wall
make_pad("Pad_FrontWall", "Sketch_FrontWall", 0.0, 25.0,
         lambda sk: add_rect(sk, 0.0, 109.0, 160.0, 112.0))

# 3 ------------------------------------------------------------- back wall
make_pad("Pad_BackWall", "Sketch_BackWall", 0.0, 25.0,
         lambda sk: add_rect(sk, 0.0, 0.0, 160.0, 3.0))

# 4 ------------------------------------------- back wall tabs (Z 25 -> 43)
def _tabs(sk):
    add_rect(sk, 0.0, 0.0, 22.0, 3.0)
    add_rect(sk, 138.0, 0.0, 160.0, 3.0)
make_pad("Pad_BackTabs", "Sketch_BackTabs", 25.0, 18.0, _tabs)

# 5 ---------------------------------- ledge on back wall face (Z 23 -> 27)
make_pad("Pad_Ledge", "Sketch_Ledge", 23.0, 4.0,
         lambda sk: add_rect(sk, 22.0, 3.0, 138.0, 12.0))

# 6 ------------------------------------------------------- right side wall
make_pad("Pad_RightWall", "Sketch_RightWall", 0.0, 8.0,
         lambda sk: add_rect(sk, 157.0, 3.0, 160.0, 109.0))

# 7 ------------------------------ corner pads on front wall (Z 24 -> 27)
def _cpads(sk):
    add_rect(sk, 0.0, 94.0, 16.0, 112.0)
    add_rect(sk, 144.0, 94.0, 160.0, 112.0)
make_pad("Pad_CornerPads", "Sketch_CornerPads", 24.0, 3.0, _cpads)

# 8 ------------------------------------------------- centre rib (Z 3 -> 11)
RIB = [(60.0, 42.0), (75.0, 32.0), (86.0, 32.0), (97.5, 40.0),
       (120.0, 40.0), (120.0, 58.0), (101.0, 58.0), (101.0, 64.0),
       (86.5, 74.0), (75.0, 74.0), (75.0, 72.0), (40.0, 72.0),
       (40.0, 54.0), (60.0, 54.0)]
make_pad("Pad_Rib", "Sketch_Rib", 3.0, 8.0, lambda sk: add_poly(sk, RIB))

# 9 ------------------------------------------------- boss pads (Z 3 -> 14)
def _bpads(sk):
    add_rect(sk, 40.0, 54.0, 75.0, 72.0)     # left pad 35 x 18
    add_rect(sk, 87.0, 40.0, 120.0, 58.0)    # right pad 33 x 18
make_pad("Pad_BossPads", "Sketch_BossPads", 3.0, 11.0, _bpads)

# 10 ---------------------------------------------------- front wall slots
# sketch plane parallel to XZ at Y=112 (front face); sketch x -> world X,
# sketch y -> world Z. Pocket cuts -Y (reversed) through the 3 mm wall.
sk_fs = body.newObject("Sketcher::SketchObject", "Sketch_FrontSlots")
sk_fs.Placement = App.Placement(V(0, 112, 0), App.Rotation(V(1, 0, 0), 90))
for k in range(11):
    add_stadium_v(sk_fs, 11.0 + 13.8 * k, 15.0, 5.0, 14.0)
pk_fs = body.newObject("PartDesign::Pocket", "Pocket_FrontSlots")
pk_fs.Profile = sk_fs
pk_fs.Length = 3.0
pk_fs.Reversed = True

# 11 ----------------------------------- back wall slots + tab slots (2x14x5)
sk_bs = body.newObject("Sketcher::SketchObject", "Sketch_BackSlots")
sk_bs.Placement = App.Placement(V(0, 0, 0), App.Rotation(V(1, 0, 0), 90))
for k in range(11):
    add_stadium_v(sk_bs, 11.0 + 13.8 * k, 15.0, 5.0, 14.0)
add_stadium_h(sk_bs, 11.0, 34.0, 14.0, 5.0)
add_stadium_h(sk_bs, 149.0, 34.0, 14.0, 5.0)
pk_bs = body.newObject("PartDesign::Pocket", "Pocket_BackSlots")
pk_bs.Profile = sk_bs
pk_bs.Length = 3.0
pk_bs.Reversed = False

# 12 ------------------------------------------------ corner pad holes 4x3.6
sk_ch = body.newObject("Sketcher::SketchObject", "Sketch_CornerHoles")
sk_ch.Placement = App.Placement(V(0, 0, 27.0), App.Rotation())
for hx in (5.0, 11.0, 149.0, 155.0):
    add_circle(sk_ch, hx, 101.0, 3.6)
pk_ch = body.newObject("PartDesign::Pocket", "Pocket_CornerHoles")
pk_ch.Profile = sk_ch
pk_ch.Length = 3.0

# 13 ---------------------------------------------------- boss holes 4x4.8
sk_bh = body.newObject("Sketcher::SketchObject", "Sketch_BossHoles")
sk_bh.Placement = App.Placement(V(0, 0, 14.0), App.Rotation())
for hx, hy in ((56.0, 63.0), (68.0, 63.0), (95.0, 49.0), (107.0, 49.0)):
    add_circle(sk_bh, hx, hy, 4.8)
pk_bh = body.newObject("PartDesign::Pocket", "Pocket_BossHoles")
pk_bh.Profile = sk_bh
pk_bh.Type = "ThroughAll"

# ----------------------------------------------------------------- finalise
doc.recompute()

# simple validation
shape = body.Shape
solids = shape.Solids
App.Console.PrintMessage("Bodies: %d, solids: %d\n" % (1, len(solids)))
App.Console.PrintMessage("Volume: %.2f mm^3\n" % shape.Volume)
bb = shape.BoundBox
App.Console.PrintMessage("BBox: X %.2f..%.2f  Y %.2f..%.2f  Z %.2f..%.2f\n"
                         % (bb.XMin, bb.XMax, bb.YMin, bb.YMax, bb.ZMin, bb.ZMax))
if len(solids) != 1:
    raise RuntimeError("Result is not a single solid!")

doc.saveAs("/app/answer.FCStd")
App.Console.PrintMessage("Saved /app/answer.FCStd\n")
