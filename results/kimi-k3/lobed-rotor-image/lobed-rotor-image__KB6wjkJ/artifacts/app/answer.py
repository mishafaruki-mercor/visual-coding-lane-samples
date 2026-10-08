import FreeCAD as App
import Part, Sketcher
import math
import numpy as np

# ============ PARAMETERS ============
R_OUT = 54.0          # Ø108
H_DISC = 18.0         # disc height
BOSS_AF = 14.4        # hexagon across-flats
BOSS_TOP = 19.25      # boss top z
FLOOR_T = 4.0         # bottom floor thickness
# Flower profile
R_C = 12.2
R_LOBE = 4.0
N_LOBE = 7
SAT_PITCH = 33.0      # Ø66
SAT_ANGLES = [18,90,162,234,306]  # math degrees
CENTRAL_PHASE = 14.5  # valley phase of central rotor
# Teeth
N_TEETH = 21
TEETH_R_IN = 45.5     # Ø91
TEETH_R_OUT = 49.5    # Ø99
TEETH_GAP_DEG = 9.86  # gap angular width
TEETH_PHASE = 270.0   # gap center at math 270 (bottom)
TEETH_Z0, TEETH_Z1 = 15.0, 18.0
# Slot
SLOT_W = 6.0
SLOT_ANGLE = 90.0     # math, top
SLOT_R_IN = 45.5
SLOT_R_OUT = 54.0
SLOT_Z0, SLOT_Z1 = 15.0, 18.0
# Flower z
FLOWER_Z0, FLOWER_Z1 = 4.0, 18.0

# ============ FLOWER ARCS ============
DTH = 2*math.pi/N_LOBE
HALF = DTH/2
_c0 = np.array([R_C,0.0]); _c1 = np.array([R_C*math.cos(HALF), R_C*math.sin(HALF)])
R_VALLEY = float(np.linalg.norm(_c1-_c0)) - R_LOBE

def flower_edges(cx, cy, valley_phase_deg):
    geos=[]
    vp = math.radians(valley_phase_deg)
    for k in range(N_LOBE):
        lk = vp + HALF + k*DTH
        Cl = np.array([cx + R_C*math.cos(lk), cy + R_C*math.sin(lk)])
        def tang(sign):
            vAng = lk + sign*HALF
            Cv = np.array([cx + R_C*math.cos(vAng), cy + R_C*math.sin(vAng)])
            d = np.linalg.norm(Cv-Cl)
            return Cl + R_LOBE*(Cv-Cl)/d
        Tm, Tp = tang(-1), tang(+1)
        a_m = math.atan2(Tm[1]-Cl[1], Tm[0]-Cl[0])
        a_p = math.atan2(Tp[1]-Cl[1], Tp[0]-Cl[0])
        tip = Cl + R_LOBE*np.array([math.cos(lk), math.sin(lk)])
        geos.append((Cl[0],Cl[1],R_LOBE,a_m,a_p,tip))
        vv = lk + HALF
        Cv = np.array([cx + R_C*math.cos(vv), cy + R_C*math.sin(vv)])
        lk1 = lk + DTH
        Cl1 = np.array([cx + R_C*math.cos(lk1), cy + R_C*math.sin(lk1)])
        d1 = np.linalg.norm(Cv-Cl1)
        T1 = Cl1 + R_LOBE*(Cv-Cl1)/d1
        b1 = math.atan2(Tp[1]-Cv[1], Tp[0]-Cv[0])
        b2 = math.atan2(T1[1]-Cv[1], T1[0]-Cv[0])
        vb = Cv - R_VALLEY*np.array([math.cos(vv), math.sin(vv)])
        geos.append((Cv[0],Cv[1],R_VALLEY,b1,b2,vb))
    return geos

def add_arcs(sk, arcs, z):
    def nrm(a): return a%(2*math.pi)
    for (x,y,r,a1,a2,ref) in arcs:
        circle = Part.Circle(App.Vector(x,y,z), App.Vector(0,0,1), r)
        ra = math.atan2(ref[1]-y, ref[0]-x)
        a1n,a2n,ran = nrm(a1),nrm(a2),nrm(ra)
        sweep = nrm(a2n-a1n)
        if nrm(ran-a1n) > sweep:
            a1n,a2n = a2n,a1n
        sk.addGeometry(Part.ArcOfCircle(circle, a1n, a2n), False)

def add_circle(sk, cx, cy, r, z):
    sk.addGeometry(Part.Circle(App.Vector(cx,cy,z), App.Vector(0,0,1), r), False)

def add_polygon(sk, pts, z):
    n=len(pts)
    for i in range(n):
        p1=App.Vector(pts[i][0],pts[i][1],z); p2=App.Vector(pts[(i+1)%n][0],pts[(i+1)%n][1],z)
        sk.addGeometry(Part.LineSegment(p1,p2), False)

# ============ BUILD ============
doc = App.newDocument("answer")
body = doc.addObject('PartDesign::Body','Body')
body.Label = 'SIX_ROTOR_ANNULAR_ASSEMBLY'

def new_sketch(name, z):
    sk = doc.addObject('Sketcher::SketchObject', name)
    body.addObject(sk)
    sk.Placement = App.Placement(App.Vector(0,0,z), App.Rotation())
    return sk

def pad(name, sk, length):
    p = doc.addObject('PartDesign::Pad', name)
    body.addObject(p)
    p.Profile = sk
    p.Length = length
    return p

def pocket(name, sk, length, reversed_=False):
    p = doc.addObject('PartDesign::Pocket', name)
    body.addObject(p)
    p.Profile = sk
    p.Length = length
    p.Reversed = reversed_
    return p

# 1. Base disc Ø108 x 18
sk = new_sketch('SK_BaseDisc', 0.0)
add_circle(sk, 0,0, R_OUT, 0.0)
pad('Pad_BaseDisc', sk, H_DISC)
doc.recompute()

# 2. Hexagonal boss post (z 0 - 19.25)
sk = new_sketch('SK_HexBoss', 0.0)
rv = BOSS_AF/math.sqrt(3)  # circumradius for across-flats AF: AF = sqrt(3)*rv
hexpts = []
for k in range(6):
    a = math.radians(90 + k*60)  # pointy-top (vertex at 90)
    hexpts.append((rv*math.cos(a), rv*math.sin(a)))
add_polygon(sk, hexpts, 0.0)
pad('Pad_HexBoss', sk, BOSS_TOP)
doc.recompute()
print('after boss vol:', body.Shape.Volume)

# 3. Flower pockets: 6 flowers. Central one needs hexagon hole to preserve boss.
#    -> pocket satellite flowers (full) and central flower as (flower - hexagon).
#    Do central separately with hex hole, satellites in one sketch.
sk = new_sketch('SK_FlowerCentral', FLOWER_Z1)
add_arcs(sk, flower_edges(0,0,CENTRAL_PHASE), FLOWER_Z1)
# hexagon hole (same as boss) to preserve the boss post
add_polygon(sk, hexpts, FLOWER_Z1)
pocket('Pocket_FlowerCentral', sk, FLOWER_Z1-FLOWER_Z0)
doc.recompute()
print('after central flower vol:', body.Shape.Volume)

sk = new_sketch('SK_FlowerSats', FLOWER_Z1)
for phi in SAT_ANGLES:
    a = math.radians(phi)
    sx, sy = SAT_PITCH*math.cos(a), SAT_PITCH*math.sin(a)
    add_arcs(sk, flower_edges(sx, sy, phi), FLOWER_Z1)
pocket('Pocket_FlowerSats', sk, FLOWER_Z1-FLOWER_Z0)
doc.recompute()
print('after sat flowers vol:', body.Shape.Volume)

# 4. Teeth: 21 gaps (void) from r=45.5 to 49.5, z 15-18
sk = new_sketch('SK_Teeth', TEETH_Z1)
for k in range(N_TEETH):
    ac = math.radians(TEETH_PHASE + k*360.0/N_TEETH)  # gap center
    halfw = math.radians(TEETH_GAP_DEG/2)
    a1, a2 = ac-halfw, ac+halfw
    # rectangle (annular segment) from r_in to r_out
    pts=[]
    pts.append((TEETH_R_IN*math.cos(a1), TEETH_R_IN*math.sin(a1)))
    pts.append((TEETH_R_OUT*math.cos(a1), TEETH_R_OUT*math.sin(a1)))
    pts.append((TEETH_R_OUT*math.cos(a2), TEETH_R_OUT*math.sin(a2)))
    pts.append((TEETH_R_IN*math.cos(a2), TEETH_R_IN*math.sin(a2)))
    add_polygon(sk, pts, TEETH_Z1)
pocket('Pocket_Teeth', sk, TEETH_Z1-TEETH_Z0)
doc.recompute()
print('after teeth vol:', body.Shape.Volume)

# 5. Top slot (width 6, radial, at math 90), r 45.5-54, z 15-18
sk = new_sketch('SK_Slot', SLOT_Z1)
a = math.radians(SLOT_ANGLE)
# radial slot: from r_in to r_out, width SLOT_W (perpendicular)
ux, uy = math.cos(a), math.sin(a)     # radial dir
vx, vy = -math.sin(a), math.cos(a)    # tangential dir
w2 = SLOT_W/2
pts = [
 (SLOT_R_IN*ux - w2*vx, SLOT_R_IN*uy - w2*vy),
 (SLOT_R_OUT*ux - w2*vx, SLOT_R_OUT*uy - w2*vy),
 (SLOT_R_OUT*ux + w2*vx, SLOT_R_OUT*uy + w2*vy),
 (SLOT_R_IN*ux + w2*vx, SLOT_R_IN*uy + w2*vy),
]
add_polygon(sk, pts, SLOT_Z1)
pocket('Pocket_Slot', sk, SLOT_Z1-SLOT_Z0)
doc.recompute()
print('after slot vol:', body.Shape.Volume)

# Final check
sh = body.Shape
print('valid:', sh.isValid(), 'solids:', len(sh.Solids), 'bbox:', sh.BoundBox)
doc.saveAs('/tmp/proto.FCStd')
print('saved /tmp/proto.FCStd')
