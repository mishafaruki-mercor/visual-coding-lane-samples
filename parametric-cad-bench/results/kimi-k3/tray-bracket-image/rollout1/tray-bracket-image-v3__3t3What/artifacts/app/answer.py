import FreeCAD as App
import Part
from FreeCAD import Vector
import math, os

DOC_NAME = "bracket"

def new_doc():
    try: App.closeDocument(DOC_NAME)
    except Exception: pass
    return App.newDocument(DOC_NAME)

def sketch_xy(body, name, z=0.0):
    sk = body.newObject('Sketcher::SketchObject', name)
    sk.AttachmentSupport = [(body.getObject('XY_Plane'), '')]
    sk.MapMode = 'FlatFace'
    if z: sk.AttachmentOffset = App.Placement(Vector(0,0,z), App.Rotation())
    return sk

def sketch_xz(body, name, y=0.0):
    # XZ plane; local Z maps to global -Y, so offset (0,0,-y) puts base at global y
    sk = body.newObject('Sketcher::SketchObject', name)
    sk.AttachmentSupport = [(body.getObject('XZ_Plane'), '')]
    sk.MapMode = 'FlatFace'
    if y: sk.AttachmentOffset = App.Placement(Vector(0,0,-y), App.Rotation())
    return sk

def rect(sk, x0, y0, x1, y1):
    pts=[(x0,y0),(x1,y0),(x1,y1),(x0,y1)]
    for i in range(4):
        a=pts[i]; b=pts[(i+1)%4]
        sk.addGeometry(Part.LineSegment(Vector(a[0],a[1],0),Vector(b[0],b[1],0)))

def poly(sk, pts):
    for i in range(len(pts)):
        a=pts[i]; b=pts[(i+1)%len(pts)]
        sk.addGeometry(Part.LineSegment(Vector(a[0],a[1],0),Vector(b[0],b[1],0)))

def circle(sk, x, y, r):
    sk.addGeometry(Part.Circle(Vector(x,y,0),Vector(0,0,1),r))

def vslot(sk, cx, z0, w, h):
    r = w/2.0
    wl, wr = cx-w/2.0, cx+w/2.0
    zb, zt = z0+r, z0+h-r
    sk.addGeometry(Part.LineSegment(Vector(wr,zb,0),Vector(wr,zt,0)))
    sk.addGeometry(Part.ArcOfCircle(Part.Circle(Vector(cx,zt,0),Vector(0,0,1),r),0.0,math.pi))
    sk.addGeometry(Part.LineSegment(Vector(wl,zt,0),Vector(wl,zb,0)))
    sk.addGeometry(Part.ArcOfCircle(Part.Circle(Vector(cx,zb,0),Vector(0,0,1),r),math.pi,2*math.pi))

def hslot(sk, cx, cz, L, H):
    r = H/2.0
    xl, xr = cx-L/2.0+r, cx+L/2.0-r
    zb, zt = cz-H/2.0, cz+H/2.0
    sk.addGeometry(Part.LineSegment(Vector(xl,zb,0),Vector(xr,zb,0)))
    sk.addGeometry(Part.ArcOfCircle(Part.Circle(Vector(xr,cz,0),Vector(0,0,1),r),-math.pi/2,math.pi/2))
    sk.addGeometry(Part.LineSegment(Vector(xr,zt,0),Vector(xl,zt,0)))
    sk.addGeometry(Part.ArcOfCircle(Part.Circle(Vector(xl,cz,0),Vector(0,0,1),r),math.pi/2,3*math.pi/2))

def pad(body, sk, name, L, rev=False):
    p=body.newObject('PartDesign::Pad',name); p.Profile=sk; p.Length=L; p.Reversed=rev
    return p

def pocket(body, sk, name, L, rev=False):
    p=body.newObject('PartDesign::Pocket',name); p.Profile=sk; p.Length=L; p.Reversed=rev
    return p

def build():
    doc = new_doc()
    body = doc.addObject('PartDesign::Body','Bracket')

    # Base plate 160x112, z=0..3
    sk = sketch_xy(body,'Sketch_Base',0); rect(sk,0,0,160,112); pad(body,sk,'Pad_Base',3)

    # Interior platform (floor) X0..160, Y3..109, z=3..8
    sk = sketch_xy(body,'Sketch_Floor',3); rect(sk,0,3,160,109); pad(body,sk,'Pad_Floor',5)

    # Front wall X0..160, Y0..3, z=3..25
    sk = sketch_xy(body,'Sketch_FrontWall',3); rect(sk,0,0,160,3); pad(body,sk,'Pad_FrontWall',22)

    # Back wall X0..160, Y109..112, z=3..25
    sk = sketch_xy(body,'Sketch_BackWall',3); rect(sk,0,109,160,112); pad(body,sk,'Pad_BackWall',22)

    # Tabs X0..22 & 138..160, Y109..112, z=25..43
    sk = sketch_xy(body,'Sketch_Tabs',25); rect(sk,0,109,22,112); rect(sk,138,109,160,112); pad(body,sk,'Pad_Tabs',18)

    # Bar X22..138, Y100..109, z=23..27
    sk = sketch_xy(body,'Sketch_Bar',23); rect(sk,22,100,138,109); pad(body,sk,'Pad_Bar',4)

    # Corner bosses X0..16 & 144..160, Y0..18, z=24..27
    sk = sketch_xy(body,'Sketch_Bosses',24); rect(sk,0,0,16,18); rect(sk,144,0,160,18); pad(body,sk,'Pad_Bosses',3)

    # Pads z=8..14
    sk = sketch_xy(body,'Sketch_Pad1',8); rect(sk,40,40,75,58); pad(body,sk,'Pad_Pad1',6)
    sk = sketch_xy(body,'Sketch_Pad2',8); rect(sk,87,54,120,72); pad(body,sk,'Pad_Pad2',6)

    # Ribs (pentagons) z=8..11
    sk = sketch_xy(body,'Sketch_Rib1',8)
    poly(sk,[(59.8,56),(59.8,70),(74.8,80),(86.2,80),(98.4,72),(98.4,56)])
    pad(body,sk,'Pad_Rib1',3)
    sk = sketch_xy(body,'Sketch_Rib2',8)
    poly(sk,[(73,56),(101.1,56),(101.1,48),(86.2,38),(74.5,38),(73,48)])
    pad(body,sk,'Pad_Rib2',3)

    # Front wall slots (through front wall Y0..3)
    sk = sketch_xz(body,'Sketch_FrontSlots',0)
    for k in range(11): vslot(sk, 11+13.8*k, 8, 5, 14)
    pocket(body,sk,'Pocket_FrontSlots',3)

    # Back wall slots (through back wall Y109..112): sketch at global y=109
    sk = sketch_xz(body,'Sketch_BackSlots',109)
    for k in range(11): vslot(sk, 11+13.8*k, 8, 5, 14)
    pocket(body,sk,'Pocket_BackSlots',3)

    # Tab slots (horizontal, through tabs Y109..112)
    sk = sketch_xz(body,'Sketch_TabSlots',109)
    hslot(sk, 11, 34, 14, 5)
    hslot(sk, 149, 34, 14, 5)
    pocket(body,sk,'Pocket_TabSlots',3)

    # Boss holes (4x dia 3.6, through bosses z=24..27)
    sk = sketch_xy(body,'Sketch_BossHoles',27)
    for (hx,hy) in [(5,11),(11,11),(149,11),(155,11)]: circle(sk,hx,hy,1.8)
    pocket(body,sk,'Pocket_BossHoles',3)

    # Pad holes (4x dia 4.8, through pads z=8..14)
    sk = sketch_xy(body,'Sketch_PadHoles',14)
    for (hx,hy) in [(56,49),(68,49),(95,63),(107,63)]: circle(sk,hx,hy,2.4)
    pocket(body,sk,'Pocket_PadHoles',6)

    doc.recompute()
    return doc, body

doc, body = build()
out = '/app/answer.FCStd'
if os.path.exists(out): os.remove(out)
doc.saveAs(out)
print('SAVED', out, 'solids:', len(body.Shape.Solids), 'vol:', body.Shape.Volume)
