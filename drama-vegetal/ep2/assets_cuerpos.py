# -*- coding: utf-8 -*-
"""DRAMA VEGETAL — personajes CON CUERPO (brazos, manos y piernas) en 3D.

blender -b -P assets_cuerpos.py [-- nombre ...]

Para cada personaje y pose se renderizan dos imagenes:
  <nombre>.png        personaje completo (vegetal + brazos + piernas)
  <nombre>_limbs.png  solo las extremidades que quedan DELANTE del cuerpo
                      (el vegetal hace de "holdout"); se compone encima de
                      la cara para que las manos tapen correctamente.
"""
import bpy, math, os, sys, json
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "v2"))
sys.path.insert(0, HERE)
_ARGV = list(sys.argv)
sys.argv = [sys.argv[0], "--", "none"]
import assets_blender as AB
import assets_ep2 as A2   # registra la calabaza
from bpy_extras.object_utils import world_to_camera_view

# medidas del cuerpo de cada vegetal: radio a la altura de los hombros, altura de hombros, cadera, largo de piernas
BODY = {
    "berenjena": dict(R=0.62, zs=1.05, hip=0.42, leg=0.75, limb=(0.03, 0.006, 0.05), r=0.085),
    "tomate": dict(R=0.78, zs=0.75, hip=0.4, leg=0.55, limb=(0.16, 0.012, 0.01), r=0.075),
    "pepino": dict(R=0.36, zs=1.55, hip=0.22, leg=0.8, limb=(0.012, 0.05, 0.015), r=0.07),
    "calabaza": dict(R=1.05, zs=0.65, hip=0.6, leg=0.5, limb=(0.35, 0.1, 0.01), r=0.11),
}


def pose_points(kind, pose, s):
    """Devuelve (codo, mano) en coordenadas del cuerpo para el lado s (-1 izq, +1 der)."""
    b = BODY[kind]
    R, zs = b["R"], b["zs"]
    Hb = 2.0
    P = {
        "idle": ((s * R * 1.3, 0.0, zs - 0.22 * Hb), (s * R * 1.38, -0.1 * R, zs - 0.44 * Hb)),
        "fear": ((s * R * 1.55, -0.45 * R, zs - 0.06 * Hb), (s * R * 1.25, -1.0 * R, zs + 0.16 * Hb)),
        "angry": ((s * R * 1.7, 0.1 * R, zs - 0.1 * Hb), (s * R * 1.05, -0.35 * R, zs - 0.3 * Hb)),
        "happy": ((s * R * 1.45, -0.1 * R, zs + 0.2 * Hb), (s * R * 1.65, -0.25 * R, zs + 0.46 * Hb)),
        "point": ((s * R * 1.3, 0.0, zs - 0.22 * Hb), (s * R * 1.38, -0.1 * R, zs - 0.44 * Hb)) if s < 0 else
                 ((R * 1.6, -0.5 * R, zs + 0.02 * Hb), (R * 2.3, -1.2 * R, zs + 0.06 * Hb)),
        "knock": ((s * R * 1.3, 0.0, zs - 0.22 * Hb), (s * R * 1.38, -0.1 * R, zs - 0.44 * Hb)) if s < 0 else
                 ((R * 1.45, -0.7 * R, zs + 0.02 * Hb), (R * 0.9, -1.45 * R, zs + 0.24 * Hb)),
        "crossed": ((s * R * 1.25, -0.75 * R, zs - 0.2 * Hb), (-s * R * 0.55, -1.2 * R, zs - 0.13 * Hb)),
        "evil": ((s * R * 1.35, -0.7 * R, zs - 0.17 * Hb), (s * R * 0.14, -1.25 * R, zs - 0.07 * Hb)),
        "open": ((s * R * 1.55, -0.35 * R, zs - 0.02 * Hb), (s * R * 2.1, -0.55 * R, zs + 0.06 * Hb)),
        "clasp": ((s * R * 1.15, -0.55 * R, zs - 0.25 * Hb), (s * R * 0.14, -1.1 * R, zs - 0.33 * Hb)),
        "protect": ((s * R * 1.25, -0.75 * R, zs - 0.1 * Hb), (s * R * 0.95, -1.45 * R, zs - 0.2 * Hb)),
    }
    return P[pose]


def tube(name, pts, radius, mat):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"; cu.bevel_depth = radius; cu.bevel_resolution = 8; cu.use_fill_caps = True
    sp = cu.splines.new("BEZIER")
    sp.bezier_points.add(len(pts) - 1)
    for i, p in enumerate(pts):
        bp = sp.bezier_points[i]
        bp.co = p
        bp.handle_left_type = bp.handle_right_type = "AUTO"
    ob = bpy.data.objects.new(name, cu)
    bpy.context.collection.objects.link(ob)
    ob.data.materials.append(mat)
    return ob


def sphere(name, loc, scale, mat, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1, segments=48, ring_count=24, location=loc)
    ob = bpy.context.object; ob.name = name
    ob.scale = scale; ob.rotation_euler = rot
    bpy.ops.object.shade_smooth()
    ob.data.materials.append(mat)
    return ob


def glove(name, loc, direction, size, mat):
    """Mano de dibujo animado: palma + pulgar + cuatro dedos redondeados."""
    d = Vector(direction).normalized()
    rot = d.to_track_quat("Z", "Y").to_euler()
    parts = [sphere(name + "_palma", loc, (size, size * 0.8, size * 1.05), mat, rot)]
    side = d.cross(Vector((0, -1, 0)))
    if side.length < 0.1:
        side = Vector((1, 0, 0))
    side.normalize()
    for k in range(4):
        off = side * (size * (-0.6 + k * 0.4)) + d * size * 1.0
        parts.append(sphere(f"{name}_d{k}", Vector(loc) + off, (size * 0.24, size * 0.24, size * 0.48), mat, rot))
    parts.append(sphere(name + "_pulgar", Vector(loc) - side * size * 0.95 + d * size * 0.2, (size * 0.26, size * 0.26, size * 0.45), mat,
                        (rot[0], rot[1] + 0.6, rot[2])))
    return parts


def add_body(kind, pose):
    """Anade brazos, guantes, piernas y zapatillas. Devuelve los objetos de las extremidades."""
    b = BODY[kind]
    L = b["leg"]
    limb_m = AB.mat(kind + "_limb", b["limb"], rough=0.35, coat=0.4, sss=0.05)
    glove_m = AB.mat("guante", (0.85, 0.85, 0.82), rough=0.45, sheen=0.3)
    shoe_m = AB.mat("zapatilla", (0.9, 0.9, 0.92), rough=0.4)
    sole_m = AB.mat("suela", {"berenjena": (0.4, 0.05, 0.5), "tomate": (0.6, 0.03, 0.03), "pepino": (0.05, 0.3, 0.05),
                               "calabaza": (0.5, 0.2, 0.0)}[kind], rough=0.5)
    limbs = []
    for s in (-1, 1):
        sh = Vector((s * b["R"] * 0.92, 0.0, b["zs"] + L))
        el, hd = pose_points(kind, pose, s)
        el = Vector(el) + Vector((0, 0, L)); hd = Vector(hd) + Vector((0, 0, L))
        limbs.append(tube(f"brazo{s}", [sh, el, hd], b["r"], limb_m))
        limbs += glove(f"mano{s}", hd + (hd - el).normalized() * b["r"] * 1.6, hd - el, b["r"] * 2.1, glove_m)
        # piernas
        hip = Vector((s * b["hip"], 0.0, L + 0.08))
        knee = Vector((s * (b["hip"] + 0.04), -0.05, L * 0.5))
        ank = Vector((s * (b["hip"] + 0.02), 0.0, 0.14))
        limbs.append(tube(f"pierna{s}", [hip, knee, ank], b["r"] * 1.1, limb_m))
        shoe = sphere(f"zapato{s}", (ank.x, ank.y - 0.12, 0.1), (b["r"] * 2.0, b["r"] * 3.2, b["r"] * 1.4), shoe_m)
        sole = sphere(f"suela{s}", (ank.x, ank.y - 0.12, 0.045), (b["r"] * 2.1, b["r"] * 3.3, b["r"] * 0.5), sole_m)
        limbs += [shoe, sole]
    return limbs


def render_body_char(kind, light, pose, name, res_y=1700, samples=32):
    s = AB.reset()
    AB.world_color((0.02, 0.025, 0.06), 0.4 if light != "back" else 0.1)
    if kind == "calabaza":
        anchors, eye_r = A2.build_calabaza()
    else:
        anchors, eye_r = AB.BUILDERS[kind]()
    L = BODY[kind]["leg"]
    # sube el vegetal sobre las piernas
    veg_objs = [o for o in bpy.context.scene.objects if o.type in ("MESH", "CURVE")]
    for o in veg_objs:
        o.location.z += L
    for k in anchors:
        anchors[k] = anchors[k] + Vector((0, 0, L))
    limbs = add_body(kind, pose)
    for (n, loc, e, c, sz) in AB.LIGHTING[light]:
        AB.area(n, loc, (0, 0, 1.0 + L), e, c, sz)
    # encuadre fijo por personaje (igual en todas las poses)
    b = BODY[kind]
    top = anchors["top"].z + 0.75 + 0.25
    width = b["R"] * 5.2
    cz = top / 2 - 0.25
    s.render.film_transparent = True
    s.render.resolution_y = res_y
    s.render.resolution_x = int(res_y * width / top)
    cam = AB.camera((0, -12, cz), (0, 0, cz), lens=85)
    cam.data.sensor_fit = "VERTICAL"; cam.data.sensor_height = 24
    cam.location.y = -(top / 2) / math.tan(math.atan(12 / 85))
    cam.location.z = cz; cam.rotation_euler = (math.pi / 2, 0, 0)
    s.cycles.samples = samples
    out = AB.OUT
    s.render.filepath = os.path.join(out, name + ".png")
    bpy.ops.render.render(write_still=True)
    # pasada de extremidades: el vegetal tapa pero no se ve
    for o in veg_objs:
        o.is_holdout = True
    s.render.filepath = os.path.join(out, name + "_limbs.png")
    s.cycles.samples = max(16, samples // 2)
    bpy.ops.render.render(write_still=True)
    bpy.context.view_layer.update()
    res = {}
    for k, p in anchors.items():
        co = world_to_camera_view(s, cam, p)
        res[k] = [co.x * s.render.resolution_x, (1 - co.y) * s.render.resolution_y]
    a = world_to_camera_view(s, cam, anchors["eye_l"]); bb = world_to_camera_view(s, cam, anchors["eye_l"] + Vector((eye_r, 0, 0)))
    res["eye_rad"] = abs(bb.x - a.x) * s.render.resolution_x
    res["size"] = [s.render.resolution_x, s.render.resolution_y]
    res["limbs"] = True
    return res


JOBS = [
    ("berenjena", "moon", "idle"), ("berenjena", "moon", "fear"), ("berenjena", "moon", "angry"),
    ("berenjena", "moon", "happy"), ("berenjena", "moon", "point"),
    ("pepino", "back", "knock"), ("pepino", "moon", "crossed"), ("pepino", "moon", "evil"), ("pepino", "moon", "open"),
    ("tomate", "moon", "clasp"), ("tomate", "moon", "happy"),
    ("calabaza", "moon", "protect"), ("calabaza", "moon", "fear"),
]
PFX = {"berenjena": "ber", "pepino": "pep", "tomate": "tom", "calabaza": "cal"}

if __name__ == "__main__":
    want = _ARGV[_ARGV.index("--") + 1:] if "--" in _ARGV else []
    A = AB.load_anchors()
    for kind, light, pose in JOBS:
        name = f"{PFX[kind]}B_{light}_{pose}"
        if want and name not in want:
            continue
        A[name] = render_body_char(kind, light, pose, name, res_y=int(os.environ.get("RES", 1700)), samples=int(os.environ.get("SAMPLES", 32)))
        AB.save_anchors(A)
        print("listo", name, flush=True)
    print("CUERPOS LISTOS")
