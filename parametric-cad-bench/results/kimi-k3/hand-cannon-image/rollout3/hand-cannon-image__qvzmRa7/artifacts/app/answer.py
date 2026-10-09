# FreeCAD 1.1.0 script: builds the "ORNATE HAND CANNON" part from the
# engineering drawing hand-cannon.png and saves it to answer.FCStd.
#
# Geometry read from the drawing (all mm):
#   Barrel is a surface of revolution about the X axis, muzzle face at X=0.
#   Outer profile stations (X, radius) from the drawing:
#     (0,29) Ø58 muzzle face   (4,31) Ø62 lip   (9,29) Ø58
#     (18,22) Ø44   (30,18) Ø36   (49,16) Ø32 waist ... to X=98
#     X=98..107 ring Ø42 (9 wide)   X=107..117 groove Ø34
#     X=117..125 ring Ø38 (8 wide)  breech shoulder at X=125
#     Tang: X=125..140 Ø22, X=140..162 Ø28  (total length 162)
#   Bore (blind): Ø50 at muzzle, conical taper to Ø21 at X=30,
#     then Ø21 straight to a flat bottom at X=88.
#   Grip: rectangular bar, horizontal width 16, sides at 30 deg from
#     vertical, depth 22 (Z), running from the barrel underside to the
#     pommel; right side meets the breech face, left side the groove.
#   Pommel: 22 (X) x 12 (Y) x 28 (Z) block, bottom 82 below the barrel
#     axis; right edge 3.36 mm past the grip's right edge.
#
# The part is built as a single PartDesign Body with a feature tree:
#   Sketch_Barrel -> Revolution_Barrel -> (Sketch_Bore -> Groove_Bore)
#   -> (Sketch_Grip -> Pad_Grip) -> (Sketch_Pommel -> Pad_Pommel)

import os
import math
import FreeCAD as App
import Part
import Sketcher

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "answer.FCStd")

TAN30 = math.tan(math.radians(30.0))


def make_profile_sketch(body, name, points):
    """Closed polyline sketch on the XY plane from a list of (x, y) points."""
    sk = body.newObject("Sketcher::SketchObject", name)
    pts = list(points)
    n = len(pts)
    for i in range(n):
        p0 = pts[i]
        p1 = pts[(i + 1) % n]
        sk.addGeometry(
            Part.LineSegment(App.Vector(p0[0], p0[1], 0.0),
                             App.Vector(p1[0], p1[1], 0.0)),
            False,
        )
    for i in range(n):
        j = (i + 1) % n
        sk.addConstraint(Sketcher.Constraint("Coincident", i, 2, j, 1))
    return sk


def main():
    doc = App.newDocument("hand_cannon")
    body = doc.addObject("PartDesign::Body", "Body")

    # ------------------------------------------------------------------
    # 1. Barrel: revolved outer profile about the X axis.
    # ------------------------------------------------------------------
    outer = [
        (0.0, 29.0),    # muzzle face, dia 58
        (4.0, 31.0),    # bell lip, dia 62
        (9.0, 29.0),    # dia 58
        (18.0, 22.0),   # dia 44
        (30.0, 18.0),   # dia 36
        (49.0, 16.0),   # waist, dia 32
        (98.0, 16.0),   # end of waist
        (98.0, 21.0),   # ring 1, dia 42 (9 mm wide)
        (107.0, 21.0),
        (107.0, 17.0),  # groove, dia 34
        (117.0, 17.0),
        (117.0, 19.0),  # ring 2, dia 38 (8 mm wide)
        (125.0, 19.0),  # breech shoulder at X=125
        (125.0, 11.0),  # tang section 1, dia 22
        (140.0, 11.0),
        (140.0, 14.0),  # tang section 2, dia 28
        (162.0, 14.0),  # rear face, total length 162
        (162.0, 0.0),
        (0.0, 0.0),
    ]
    sk_barrel = make_profile_sketch(body, "Sketch_Barrel", outer)

    rev = body.newObject("PartDesign::Revolution", "Revolution_Barrel")
    rev.Profile = sk_barrel
    rev.ReferenceAxis = (sk_barrel, ["H_Axis"])
    rev.Angle = 360.0

    # ------------------------------------------------------------------
    # 2. Bore: revolved groove cut (blind, flat bottom at X=88).
    # ------------------------------------------------------------------
    bore = [
        (0.0, 0.0),
        (0.0, 25.0),    # dia 50 opening at the muzzle
        (30.0, 10.5),   # cone down to dia 21 at X=30
        (88.0, 10.5),   # straight dia 21 to X=88
        (88.0, 0.0),    # flat bore bottom
    ]
    sk_bore = make_profile_sketch(body, "Sketch_Bore", bore)

    groove = body.newObject("PartDesign::Groove", "Groove_Bore")
    groove.Profile = sk_bore
    groove.ReferenceAxis = (sk_bore, ["H_Axis"])
    groove.Angle = 360.0
    groove.BaseFeature = rev

    # ------------------------------------------------------------------
    # 3. Grip bar: parallelogram, sides 30 deg from vertical, horizontal
    #    width 16, extruded 22 (midplane) in Z.
    # ------------------------------------------------------------------
    # Right side line passes through (125.2, -12.4) (breech face bottom).
    def x_right(y):
        return 125.2 - TAN30 * (y + 12.4)

    def x_left(y):
        return x_right(y) - 16.0

    y_top = -1.0        # starts inside the barrel
    y_bot = -72.0       # ends inside the pommel (pommel top is at -70)
    grip = [
        (x_right(y_top), y_top),
        (x_left(y_top), y_top),
        (x_left(y_bot), y_bot),
        (x_right(y_bot), y_bot),
    ]
    sk_grip = make_profile_sketch(body, "Sketch_Grip", grip)

    pad_grip = body.newObject("PartDesign::Pad", "Pad_Grip")
    pad_grip.Profile = sk_grip
    pad_grip.Length = 22.0       # grip depth in Z
    pad_grip.SideType = "Symmetric"
    pad_grip.BaseFeature = groove

    # ------------------------------------------------------------------
    # 4. Pommel: 22 (X) x 12 (Y) block, 28 deep in Z, bottom at -82,
    #    right edge 3.36 mm past the grip's right edge at the pommel top.
    # ------------------------------------------------------------------
    y_p_top = -70.0
    y_p_bot = -82.0
    x_p_right = x_right(y_p_top) + 3.36
    x_p_left = x_p_right - 22.0
    pommel = [
        (x_p_right, y_p_top),
        (x_p_left, y_p_top),
        (x_p_left, y_p_bot),
        (x_p_right, y_p_bot),
    ]
    sk_pommel = make_profile_sketch(body, "Sketch_Pommel", pommel)

    pad_pommel = body.newObject("PartDesign::Pad", "Pad_Pommel")
    pad_pommel.Profile = sk_pommel
    pad_pommel.Length = 28.0     # pommel depth in Z
    pad_pommel.SideType = "Symmetric"
    pad_pommel.BaseFeature = pad_grip

    body.Tip = pad_pommel
    doc.recompute()

    shape = body.Shape
    solids = shape.Solids
    print("Solids:", len(solids))
    print("Volume: %.2f mm^3" % shape.Volume)
    bb = shape.BoundBox
    print("BBox: X %.2f..%.2f  Y %.2f..%.2f  Z %.2f..%.2f"
          % (bb.XMin, bb.XMax, bb.YMin, bb.YMax, bb.ZMin, bb.ZMax))
    if len(solids) != 1:
        raise RuntimeError("Result is not a single solid!")

    doc.saveAs(OUT)
    print("Saved:", OUT)


main()
