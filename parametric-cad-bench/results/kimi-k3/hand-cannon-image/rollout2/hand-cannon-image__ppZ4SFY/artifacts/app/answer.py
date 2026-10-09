"""
ORNATE HAND CANNON - reconstructed from the engineering drawing /app/hand-cannon.png

Geometry (all mm), barrel axis along global X, muzzle face at X=0:
  - Revolved barrel (about X axis):
      outer: face r30 @0, rim crown to r31 @4, cones r29 @9, r22 @18, r18 @30,
             r16 @49 (barrel) to 88, cone to r17 @98, band r21 (98-107, Ø42, w9),
             groove r17 (107-117, Ø34), band r19 (117-125, Ø38, w8), back face @125
      inner: bore cone r25->r10.5 (0->30), bore r10.5 (30->88, blind), wall @88
  - Handle bar: flat bar in XZ center plane, 30 deg from vertical, horizontal
    extent 16, thickness 22 (Y +/-11), from breech underside into the pommel
  - Pommel: 22(X) x 12(Z) x 28(Y) block, X 140-162, Z -70..-82 (bottom at -82)

Produces one PartDesign Body with a feature tree of named objects -> single solid.
"""

import FreeCAD as App
import Part
import Sketcher

import os

try:
    App.ParamGet("BaseApp/Preferences/Document").SetInt("CountBackupFiles", 0)
except Exception:
    pass

DOC_NAME = "answer"
OUT_PATH = "/app/answer.FCStd"


def build():
    existing = [d for d in App.listDocuments() if d == DOC_NAME]
    for d in existing:
        App.closeDocument(d)
    doc = App.newDocument(DOC_NAME)
    body = doc.addObject("PartDesign::Body", "HandCannon")

    # ------------------------------------------------------------------
    # 1) Barrel profile sketch on the global XZ plane (normal -Y)
    #    sketch local (u,v) -> global (u, 0, v)
    # ------------------------------------------------------------------
    sk = body.newObject("Sketcher::SketchObject", "BarrelProfile")
    sk.Placement = App.Placement(App.Vector(0, 0, 0),
                                 App.Rotation(App.Vector(1, 0, 0), 90))

    # outer + inner profile (closed loop), (x, r)
    pts = [
        (0.0, 25.0),    # bore mouth (face inner edge)
        (0.0, 30.0),    # muzzle face outer corner
        (4.0, 31.0),    # rim crown (Ø62)
        (9.0, 29.0),    # flare kink (Ø58)
        (18.0, 22.0),   # flare (Ø44)
        (30.0, 18.0),   # flare (Ø36)
        (49.0, 16.0),   # flare end / barrel (Ø32)
        (88.0, 16.0),   # barrel end
        (98.0, 17.0),   # cone to groove level (Ø34)
        (98.0, 21.0),   # step up to band 1
        (107.0, 21.0),  # band 1 (Ø42, width 9)
        (107.0, 17.0),  # step down to groove
        (117.0, 17.0),  # groove (Ø34, width 10)
        (117.0, 19.0),  # step up to band 2
        (125.0, 19.0),  # band 2 (Ø38, width 8)
        (125.0, 0.0),   # breech back face down to axis
        (88.0, 0.0),    # along axis to bore bottom
        (88.0, 10.5),   # bore bottom wall (Ø21)
        (30.0, 10.5),   # bore (Ø21)
        # back to (0,25) via the conical mouth
    ]
    n = len(pts)
    for i in range(n):
        p0 = pts[i]
        p1 = pts[(i + 1) % n]
        sk.addGeometry(Part.LineSegment(App.Vector(p0[0], p0[1], 0),
                                        App.Vector(p1[0], p1[1], 0)), False)

    rev = body.newObject("PartDesign::Revolution", "BarrelRevolution")
    rev.Profile = sk
    rev.ReferenceAxis = (sk, ["H_Axis"])   # revolve about sketch X axis (global X)
    rev.Angle = 360.0

    # ------------------------------------------------------------------
    # 2) Handle bar sketch on the XZ plane
    # ------------------------------------------------------------------
    sk2 = body.newObject("Sketcher::SketchObject", "HandleBarProfile")
    sk2.Placement = App.Placement(App.Vector(0, 0, 0),
                                  App.Rotation(App.Vector(1, 0, 0), 90))

    tan30 = 0.5773502691896258
    # right edge passes through (158.64, -70) [3.36 from pommel back face 162]
    # left edge 16 mm to its left (horizontal extent)
    def xr(z):  # right edge x at height z
        return 158.64 - (z + 70.0) * tan30

    def xl(z):  # left edge x at height z
        return 142.64 - (z + 70.0) * tan30

    z_top = 10.0       # embedded into the bands (fusion)
    z_bot = -74.0      # embedded into the pommel (fusion)
    bar = [
        (xl(z_top), z_top),
        (xr(z_top), z_top),
        (xr(z_bot), z_bot),
        (xl(z_bot), z_bot),
    ]
    for i in range(4):
        p0 = bar[i]
        p1 = bar[(i + 1) % 4]
        sk2.addGeometry(Part.LineSegment(App.Vector(p0[0], p0[1], 0),
                                         App.Vector(p1[0], p1[1], 0)), False)

    pad2 = body.newObject("PartDesign::Pad", "HandleBar")
    pad2.Profile = sk2
    pad2.Length = 22.0
    pad2.SideType = "Symmetric"

    # ------------------------------------------------------------------
    # 3) Pommel sketch on the XZ plane
    # ------------------------------------------------------------------
    sk3 = body.newObject("Sketcher::SketchObject", "PommelProfile")
    sk3.Placement = App.Placement(App.Vector(0, 0, 0),
                                  App.Rotation(App.Vector(1, 0, 0), 90))
    pom = [(140.0, -70.0), (162.0, -70.0), (162.0, -82.0), (140.0, -82.0)]
    for i in range(4):
        p0 = pom[i]
        p1 = pom[(i + 1) % 4]
        sk3.addGeometry(Part.LineSegment(App.Vector(p0[0], p0[1], 0),
                                         App.Vector(p1[0], p1[1], 0)), False)

    pad3 = body.newObject("PartDesign::Pad", "Pommel")
    pad3.Profile = sk3
    pad3.Length = 28.0
    pad3.SideType = "Symmetric"

    doc.recompute()
    return doc, body


def main():
    doc, body = build()

    # ---------------- verification ----------------
    shape = body.Shape
    solids = shape.Solids
    print("Solids:", len(solids))
    print("Volume: %.2f mm^3" % shape.Volume)
    bb = shape.BoundBox
    print("BBox: X %.2f..%.2f  Y %.2f..%.2f  Z %.2f..%.2f"
          % (bb.XMin, bb.XMax, bb.YMin, bb.YMax, bb.ZMin, bb.ZMax))
    if len(solids) != 1:
        raise RuntimeError("expected a single solid")

    doc.saveAs(OUT_PATH)
    # remove any backup artifacts created next to the answer
    for fn in os.listdir("/app"):
        if fn.startswith("answer.") and (fn.endswith(".FCBak") or ".FCBak" in fn):
            try:
                os.remove(os.path.join("/app", fn))
            except OSError:
                pass
    print("saved", OUT_PATH)


main()
