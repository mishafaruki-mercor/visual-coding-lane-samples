# -*- coding: utf-8 -*-
"""
PERFORATED_TRAY_BRACKET - generated from engineering drawing /app/perforated-tray-bracket.png
FreeCAD 1.1.0 - one PartDesign Body, feature tree of named objects, single solid.

Coordinate system: X = length (0..160), Y = depth (0..115, back->front), Z = height.
All dimensions in mm, read from the drawing.
"""
import FreeCAD as App
import Part
import Sketcher

DOC = App.newDocument("answer")

# ---------------------------------------------------------------- helpers
def add_box(body, name, x0, y0, z0, x1, y1, z1):
    """PartDesign additive box from (x0,y0,z0) to (x1,y1,z1)."""
    f = body.newObject("PartDesign::AdditiveBox", name)
    f.Length = abs(x1 - x0)
    f.Width  = abs(y1 - y0)
    f.Height = abs(z1 - z0)
    f.Placement = App.Placement(App.Vector(min(x0,x1), min(y0,y1), min(z0,z1)),
                                App.Rotation())
    return f

def sub_box(body, name, x0, y0, z0, x1, y1, z1):
    f = body.newObject("PartDesign::SubtractiveBox", name)
    f.Length = abs(x1 - x0)
    f.Width  = abs(y1 - y0)
    f.Height = abs(z1 - z0)
    f.Placement = App.Placement(App.Vector(min(x0,x1), min(y0,y1), min(z0,z1)),
                                App.Rotation())
    return f

def sub_cyl(body, name, cx, cy, z0, z1, radius):
    """Subtractive cylinder along Z centred (cx,cy), z0..z1."""
    f = body.newObject("PartDesign::SubtractiveCylinder", name)
    f.Radius = radius
    f.Height = abs(z1 - z0)
    f.Placement = App.Placement(App.Vector(cx, cy, min(z0,z1)), App.Rotation())
    return f

def stadium_sketch(body, name, plane, slots, normal):
    """
    Sketch holding several 'stadium' (capsule) profiles.
    plane  : (origin Vector, rotation) for the sketch placement
    slots  : list of (cu, cv, w, h) -> centre in sketch u/v coords, width along u, height along v
    """
    import math
    sk = body.newObject("Sketcher::SketchObject", name)
    sk.Placement = App.Placement(plane[0], plane[1])
    for (cu, cv, w, h) in slots:
        r = w / 2.0
        hs = (h - w) / 2.0  # half length of the straight part
        # left line
        sk.addGeometry(Part.LineSegment(App.Vector(cu-r, cv-hs, 0), App.Vector(cu-r, cv+hs, 0)), False)
        # top semicircle (from (cu+r,cv+hs) to (cu-r,cv+hs), bulging +v)
        sk.addGeometry(Part.ArcOfCircle(Part.Circle(App.Vector(cu, cv+hs, 0), App.Vector(0,0,1), r), 0.0, math.pi), False)
        # right line
        sk.addGeometry(Part.LineSegment(App.Vector(cu+r, cv+hs, 0), App.Vector(cu+r, cv-hs, 0)), False)
        # bottom semicircle (from (cu-r,cv-hs) to (cu+r,cv-hs), bulging -v)
        sk.addGeometry(Part.ArcOfCircle(Part.Circle(App.Vector(cu, cv-hs, 0), App.Vector(0,0,1), r), math.pi, 2*math.pi), False)
    return sk

# ---------------------------------------------------------------- build
body = doc_body = DOC.addObject("PartDesign::Body", "Bracket")

# 1. base plate 160 x 112 x 3
add_box(body, "BasePlate", 0, 0, 0, 160, 112, 3)

# 2. back wall (Y 0-3, Z 0-25)
add_box(body, "BackWall", 0, 0, 0, 160, 3, 25)

# 3. top flange of back wall (X 22-138, Y 0-12, Z 22-25)
add_box(body, "BackFlange", 22, 0, 22, 138, 12, 25)

# 4/5. ears on back wall (X 0-22 and X 138-160, Y 0-3, Z 25-43)
add_box(body, "EarLeft",  0,   0, 25, 22,  3, 43)
add_box(body, "EarRight", 138, 0, 25, 160, 3, 43)

# 6. front wall (Y 112-115, Z 0-23)
add_box(body, "FrontWall", 0, 112, 0, 160, 115, 23)

# 7. right side wall (X 157-160, Y 0-112, Z 0-23)
add_box(body, "RightWall", 157, 0, 0, 160, 112, 23)

# 8. left lip (X 0-3, Y 3-112, Z 0-4.5)
add_box(body, "LeftLip", 0, 3, 0, 3, 112, 4.5)

# 9/10. pads (Z 3-11 -> 8 tall)
add_box(body, "PadLeft",  40, 56, 3, 75,  74, 11)
add_box(body, "PadRight", 87, 40, 3, 120, 58, 11)

# 11. corner blocks on front wall top (Z 22-25)
add_box(body, "CornerBlockLeft",  0,   97, 22, 16,  115, 25)
add_box(body, "CornerBlockRight", 144, 97, 22, 160, 115, 25)

# 12. rib boss (6 tall, Z 3-9) via sketch + Pad
# rib boss outline in plan (X,Y): starts on left pad top edge (X=60, the "41" dim),
# rises 19 to the plateau (the "19" dim), plateau 11 long, descends to right pad,
# lower boundary dips and returns to the left pad bottom-right corner.
rib_pts = [(60.0,56.0),(60.0,52.0),(75.0,33.0),(86.0,33.0),(98.0,40.0),
           (101.0,40.0),(101.0,58.0),(86.0,76.0),(75.0,74.0),(60.0,74.0)]
rib_sk = body.newObject("Sketcher::SketchObject", "RibSketch")
rib_sk.Placement = App.Placement(App.Vector(0,0,3), App.Rotation())
n = len(rib_pts)
for i in range(n):
    p0 = rib_pts[i]; p1 = rib_pts[(i+1) % n]
    rib_sk.addGeometry(Part.LineSegment(App.Vector(p0[0],p0[1],0), App.Vector(p1[0],p1[1],0)), False)
for i in range(n):
    rib_sk.addConstraint(Sketcher.Constraint('Coincident', i, 2, (i+1)%n, 1))
rib_pad = body.newObject("PartDesign::Pad", "RibBoss")
rib_pad.Profile = rib_sk
rib_pad.Length = 6.0
rib_pad.Reversed = False
# (Midplane defaults to False)
rib_pad.Type = 0

# 13. perforation slots on back wall + front wall: 11 x (5 x 14) at X=11+13.8i, Z 8-22
XZ = App.Rotation(App.Vector(1,0,0), 90)   # local (u,v)->world (u,0,v), normal -Y
YZ = App.Rotation(App.Vector(1,1,1), 120)  # local (u,v)->world (0,u,v), normal +X
slots_x = [11 + i*13.8 for i in range(11)]
# back wall: sketch on XZ plane at Y=0 (outer face), normal -Y, pocket reversed into +Y
sk_b = stadium_sketch(body, "SlotsBackSketch",
                      (App.Vector(0,0,0), XZ),
                      [(x, 15.0, 5.0, 14.0) for x in slots_x], "-Y")
pk_b = body.newObject("PartDesign::Pocket", "SlotsBack")
pk_b.Profile = sk_b
pk_b.Length = 3.0
pk_b.Reversed = False
# front wall: sketch on XZ plane at Y=115 (outer face), normal -Y points into wall
sk_f = stadium_sketch(body, "SlotsFrontSketch",
                      (App.Vector(0,115,0), XZ),
                      [(x, 15.0, 5.0, 14.0) for x in slots_x], "-Y")
pk_f = body.newObject("PartDesign::Pocket", "SlotsFront")
pk_f.Profile = sk_f
pk_f.Length = 3.0
pk_f.Reversed = True

# 14. right wall slots: 4 x (5 x 14) along Y, Z 8-22 ; wall X 157-160
#     sketch on YZ plane at X=157 (inner face), normal +X points into wall
sk_r = stadium_sketch(body, "SlotsRightSketch",
                      (App.Vector(157,0,0), YZ),
                      [(y, 15.0, 5.0, 14.0) for y in (20.0, 45.0, 70.0, 95.0)], "+X")
pk_r = body.newObject("PartDesign::Pocket", "SlotsRight")
pk_r.Profile = sk_r
pk_r.Length = 3.0
pk_r.Reversed = True

# 15. ear slots: 2 x (14 x 5) horizontal, Z 31.5-36.5 ; through back wall (Y 0-3)
sk_e = stadium_sketch(body, "SlotsEarSketch",
                      (App.Vector(0,0,0), XZ),
                      [(11.0, 34.0, 14.0, 5.0), (149.0, 34.0, 14.0, 5.0)], "-Y")
pk_e = body.newObject("PartDesign::Pocket", "SlotsEar")
pk_e.Profile = sk_e
pk_e.Length = 3.0
pk_e.Reversed = False

# 16. pad holes: 4 x dia 4.8 through pads (Z 3-11)
for j,(hx,hy) in enumerate([(56,65),(68,65),(95,49),(107,49)]):
    sub_cyl(body, "PadHole%d" % (j+1), hx, hy, 3, 11, 2.4)

# 17. corner block holes: 4 x dia 3.6 through blocks (Z 22-25)
for j,(hx,hy) in enumerate([(5,101),(11,101),(149,101),(155,101)]):
    sub_cyl(body, "CornerHole%d" % (j+1), hx, hy, 22, 25, 1.8)

# 18. front wall notch (X 96-106, Z 14.5-18.5, through Y 112-115)
sub_box(body, "FrontNotch", 96, 112, 14.5, 106, 115, 18.5)

# ---------------------------------------------------------------- finish
DOC.recompute()
# ensure single solid
shape = body.Shape
print("solids:", len(shape.Solids), "volume:", shape.Volume)
assert len(shape.Solids) == 1, "not a single solid!"
DOC.saveAs("/app/answer.FCStd")
print("saved /app/answer.FCStd")
