"""Check specification dimensions against measurements from FreeCAD geometry.

Measurements are grouped by diameter (D), radius (R), angle (A), count (C),
length (L), and signed coordinate (X), with a geometric source for each value.
Linear measurements use millimetres; angles use radians.

Pools are built from sketch geometry, feature properties, and B-rep geometry
independently of comparison targets. Each specification value is compared with
the nearest measurement in its pool using the supplied relative tolerance.
Measurements remain available for repeated dimensions. The adjacent spec.json
provides unit metadata; comparison targets come from the spec passed to apply().
"""
from __future__ import annotations

import itertools
import math
import re

from freecad_validator.consistency.compare import (
    as_display_angle,
    make_consistent_finding,
    make_inconsistent_finding,
    make_not_found_finding,
)

_SOLID_OPS = frozenset({
    "PartDesign::Pad",
    "PartDesign::Pocket",
    "PartDesign::Revolution",
    "PartDesign::Groove",
    "PartDesign::Hole",
    "PartDesign::AdditiveLoft",
    "PartDesign::SubtractiveLoft",
    "PartDesign::AdditivePipe",
    "PartDesign::SubtractivePipe",
    "PartDesign::AdditiveHelix",
    "PartDesign::SubtractiveHelix",
})

_TRANSFORM_OPS = frozenset({
    "PartDesign::LinearPattern",
    "PartDesign::PolarPattern",
    "PartDesign::Mirrored",
    "PartDesign::MultiTransform",
})


def _modeling_feature_count(bank) -> int:
    """Count solid modeling operations and pattern or mirror transformations."""
    return sum(
        1 for e in bank.feature_tree if e.type_id in _SOLID_OPS or e.type_id in _TRANSFORM_OPS
    )


def _build_pools(bank):
    pools = {"D": [], "R": [], "A": [], "C": [], "L": [], "X": []}

    def add(kind, value, source):
        value = float(value)
        if not math.isfinite(value) or (kind in ("D", "R", "L") and value <= 0):
            return
        pools[kind].append((value, source))

    for p in bank.sketch_profiles:
        entry_for_polar = next((e for e in bank.feature_tree if e.name == p.name), None)
        radius_counts = {}
        for r in p.circle_radii:
            add("D", 2 * r, f"{p.name}.circle")
            add("R", r, f"{p.name}.circle_radius")
            radius_counts[round(r, 4)] = radius_counts.get(round(r, 4), 0) + 1
        arc_counts = {}
        for r in p.arc_radii:
            add("D", 2 * r, f"{p.name}.arc_as_diameter")
            add("R", r, f"{p.name}.arc_radius")
            arc_counts[round(r, 4)] = arc_counts.get(round(r, 4), 0) + 1
        for n in arc_counts.values():
            if n >= 2:
                add("C", n, f"{p.name}.equal_arc_count")
        for n in radius_counts.values():
            if n >= 2:
                add("C", n, f"{p.name}.equal_circle_count")
        for seg in p.line_segments:
            add("L", seg.length, f"{p.name}.segment")
            # Include the axis components of slanted sketch segments.
            for axis, label in ((0, "run"), (1, "rise")):
                delta = abs(seg.end[axis] - seg.start[axis])
                if delta > 1e-6 and delta < seg.length - 1e-6:
                    add("L", delta, f"{p.name}.segment_{label}")
        # Measure the centre of the sketch's line-segment envelope.
        for axis in (0, 1):
            vals = [c for seg in p.line_segments for c in (seg.start[axis], seg.end[axis])]
            if vals and max(vals) - min(vals) > 1e-6:
                add("X", (max(vals) + min(vals)) / 2.0, f"{p.name}.profile_center_ax{axis}")

        # Measure opening spans between the outer endpoints of two segments
        # meeting at a shared vertex.
        incident: dict = {}
        for seg in p.line_segments:
            for near, far in ((seg.start, seg.end), (seg.end, seg.start)):
                incident.setdefault((round(near[0], 4), round(near[1], 4)), []).append(far)
        for ends in incident.values():
            if len(ends) != 2:
                continue
            a, b_ = ends
            for axis, label in ((0, "ax0"), (1, "ax1")):
                gap = abs(a[axis] - b_[axis])
                if gap > 1e-6:
                    add("L", gap, f"{p.name}.corner_opening_{label}")

        # Measure spans between vertex coordinates symmetric about a sketch axis.
        for axis in (0, 1):
            coords = {
                round(c, 4)
                for seg in p.line_segments
                for c in (seg.start[axis], seg.end[axis])
            }
            mirrored = {-c for c in coords if c < -1e-6}
            for c in sorted(x for x in coords if x > 1e-6):
                if c in mirrored:
                    add("L", 2.0 * c, f"{p.name}.symmetric_span_ax{axis}")
        # Represent sharp corners in line-only profiles with a zero radius.
        # Append directly because add() excludes nonpositive radii.
        if p.line_segments and not (p.arc_radii or p.circle_radii):
            pools["R"].append((0.0, f"{p.name}.sharp_corner"))
        # Record circle and arc centre angles in signed and full-turn form.
        if entry_for_polar is not None:
            for vkey, vec in (entry_for_polar.vectors or {}).items():
                if not vkey.endswith(("CircleCenter", "ArcCenter")):
                    continue
                cx, cy = vec[0], vec[1]
                if math.hypot(cx, cy) < 1e-6:
                    continue
                theta = math.atan2(cy, cx)
                add("A", theta, f"{p.name}.center_polar_angle")
                add("A", theta % (2 * math.pi), f"{p.name}.center_polar_angle")
                # Measure radial distance from the sketch origin.
                polar_r = math.hypot(cx, cy)
                add("L", polar_r, f"{p.name}.center_polar_radius")
        for a in p.constraint_angles:
            add("A", a, f"{p.name}.constraint_angle")
        # Measure corner angles from segment directions and arc tangents.
        vertices = {}
        entry = next((e for e in bank.feature_tree if e.name == p.name), None)
        if entry is not None:
            for gkey, radius in entry.properties.items():
                if not gkey.endswith(".ArcRadius") or radius <= 0:
                    continue
                idx = gkey.split("[", 1)[1].split("]", 1)[0]
                centre = entry.vectors.get(f"Geometry[{idx}].ArcCenter")
                for label in ("ArcStart", "ArcEnd"):
                    pt = entry.vectors.get(f"Geometry[{idx}].{label}")
                    if centre is None or pt is None:
                        continue
                    # Include both tangent directions at the arc endpoint.
                    rx, ry = pt[0] - centre[0], pt[1] - centre[1]
                    vkey = (round(pt[0], 4), round(pt[1], 4))
                    vertices.setdefault(vkey, []).append((-ry, rx))
                    vertices.setdefault(vkey, []).append((ry, -rx))
        for seg in p.line_segments:
            for near, far in ((seg.start, seg.end), (seg.end, seg.start)):
                key = (round(near[0], 4), round(near[1], 4))
                vertices.setdefault(key, []).append((far[0] - near[0], far[1] - near[1]))
        if entry is not None:
            for gkey, radius in entry.properties.items():
                if not gkey.endswith(".ArcRadius") or radius <= 0:
                    continue
                idx = gkey.split("[", 1)[1].split("]", 1)[0]
                ends = [entry.vectors.get(f"Geometry[{idx}].{lab}")
                        for lab in ("ArcStart", "ArcEnd")]
                if any(e is None for e in ends):
                    continue
                touching = []
                for end_pt in ends:
                    for seg in p.line_segments:
                        for near, far in ((seg.start, seg.end), (seg.end, seg.start)):
                            if abs(near[0] - end_pt[0]) < 1e-4 and abs(near[1] - end_pt[1]) < 1e-4:
                                touching.append((far[0] - near[0], far[1] - near[1]))
                for i in range(len(touching)):
                    for j in range(i + 1, len(touching)):
                        (ax_, ay), (bx_, by) = touching[i], touching[j]
                        na, nb = math.hypot(ax_, ay), math.hypot(bx_, by)
                        if na <= 0 or nb <= 0:
                            continue
                        cos = max(-1.0, min(1.0, (ax_ * bx_ + ay * by) / (na * nb)))
                        across = math.acos(cos)
                        for variant in (across, math.pi - across,
                                        2 * math.pi - across, math.pi + across):
                            add("A", variant, f"{p.name}.angle_across_fillet")

        for (vx, vy), dirs in vertices.items():
            for i in range(len(dirs)):
                for j in range(i + 1, len(dirs)):
                    (ax, ay), (bx, by) = dirs[i], dirs[j]
                    na, nb = math.hypot(ax, ay), math.hypot(bx, by)
                    if na <= 0 or nb <= 0:
                        continue
                    cos = max(-1.0, min(1.0, (ax * bx + ay * by) / (na * nb)))
                    interior = math.acos(cos)
                    # Include supplementary and reflex forms of the corner angle.
                    at = f"@({vx},{vy})"
                    add("A", interior, f"{p.name}.corner{at}")
                    add("A", 2 * math.pi - interior, f"{p.name}.corner_reflex{at}")
                    add("A", math.pi - interior, f"{p.name}.corner_supplement{at}")
                    add("A", math.pi + interior, f"{p.name}.corner_supplement_reflex{at}")
        # Measure coordinate offsets from profile extremes and consecutive
        # coordinate spacings along each sketch axis.
        entry_geo = next((e for e in bank.feature_tree if e.name == p.name), None)
        for axis in (0, 1):
            coords = set()
            for seg in p.line_segments:
                coords.add(round(seg.start[axis], 4))
                coords.add(round(seg.end[axis], 4))
            if entry_geo is not None:
                for gkey, radius in entry_geo.properties.items():
                    label = ".CircleRadius" if gkey.endswith(".CircleRadius") else (
                        ".ArcRadius" if gkey.endswith(".ArcRadius") else None)
                    if label is None or radius <= 0:
                        continue
                    idx = gkey.split("[", 1)[1].split("]", 1)[0]
                    name = "CircleCenter" if label == ".CircleRadius" else "ArcCenter"
                    centre = entry_geo.vectors.get(f"Geometry[{idx}].{name}")
                    if centre is None:
                        continue
                    coords.add(round(centre[axis], 4))
            ordered = sorted(coords)
            if len(ordered) < 2:
                continue
            first, last = ordered[0], ordered[-1]
            for value in ordered:
                add("L", value - first, f"{p.name}.ax{axis}_from_min")
                add("L", last - value, f"{p.name}.ax{axis}_from_max")
            for i in range(len(ordered) - 1):
                add("L", ordered[i + 1] - ordered[i], f"{p.name}.ax{axis}_step")

        # Group segments and arcs by shared endpoints into connected regions.
        elements = []
        for seg in p.line_segments:
            elements.append((
                (seg.start[0], seg.start[1]), (seg.end[0], seg.end[1]),
                [seg.start[0], seg.end[0]], [seg.start[1], seg.end[1]],
            ))
        if entry is not None:
            for gkey, radius in entry.properties.items():
                if not gkey.endswith(".ArcRadius") or radius <= 0:
                    continue
                idx = gkey.split("[", 1)[1].split("]", 1)[0]
                a0 = entry.vectors.get(f"Geometry[{idx}].ArcStart")
                a1 = entry.vectors.get(f"Geometry[{idx}].ArcEnd")
                ac = entry.vectors.get(f"Geometry[{idx}].ArcCenter")
                if a0 is None or a1 is None or ac is None:
                    continue
                elements.append((
                    (a0[0], a0[1]), (a1[0], a1[1]),
                    [a0[0], a1[0], ac[0] - radius, ac[0] + radius],
                    [a0[1], a1[1], ac[1] - radius, ac[1] + radius],
                ))
        parent = list(range(len(elements)))

        def _root(a):
            while parent[a] != a:
                parent[a] = parent[parent[a]]
                a = parent[a]
            return a

        at_point: dict = {}
        for idx, el in enumerate(elements):
            for pt in (el[0], el[1]):
                at_point.setdefault((round(pt[0], 3), round(pt[1], 3)), []).append(idx)
        for members in at_point.values():
            for other in members[1:]:
                parent[_root(other)] = _root(members[0])
        regions: dict = {}
        for idx in range(len(elements)):
            regions.setdefault(_root(idx), []).append(idx)
        # Group region centres into rows or columns for lattice counts.
        def _lanes(values, tol):
            lanes: list = []
            for v in sorted(values):
                if lanes and v - lanes[-1][-1] <= tol:
                    lanes[-1].append(v)
                else:
                    lanes.append([v])
            return lanes

        # Use the most frequent region edge count to identify repeated cells.
        sides: dict = {}
        for members in regions.values():
            if len(members) >= 3:
                sides[len(members)] = sides.get(len(members), 0) + 1
        cell_sides = max(sides, key=lambda k: (sides[k], -k)) if sides else None
        centres = []
        for members in regions.values():
            if len(members) != cell_sides:
                continue
            centre = []
            for axis in (0, 1):
                vals = [c for i in members for c in elements[i][2 + axis]]
                centre.append((max(vals) + min(vals)) / 2.0)
            centres.append(centre)
        if len(centres) >= 4:
            for axis, label in ((1, "row"), (0, "column")):
                coords = [c[axis] for c in centres]
                span = max(coords) - min(coords)
                if span <= 1e-9:
                    continue
                lanes = _lanes(coords, span * 1e-3)
                add("C", len(lanes), f"{p.name}.{label}_count")
                sizes = sorted({len(g) for g in lanes})
                add("C", max(sizes), f"{p.name}.max_per_{label}")
                if len(sizes) > 1:
                    add("C", min(sizes), f"{p.name}.min_per_{label}")

        # Retain signed vertex and centre coordinates in the sketch frame.
        for seg in p.line_segments:
            for pt in (seg.start, seg.end):
                add("X", pt[0], f"{p.name}.vertex_x")
                add("X", pt[1], f"{p.name}.vertex_y")
        if entry is not None:
            for gkey, radius in entry.properties.items():
                is_arc = gkey.endswith(".ArcRadius")
                if not (is_arc or gkey.endswith(".CircleRadius")) or radius <= 0:
                    continue
                idx = gkey.split("[", 1)[1].split("]", 1)[0]
                name = "ArcCenter" if is_arc else "CircleCenter"
                centre = entry.vectors.get(f"Geometry[{idx}].{name}")
                if centre is None:
                    continue
                add("X", centre[0], f"{p.name}.centre_x")
                add("X", centre[1], f"{p.name}.centre_y")
                if not is_arc:
                    continue
                for label in ("ArcStart", "ArcEnd"):
                    pt = entry.vectors.get(f"Geometry[{idx}].{label}")
                    if pt is None:
                        continue
                    add("X", pt[0], f"{p.name}.arc_end_x")
                    add("X", pt[1], f"{p.name}.arc_end_y")
                    # Measure endpoint angles relative to the arc's centre.
                    theta = math.atan2(pt[1] - centre[1], pt[0] - centre[0])
                    add("A", theta, f"{p.name}.arc_endpoint_angle")
                    add("A", theta % (2 * math.pi), f"{p.name}.arc_endpoint_angle")

        # Measure perpendicular spacing between parallel supporting lines.
        # Merge collinear segments before comparing offsets.
        lines = {}
        for seg in p.line_segments:
            dx, dy = seg.end[0] - seg.start[0], seg.end[1] - seg.start[1]
            norm = math.hypot(dx, dy)
            if norm < 1e-9:
                continue
            ux, uy = dx / norm, dy / norm
            if (ux, uy) < (-ux, -uy):        # Canonical direction.
                ux, uy = -ux, -uy
            offset = seg.start[0] * (-uy) + seg.start[1] * ux
            lines[(round(ux, 4), round(uy, 4), round(offset, 4))] = None
        keys = list(lines)
        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                ux, uy, oi = keys[i]
                vx, vy, oj = keys[j]
                if abs(ux * vy - uy * vx) > 1e-3:
                    continue
                across = abs(oi - oj)
                if across > 1e-6:
                    add("L", across, f"{p.name}.parallel_edge_width")
        length_hist: dict[float, int] = {}
        for seg in p.line_segments:
            key = round(seg.length, 3)
            length_hist[key] = length_hist.get(key, 0) + 1
        for n in length_hist.values():
            if n >= 2:
                add("C", n, f"{p.name}.equal_segment_count")
    for e in bank.feature_tree:
        length = float(e.properties.get("Length", 0.0))
        if (e.type_id in _SOLID_OPS or e.type_id in _TRANSFORM_OPS) and length > 0:
            add("L", length, f"{e.name}.Length")
        if e.type_id == "Sketcher::SketchObject":
            groups: dict[float, list[tuple[float, float]]] = {}
            for key, vec in e.vectors.items():
                if "CircleCenter" not in key:
                    continue
                idx = key.split("[", 1)[1].split("]", 1)[0]
                r = e.properties.get(f"Geometry[{idx}].CircleRadius")
                if r:
                    groups.setdefault(round(r, 4), []).append((vec[0], vec[1]))
            for r, centers in groups.items():
                if len(centers) < 3:
                    continue
                add("C", len(centers), f"{e.name}.r{r}_circle_count")
                for axis in (0, 1):
                    coords = sorted({round(c[axis], 3) for c in centers})
                    if len(coords) >= 2:
                        add("C", len(coords), f"{e.name}.r{r}_axis{axis}_positions")
                        deltas = {round(coords[i + 1] - coords[i], 3) for i in range(len(coords) - 1)}
                        for dv in deltas:
                            add("L", dv, f"{e.name}.r{r}_axis{axis}_pitch")
        for prop in ("Radius", "Radius1", "Radius2"):
            v = e.properties.get(prop)
            if v:
                add("R", v, f"{e.name}.{prop}")
                add("D", 2 * v, f"{e.name}.{prop}x2")
        v = e.properties.get("Diameter")
        if v:
            add("D", v, f"{e.name}.Diameter")
            add("R", v / 2.0, f"{e.name}.Diameter/2")
        for prop in ("Angle", "Angle1", "Angle2"):
            v = e.properties.get(prop)
            if v:
                add("A", v, f"{e.name}.{prop}")
        occ = e.properties.get("Occurrences")
        if occ:
            add("C", occ, f"{e.name}.Occurrences")
        if e.type_id == "Sketcher::SketchObject":
            pos = e.vectors.get("Placement.Position")
            if pos is not None:
                for axis, comp in zip("xyz", pos):
                    if abs(comp) > 1e-9:
                        add("L", abs(comp), f"{e.name}.plane_{axis}")

    for e in bank.feature_tree:
        for key, radius in e.properties.items():
            if not key.endswith(".ArcRadius") or radius <= 0:
                continue
            idx = key.split("[", 1)[1].split("]", 1)[0]
            centre = e.vectors.get(f"Geometry[{idx}].ArcCenter")
            start = e.vectors.get(f"Geometry[{idx}].ArcStart")
            end = e.vectors.get(f"Geometry[{idx}].ArcEnd")
            if centre is None or start is None or end is None:
                continue
            a0 = math.atan2(start[1] - centre[1], start[0] - centre[0])
            a1 = math.atan2(end[1] - centre[1], end[0] - centre[0])
            sweep = (a1 - a0) % (2 * math.pi)
            add("A", sweep, f"{e.name}.arc_sweep")
            add("A", 2 * math.pi - sweep, f"{e.name}.arc_sweep_reflex")

    # Aggregate cylinder counts across clusters with the same radius.
    radius_totals: dict[float, int] = {}
    for c in bank.cylinder_clusters:
        radius_totals[round(c.radius, 3)] = radius_totals.get(round(c.radius, 3), 0) + c.count
    for radius, total in radius_totals.items():
        add("C", total, f"cyl_r{radius}.total_count")
    grid_total = sum(g.count for g in bank.grids)
    if grid_total:
        add("C", grid_total, "grids.total_count")

    for c in bank.cylinder_clusters:
        add("D", 2 * c.radius, f"{c.id}.cyl_diameter")
        add("R", c.radius, f"{c.id}.cyl_radius")
        add("C", c.count, f"{c.id}.count")
        add("L", c.axial_extent, f"{c.id}.axial_extent")
    # Include plane-pair offsets when both faces have positive area.
    for pp in bank.plane_pairs:
        if pp.min_area > 0:
            add("L", pp.offset, f"{pp.id}.offset")
    for g in bank.grids:
        add("C", g.count, f"{g.source}.count")
        add("C", g.rows, f"{g.source}.rows")
        add("C", g.columns, f"{g.source}.columns")
        for sp in (g.spacing_rows, g.spacing_cols):
            if sp > 0:
                add("L", sp, f"{g.source}.pitch")
    for cp in bank.circular_patterns:
        add("C", cp.count, f"{cp.source}.n_fold")
        add("R", cp.pattern_radius, f"{cp.source}.pattern_radius")
        add("D", 2 * cp.pattern_radius, f"{cp.source}.pattern_diameter")
    for cs in bank.conic_surfaces:
        included = 2.0 * abs(cs.semi_angle)
        add("A", included, "cone.2x_semi_angle")
        add("A", 2 * math.pi - included, f"{cs.id}.included_angle_reflex")
    for m in bank.globals.values():
        if isinstance(m.value, (int, float)) and m.unit == "mm":
            add("L", m.value, f"global.{m.id}")
    return pools


# Coordinate measurements retain zero and negative values.
_COORDINATE = re.compile(
    r"(?:^|_)(?:x|y|z)(?:\d+)?(?:_|$)|center_[xyz]|centre_[xyz]|"
    r"[xyz]_(?:min|max|position|offset|coord)|"
    # Recognize horizontal and vertical coordinates in face-local frames.
    r"(?:^|_)(?:horizontal|vertical)_(?:offset|position|min|max|coord)(?:_|$)"
)


def _classify(key: str) -> str:
    tokens = set(key.split("_"))
    # Count tokens take precedence over dimension tokens.
    if tokens & {"count", "num", "number", "elements", "quantity"} or "num_element" in key:
        return "C"
    # Match complete angle tokens to avoid substrings such as 'angled'.
    if tokens & {"angle", "angles"}:
        return "A"
    # Dimension suffixes take precedence over axis tokens.
    # An arc span denotes an angle.
    if "arc" in tokens and re.sub(r"_\d+$", "", key).endswith(("_span", "_spans")):
        return "A"
    if re.sub(r"_\d+$", "", key).endswith(
        (
            "_length",
            "_width",
            "_height",
            "_depth",
            "_thickness",
            "_span",
            "_gap",
            "_spacing",
            "_pitch",
            "_clearance",
        )
    ):
        return "L"
    if _COORDINATE.search(key):
        return "X"
    if "diameter" in key or "diameters" in key:
        return "D"
    if "radius" in key or "radii" in key:
        return "R"
    return "L"


def _circle_patterns(centres):
    """Yield the radius, count, and centre of regular circular point arrays.

    Propose centres from point-pair midpoints, then require at least four
    points on the same circle with equal angular gaps around a full turn.
    """
    centres = sorted({tuple(point[:2]) for point in centres})
    found = set()
    for a, b in itertools.combinations(centres, 2):
        cx, cy = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        radius = math.hypot(a[0] - cx, a[1] - cy)
        if radius < 1e-9:
            continue
        signature = (round(cx, 6), round(cy, 6), round(radius, 6))
        if signature in found:
            continue
        angles = sorted(math.atan2(y - cy, x - cx) % (2 * math.pi)
                        for x, y in centres
                        if abs(math.hypot(x - cx, y - cy) - radius)
                        <= 1e-6 * max(1.0, radius))
        if len(angles) < 4:
            continue
        pitch = 2 * math.pi / len(angles)
        gaps = [(angles[(i + 1) % len(angles)] - angle) % (2 * math.pi)
                for i, angle in enumerate(angles)]
        if all(abs(gap - pitch) <= 1e-5 for gap in gaps):
            found.add(signature)
            yield radius, len(angles), (cx, cy)


def _aligned_point_spans(points, source):
    """Yield distances between neighbouring points on axis-aligned lines.

    The caller supplies points from one wire or geometric group. Rounding
    groups coincident lines; distances use the original point coordinates.
    """
    points = list(points)
    for axis in range(3):
        others = [k for k in range(3) if k != axis]
        lines = {}
        for point, label in points:
            key = tuple(round(point[k], 6) for k in others)
            lines.setdefault(key, []).append((point, label))
        for entries in lines.values():
            entries.sort(key=lambda item: item[0][axis])
            for (a, a_label), (b, b_label) in zip(entries, entries[1:]):
                if any(abs(a[k] - b[k]) > 1e-6 for k in others):
                    continue
                distance = b[axis] - a[axis]
                if distance > 1e-6:
                    yield distance, f"{source}.{a_label}_to_{b_label}.aligned_{'xyz'[axis]}"


def _fillet_corners(wire):
    """Yield arc indices and theoretical corners of tangent line-arc-line chains.

    The supporting lines must intersect beyond their trimmed endpoints
    toward the corner removed by the fillet.
    """
    import Part

    edges = wire.OrderedEdges
    for i, arc in enumerate(edges):
        if arc.Degenerated or not isinstance(arc.Curve, Part.Circle):
            continue
        if not wire.isClosed() and i in (0, len(edges) - 1):
            continue
        if not 1e-7 < arc.LastParameter - arc.FirstParameter < math.pi + 1e-7:
            continue
        neighbours = [edges[(i - 1) % len(edges)], edges[(i + 1) % len(edges)]]
        if not all(not edge.Degenerated and isinstance(edge.Curve, Part.Line) for edge in neighbours):
            continue
        joints = []
        for line in neighbours:
            for near, far in ((line.FirstParameter, line.LastParameter),
                              (line.LastParameter, line.FirstParameter)):
                p = line.valueAt(near)
                direction = line.valueAt(far) - p
                if direction.Length < 1e-9:
                    continue
                direction.normalize()
                for parameter in (arc.FirstParameter, arc.LastParameter):
                    if (p - arc.valueAt(parameter)).Length > 1e-6:
                        continue
                    tangent = arc.tangentAt(parameter)
                    if direction.cross(tangent).Length < 1e-6:
                        joints.append((p, direction))
        if len(joints) != 2:
            continue
        (p, u), (q, v) = joints
        if (q - p).Length < 1e-6:
            continue
        dot = u.dot(v)
        denominator = 1 - dot * dot
        if denominator < 1e-10:
            continue
        w = q - p
        s = (w.dot(u) - dot * w.dot(v)) / denominator
        t = (dot * w.dot(u) - w.dot(v)) / denominator
        corner = p + u * s
        if s > 1e-6 or t > 1e-6 or (corner - (q + v * t)).Length > 1e-6:
            continue
        yield i, corner


def _ellipse_extrema(edge):
    """Yield axis extrema within a trimmed ellipse, including angle wraparound."""
    import Part

    # Degenerate edges at surface poles have no 3D curve.
    # Their vertices are measured separately.
    if edge.Degenerated:
        return
    curve = edge.Curve
    if not isinstance(curve, Part.Ellipse):
        return
    a = curve.XAxis * curve.MajorRadius
    b = curve.YAxis * curve.MinorRadius
    first, last = edge.FirstParameter, edge.LastParameter
    for axis in range(3):
        if math.hypot(a[axis], b[axis]) < 1e-9:
            continue
        # Set the axis derivative of C + a*cos(u) + b*sin(u) to zero.
        root = math.atan2(b[axis], a[axis])
        for branch in (root, root + math.pi):
            period = math.ceil((first - branch) / (2 * math.pi))
            parameter = branch + period * 2 * math.pi
            if first + 1e-9 < parameter < last - 1e-9:
                yield axis, parameter, edge.valueAt(parameter)


def _base_pad_cap_datums(owner, shape, final_datums):
    """Return the base pad shape and its partially surviving end-face datums.

    Each finite cap must share a nonzero area with a coplanar final face
    in the same body. Its original extent defines the datum after cuts.
    """
    from freecad_validator._freecad_loader import import_freecad
    import Part

    FreeCAD = import_freecad()
    if len(shape.Solids) != 1:
        return None, []
    base = next((obj for obj in getattr(owner, "Group", ())
                 if hasattr(obj, "Shape") and len(obj.Shape.Solids)), None)
    if (base is None or base.TypeId != "PartDesign::Pad"
            or len(base.Shape.Solids) != 1
            or not getattr(base, "AlongSketchNormal", False)):
        return None, []
    profile = getattr(base, "Profile", None)
    if not profile or profile[0] is None:
        return None, []
    normal = profile[0].getGlobalPlacement().Rotation.multVec(FreeCAD.Vector(0, 0, 1))
    axis = max(range(3), key=lambda k: abs(normal[k]))
    if (abs(normal[axis]) < 1 - 1e-10
            or any(abs(normal[k]) > 1e-9 for k in range(3) if k != axis)):
        return None, []
    base_shape = base.Shape.copy()
    base_shape.Placement = base.getGlobalPlacement()
    bounds = base_shape.BoundBox
    levels = [getattr(bounds, "XYZ"[axis] + suffix) for suffix in ("Min", "Max")]
    datums = []
    for index, cap in enumerate(base_shape.Faces):
        surface = cap.Surface
        if not isinstance(surface, Part.Plane):
            continue
        if (abs(surface.Axis[axis]) < 1 - 1e-10
                or any(abs(surface.Axis[k]) > 1e-9 for k in range(3) if k != axis)):
            continue
        level = surface.Position[axis]
        if not any(abs(level - end) < 1e-6 for end in levels):
            continue
        for final_axis, final_level, face, ref in final_datums:
            if final_axis != axis or abs(final_level - level) > 1e-6:
                continue
            # Require a shared area in addition to coplanarity.
            if cap.common(face).Area > 1e-8:
                datums.append((axis, level, cap,
                               f"{base.Name}.Face{index + 1}.base_cap_surviving_as_{ref}"))
                break
    return base_shape, datums


def _bspline_extrema(edge):
    """Yield non-vertex axis extrema on a finite B-spline edge.

    For each axis, place probe faces beyond the bounding box, covering the
    curve's projection. OCC closest-point queries locate the extrema on the
    curve; the bounding box determines probe placement only.
    """
    from freecad_validator._freecad_loader import import_freecad
    import Part

    if edge.Degenerated or not isinstance(edge.Curve, Part.BSplineCurve):
        return
    FreeCAD = import_freecad()
    box = edge.BoundBox
    lo = [box.XMin, box.YMin, box.ZMin]
    hi = [box.XMax, box.YMax, box.ZMax]
    margin = max(1.0, box.DiagonalLength * 1e-6)
    for axis in range(3):
        if hi[axis] - lo[axis] < 1e-7:
            continue
        a, b = [k for k in range(3) if k != axis]
        for side, level in (("min", lo[axis] - margin), ("max", hi[axis] + margin)):
            corners = []
            for u, v in ((lo[a] - margin, lo[b] - margin),
                         (hi[a] + margin, lo[b] - margin),
                         (hi[a] + margin, hi[b] + margin),
                         (lo[a] - margin, hi[b] + margin)):
                p = FreeCAD.Vector()
                p[axis], p[a], p[b] = level, u, v
                corners.append(p)
            plane = Part.Face(Part.makePolygon(corners + [corners[0]]))
            _, pairs, _ = edge.distToShape(plane)
            if pairs:
                point = pairs[0][0]
                if all((point - vertex.Point).Length > 1e-7 for vertex in edge.Vertexes):
                    yield axis, side, point


def _radial_pocket_floor_offsets(owner, shape):
    """Yield radial pocket-floor offsets from the axis of an ancestor base pad.

    Match each circular floor face to a pocket profile and its computed end
    position. The pocket direction must be perpendicular to the base axis.
    """
    import Part

    objects = getattr(owner, "Group", ())
    base = next((obj for obj in objects if hasattr(obj, "Shape") and len(obj.Shape.Solids)), None)
    if (base is None or base.TypeId != "PartDesign::Pad"
            or not getattr(base, "AlongSketchNormal", False)):
        return
    link = getattr(base, "Profile", None)
    if not link or link[0] is None or link[0].TypeId != "Sketcher::SketchObject":
        return
    profile = link[0]
    geometry = [g for i, g in enumerate(profile.Geometry) if not profile.getConstruction(i)]
    if len(geometry) != 1 or not isinstance(geometry[0], Part.Circle):
        return
    placement = profile.getGlobalPlacement()
    datum = placement.multVec(geometry[0].Center)
    datum_axis = placement.Rotation.multVec(geometry[0].Axis)
    caps = []
    for index, face in enumerate(shape.Faces):
        if (not isinstance(face.Surface, Part.Plane) or len(face.Wires) != 1
                or len(face.OuterWire.Edges) != 1):
            continue
        edge = face.OuterWire.Edges[0]
        if (not edge.Degenerated and isinstance(edge.Curve, Part.Circle)
                and abs(edge.LastParameter - edge.FirstParameter - 2 * math.pi) < 1e-6):
            caps.append((index, edge.Curve))
    for pocket in objects:
        if (pocket.TypeId != "PartDesign::Pocket" or getattr(pocket, "Type", None) != "Length"
                or getattr(pocket, "SideType", None) != "One side"
                or not getattr(pocket, "AlongSketchNormal", False)):
            continue
        ancestor, visited = getattr(pocket, "BaseFeature", None), set()
        while ancestor is not None and ancestor != base and ancestor.Name not in visited:
            visited.add(ancestor.Name)
            ancestor = getattr(ancestor, "BaseFeature", None)
        if ancestor != base:
            continue
        link = getattr(pocket, "Profile", None)
        if not link or link[0] is None or link[0].TypeId != "Sketcher::SketchObject":
            continue
        sketch = link[0]
        placement = sketch.getGlobalPlacement()
        for index, circle in enumerate(sketch.Geometry):
            if sketch.getConstruction(index) or not isinstance(circle, Part.Circle):
                continue
            normal = placement.Rotation.multVec(circle.Axis)
            if abs(normal.dot(datum_axis)) > 1e-9:
                continue
            start = placement.multVec(circle.Center)
            end = start + normal * (pocket.Length.Value * (1 if pocket.Reversed else -1))
            for face_index, cap in caps:
                if ((cap.Center - end).Length > 1e-6 or abs(cap.Radius - circle.Radius) > 1e-6
                        or abs(abs(cap.Axis.dot(normal)) - 1) > 1e-9):
                    continue
                yield abs((cap.Center - datum).dot(normal)), (
                    f"{pocket.Name}.Geometry[{index}].floor@candidate.Face{face_index + 1}"
                    f".projected_from_{base.Name}.profile_axis")


def _build_shape_pools(fcstd_path):
    """Build measurement pools from FreeCAD shapes and sketches.

    Read trimmed curves, finite faces, and feature geometry directly from the
    document, applying global placements for world-coordinate measurements.
    """
    from freecad_validator._freecad_loader import import_freecad
    from freecad_validator.measurement.common import pick_representative_shape

    FreeCAD = import_freecad()
    import Part

    pools = {kind: [] for kind in ("D", "R", "A", "C", "L", "X")}

    def add(kind, value, source):
        value = float(value)
        if math.isfinite(value) and (kind not in ("D", "R", "L") or value > 1e-9):
            pools[kind].append((value, source))

    def extents(box, source):
        for axis in "XYZ":
            add("L", getattr(box, axis + "Length"), f"{source}.extent_{axis.lower()}")

    def line_inclinations(start, end, source):
        # Measure axis inclinations in the principal coordinate planes.
        delta = tuple(end[i] - start[i] for i in range(3))
        for axes, label in (((0, 1), "xy"), ((0, 2), "xz"), ((1, 2), "yz")):
            a, b = (delta[i] for i in axes)
            if math.hypot(a, b) < 1e-9:
                continue
            for x, y, datum in ((a, b, axes[0]), (b, a, axes[1])):
                angle = math.atan2(abs(y), abs(x))
                for value in (angle, math.pi - angle, math.pi + angle,
                              2 * math.pi - angle):
                    add("A", value, f"{source}.inclination_{label}_axis{datum}")

    def profile_wall_angles(wire, source):
        # Measure walls separated by one base edge in the same wire.
        # Also traverse with tangent fillets removed to recover trimmed corners.
        raw = list(enumerate(wire.OrderedEdges))
        fillets = {i for i, _ in _fillet_corners(wire)}
        traversals = [(raw, "")]
        if fillets:
            traversals.append(([item for item in raw if item[0] not in fillets],
                               "_after_tangent_fillets"))
        for edges, suffix in traversals:
            n = len(edges)
            for i in range(n):
                j = (i + 2) % n
                if i == j or (not wire.isClosed() and i + 2 >= n):
                    continue
                a, b = edges[i][1], edges[j][1]
                if (a.Degenerated or b.Degenerated
                        or not isinstance(a.Curve, Part.Line) or not isinstance(b.Curve, Part.Line)):
                    continue
                u = a.tangentAt(a.FirstParameter)
                v = b.tangentAt(b.FirstParameter)
                angle = math.acos(max(-1.0, min(1.0, u.dot(v))))
                for value in (angle, math.pi - angle, math.pi + angle,
                              2 * math.pi - angle):
                    add("A", value, f"{source}.walls_{edges[i][0]}_{edges[j][0]}{suffix}")

    def wire_spans(wire, source):
        points = [(vertex.Point, f"Vertex{i + 1}") for i, vertex in enumerate(wire.Vertexes)]
        for value, ref in _aligned_point_spans(points, source):
            add("L", value, ref)
        corners = list(_fillet_corners(wire))
        if corners:
            # Replace fillet tangent points with theoretical corners when
            # measuring the unfilleted outline.
            trimmed = [vertex.Point for index, _ in corners
                       for vertex in wire.OrderedEdges[index].Vertexes]
            outline = [(p, label) for p, label in points
                       if all((p - joint).Length > 1e-6 for joint in trimmed)]
            outline.extend((point, f"fillet{index}_intersection") for index, point in corners)
            for value, ref in _aligned_point_spans(outline, source + ".unfilleted_outline"):
                add("L", value, ref)

    def corner_angles(edges, source):
        # Measure angles at shared vertices in 3D and principal projections.
        incident = {}
        for i, edge in enumerate(edges):
            if edge.Degenerated:
                continue
            for parameter, sense in ((edge.FirstParameter, 1), (edge.LastParameter, -1)):
                point = edge.valueAt(parameter)
                tangent = edge.tangentAt(parameter) * sense
                key = tuple(round(c, 6) for c in point)
                incident.setdefault(key, []).append((i, tuple(tangent)))
        for vertex, entries in incident.items():
            for (i, a), (j, b) in itertools.combinations(entries, 2):
                if i == j:
                    continue
                for axes, label in (((0, 1, 2), "3d"), ((0, 1), "xy"),
                                    ((0, 2), "xz"), ((1, 2), "yz")):
                    na = math.sqrt(sum(a[k] ** 2 for k in axes))
                    nb = math.sqrt(sum(b[k] ** 2 for k in axes))
                    if na < 1e-9 or nb < 1e-9:
                        continue
                    cosine = sum(a[k] * b[k] for k in axes) / (na * nb)
                    angle = math.acos(max(-1.0, min(1.0, cosine)))
                    for value in (angle, math.pi - angle, math.pi + angle,
                                  2 * math.pi - angle):
                        add("A", value, f"{source}.corner_{label}@{vertex}.edges_{i}_{j}")

    doc = FreeCAD.openDocument(str(fcstd_path))
    try:
        doc.recompute()
        shape, owner = pick_representative_shape(doc)
        if shape is None:
            return pools
        shape = shape.copy()
        shape.Placement = owner.getGlobalPlacement()
        box = shape.BoundBox
        extents(box, "candidate")
        lo = (box.XMin, box.YMin, box.ZMin)
        hi = (box.XMax, box.YMax, box.ZMax)

        # Use axis-aligned planar faces as normal-distance datums.
        # A point's perpendicular projection must lie within the trimmed face.
        datum_faces = []
        for index, face in enumerate(shape.Faces):
            if not isinstance(face.Surface, Part.Plane):
                continue
            for axis in range(3):
                if (abs(face.Surface.Axis[axis]) > 1 - 1e-10
                        and all(abs(face.Surface.Axis[k]) < 1e-9 for k in range(3) if k != axis)):
                    datum_faces.append((axis, face.Surface.Position[axis], face,
                                        f"candidate.Face{index + 1}"))

        def inside_box(point, bounds):
            return all(getattr(bounds, name + "Min") - 1e-6 <= point[k]
                       <= getattr(bounds, name + "Max") + 1e-6
                       for k, name in enumerate("XYZ"))

        def vertex_to_faces(point, source, faces=datum_faces, axis_filter=None):
            seen = set()
            for axis, coordinate, face, ref in faces:
                if axis_filter is not None and axis != axis_filter:
                    continue
                key = (axis, round(coordinate, 6))
                distance = abs(point[axis] - coordinate)
                if key in seen or distance < 1e-6:
                    continue
                foot = FreeCAD.Vector(point)
                foot[axis] = coordinate
                if not inside_box(foot, face.BoundBox):
                    continue
                if face.distToShape(Part.Vertex(foot))[0] > 1e-6:
                    continue
                seen.add(key)
                add("L", distance, f"{source}.normal_to_{ref}")

        def centre_to_bounds(point, source):
            for axis in range(3):
                add("X", point[axis], f"{source}.world_{'xyz'[axis]}")
                # Measure offsets to bounding planes only within the axis bounds.
                if lo[axis] - 1e-7 <= point[axis] <= hi[axis] + 1e-7:
                    add("L", point[axis] - lo[axis], f"{source}.to_min_{'xyz'[axis]}")
                    add("L", hi[axis] - point[axis], f"{source}.to_max_{'xyz'[axis]}")

        for index, vertex in enumerate(shape.Vertexes):
            source = f"candidate.Vertex{index + 1}"
            centre_to_bounds(vertex.Point, source)
            vertex_to_faces(vertex.Point, source)

        ellipse_points = [
            (axis, point, f"candidate.Edge{index + 1}.ellipse_extremum_{'xyz'[axis]}@{parameter:.12g}")
            for index, edge in enumerate(shape.Edges)
            for axis, parameter, point in _ellipse_extrema(edge)
        ]
        if ellipse_points:
            base_shape, base_datums = _base_pad_cap_datums(owner, shape, datum_faces)
            for axis, point, source in ellipse_points:
                # Measure offsets along the axis on which the point is extremal.
                add("L", point[axis] - lo[axis], source + f".to_min_{'xyz'[axis]}")
                add("L", hi[axis] - point[axis], source + f".to_max_{'xyz'[axis]}")
                vertex_to_faces(point, source, axis_filter=axis)
                if (base_datums and base_shape.distToShape(Part.Vertex(point))[0] <= 1e-6):
                    vertex_to_faces(point, source, base_datums, axis_filter=axis)

        for index, edge in enumerate(shape.Edges):
            for axis, side, point in _bspline_extrema(edge):
                source = f"candidate.Edge{index + 1}.bspline_{side}_{'xyz'[axis]}"
                add("L", point[axis] - lo[axis], source + f".to_min_{'xyz'[axis]}")
                add("L", hi[axis] - point[axis], source + f".to_max_{'xyz'[axis]}")
                vertex_to_faces(point, source, axis_filter=axis)
        for value, source in _radial_pocket_floor_offsets(owner, shape):
            add("L", value, source)

        final_circles = {}
        for index, edge in enumerate(shape.Edges):
            if edge.Degenerated:
                continue
            source = f"candidate.Edge{index + 1}"
            curve = edge.Curve
            if isinstance(curve, Part.Line):
                add("L", edge.Length, source + ".length")
                start = edge.valueAt(edge.FirstParameter)
                end = edge.valueAt(edge.LastParameter)
                line_inclinations(start, end, source)
                for axis in range(3):
                    add("L", abs(end[axis] - start[axis]), source + f".span_{'xyz'[axis]}")
            elif isinstance(curve, Part.Circle):
                add("R", curve.Radius, source + ".radius")
                add("D", 2 * curve.Radius, source + ".diameter")
                centre_to_bounds(curve.Center, source + ".circle_centre")
                # Group coplanar full circles of equal radius for centre spacing.
                if abs(edge.LastParameter - edge.FirstParameter - 2 * math.pi) < 1e-6:
                    normal = tuple(curve.Axis)
                    # Canonicalize the normal sign using its dominant component
                    # to avoid instability in near-zero components.
                    dominant = max(range(3), key=lambda k: abs(normal[k]))
                    if normal[dominant] < 0:
                        normal = tuple(-c for c in normal)
                    level = sum(a * b for a, b in zip(normal, curve.Center))
                    key = (tuple(round(c, 6) for c in normal),
                           round(curve.Radius, 6), round(level, 6))
                    final_circles.setdefault(key, {})[tuple(round(c, 6) for c in curve.Center)] = (
                        curve.Center, source + ".circle_centre")

        for group, centres in final_circles.items():
            if len(centres) < 2:
                continue
            for value, ref in _aligned_point_spans(centres.values(), f"candidate.circle_layout@{group}"):
                add("L", value, ref)

        for index, face in enumerate(shape.Faces):
            source = f"candidate.Face{index + 1}"
            extents(face.BoundBox, source)
            for wire_index, wire in enumerate(face.Wires):
                extents(wire.BoundBox, source + f".wire{wire_index}")
                corner_angles(wire.Edges, source + f".wire{wire_index}")
                profile_wall_angles(wire, source + f".wire{wire_index}")
                wire_spans(wire, source + f".wire{wire_index}")

        # Restrict sketch and feature measurements to the selected body.
        objects = getattr(owner, "Group", ())
        spines = {}
        for obj in objects:
            if obj.TypeId in ("PartDesign::AdditivePipe", "PartDesign::SubtractivePipe"):
                link = getattr(obj, "Spine", None)
                if link and link[0] is not None:
                    spines.setdefault(link[0].Name, []).append(link[1])
        centres_by_axis = {}
        for obj in objects:
            if obj.TypeId != "Sketcher::SketchObject":
                continue
            placement = obj.getGlobalPlacement()
            circles_by_radius = {}
            for index, geom in enumerate(obj.Geometry):
                if obj.getConstruction(index):
                    continue
                if isinstance(geom, Part.LineSegment):
                    line_inclinations(geom.StartPoint, geom.EndPoint,
                                      f"{obj.Name}.Geometry[{index}].local")
                if isinstance(geom, Part.Circle):
                    circles_by_radius.setdefault(round(geom.Radius, 6), []).append(tuple(geom.Center))
                if isinstance(geom, (Part.Circle, Part.ArcOfCircle)):
                    centre = placement.multVec(geom.Center)
                    centre_source = f"{obj.Name}.Geometry[{index}].centre"
                    centre_to_bounds(centre, centre_source)
                    axis = tuple(placement.Rotation.multVec(geom.Axis))
                    axis = min(axis, tuple(-c for c in axis))
                    axis = tuple(round(c, 6) for c in axis)
                    centres_by_axis.setdefault(axis, {})[tuple(centre)] = centre_source
            for hole_radius, centres in circles_by_radius.items():
                for radius, count, centre in _circle_patterns(centres):
                    source = f"{obj.Name}.regular_circle_array@{centre}.hole_r{hole_radius}"
                    add("R", radius, source + ".pitch_radius")
                    add("D", 2 * radius, source + ".pitch_diameter")
                    add("C", count, source + ".count")
                    add("A", 2 * math.pi / count, source + ".angular_pitch")
            # Include both sketch and body placement in world-axis measurements.
            sketch_shape = obj.Shape.copy()
            sketch_shape.Placement = placement
            closed_wires = {}
            for index, wire in enumerate(sketch_shape.Wires):
                wire_spans(wire, f"{obj.Name}.wire{index}")
                if wire.isClosed():
                    extents(wire.BoundBox, f"{obj.Name}.closed_wire{index}")
                    corner_angles(wire.Edges, f"{obj.Name}.closed_wire{index}")
                    profile_wall_angles(wire, f"{obj.Name}.closed_wire{index}")
                    signature = tuple(sorted((type(edge.Curve).__name__, round(edge.Length, 6))
                                             for edge in wire.Edges if not edge.Degenerated))
                    closed_wires[signature] = closed_wires.get(signature, 0) + 1
            if closed_wires:
                add("C", sum(closed_wires.values()), f"{obj.Name}.closed_wire_count")
                for signature, count in closed_wires.items():
                    add("C", count, f"{obj.Name}.equal_closed_wire_count@{signature}")
            # Use a face as a sweep datum when a straight axial spine segment
            # crosses its outer boundary region. The spine may pass through a hole.
            for subelements in spines.get(obj.Name, ()):
                spine = (Part.Compound([sketch_shape.getElement(name) for name in subelements])
                         if subelements else sketch_shape)
                for axis, coordinate, face, ref in datum_faces:
                    crossing = False
                    for edge in spine.Edges:
                        if edge.Degenerated or not isinstance(edge.Curve, Part.Line):
                            continue
                        a = edge.valueAt(edge.FirstParameter)
                        b = edge.valueAt(edge.LastParameter)
                        if any(abs(a[k] - b[k]) > 1e-6 for k in range(3) if k != axis):
                            continue
                        if not min(a[axis], b[axis]) - 1e-6 <= coordinate <= max(a[axis], b[axis]) + 1e-6:
                            continue
                        foot = FreeCAD.Vector(a)
                        foot[axis] = coordinate
                        if inside_box(foot, face.BoundBox) and Part.Face(face.OuterWire).distToShape(Part.Vertex(foot))[0] <= 1e-6:
                            crossing = True
                            break
                    if crossing:
                        for index, vertex in enumerate(spine.Vertexes):
                            add("L", abs(vertex.Point[axis] - coordinate),
                                f"{obj.Name}.spine.Vertex{index + 1}.normal_to_{ref}")
        # Measure world-axis pitches between consecutive centre coordinates
        # within each group of parallel circle axes.
        for normal, centres in centres_by_axis.items():
            for axis in range(3):
                coordinates = {}
                for point, source in centres.items():
                    coordinates.setdefault(round(point[axis], 9), source)
                ordered = sorted(coordinates)
                for a, b in zip(ordered, ordered[1:]):
                    add("L", b - a,
                        f"{coordinates[a]}_to_{coordinates[b]}.axis{'xyz'[axis]}_pitch")
        # Sum the active lengths for explicitly two-sided extrusions.
        for obj in objects:
            if obj.TypeId not in ("PartDesign::Pad", "PartDesign::Pocket"):
                continue
            if getattr(obj, "SideType", None) == "Two sides":
                add("L", obj.Length.Value + obj.Length2.Value,
                    f"{obj.Name}.two_sided_length")
        return pools
    finally:
        FreeCAD.closeDocument(doc.Name)


def _declared_units():
    """Read parameter-unit declarations from the adjacent spec.json.

    Return a mapping from lowercase parameter names to unit labels.
    """
    from pathlib import Path
    import json

    path = Path(__file__).with_name("spec.json")
    data = json.loads(path.read_text())
    units = {}
    number = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?"
    pattern = re.compile(
        r"\b([A-Za-z][A-Za-z0-9_]*)\s*=\s*" + number
        + r"\s*(degrees|degree|deg|rad|°|mm|cm|m)?(?![A-Za-z])", re.IGNORECASE
    )
    parameters = data.get("key_parameters", "")
    if isinstance(parameters, str):
        for match in pattern.finditer(parameters):
            units[match.group(1).lower()] = (match.group(2) or "").lower()
    return units


def apply(report, bank, spec, tol_scalar) -> None:
    # Build reusable measurement pools before comparing specification values.
    pools = _build_pools(bank)
    shape_pools = _build_shape_pools(report.fcstd_path)
    for kind, measurements in shape_pools.items():
        pools[kind].extend(measurements)
    units = _declared_units()

    for source in (spec.scalars, spec.counts):
        for key, expected in source.items():
            kind = "C" if key in spec.counts else _classify(key)
            declared_unit = units.get(key, "")
            if declared_unit in {"degrees", "degree", "deg", "rad", "°"}:
                kind = "A"
            elif declared_unit in {"mm", "cm", "m"} and kind == "A":
                kind = "L"
            pool = pools[kind]
            if key == "modeling_feature_count":
                pool = [(float(_modeling_feature_count(bank)), "feature_tree.solid_op_count")]
            target = float(expected)
            display_target = as_display_angle(target) if kind == "A" else target
            unit = "deg" if kind == "A" else ("count" if kind == "C" else "mm")
            for bucket in ("consistent", "inconsistent", "not_found"):
                setattr(report, bucket, [f for f in getattr(report, bucket) if f.param != key])
            if not pool:
                report.not_found.append(make_not_found_finding(
                    param=key, spec_value=display_target, unit=unit,
                    reason=f"no measured CAD candidates of kind {kind}",
                ))
                continue
            # Select the nearest measured value within the dimension's pool.
            measured, ref = min(pool, key=lambda item: abs(item[0] - target))
            error = abs(measured - target) / max(abs(measured), abs(target), 1e-9)
            display_measured = as_display_angle(measured) if kind == "A" else measured
            kwargs = dict(param=key, spec_value=display_target,
                          measured_value=display_measured, unit=unit, feature=ref)
            if error <= tol_scalar:
                report.consistent.append(make_consistent_finding(**kwargs))
            else:
                report.inconsistent.append(make_inconsistent_finding(
                    **kwargs, rel_diff=error,
                    reason=f"measured CAD {kind} differs (rel_diff {error:.6g} > tol {tol_scalar})",
                ))
