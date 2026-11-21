# -*- coding: utf-8 -*-
"""BEBÉS EN MISIÓN — recursos 3D (Blender/Cycles).

blender -b -P assets_bebes.py [-- nombre ...]

Bebes estilizados (cabeza grande, piel con dispersion subsuperficial, panal o
pijama), el cuarto del bebe de noche con la cuna, la capa de barrotes delanteros
de la cuna (para meter al bebe "dentro") y un bloque de juguete.
Cada pose se renderiza completa y con la pasada de extremidades (manos que
quedan delante de la cara), igual que en DRAMA VEGETAL.
"""
import bpy, math, os, sys, json, random
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "drama-vegetal", "v2"))
sys.path.insert(0, os.path.join(ROOT, "drama-vegetal", "ep2"))
_ARGV = list(sys.argv)
sys.argv = [sys.argv[0], "--", "none"]
import assets_blender as AB
import assets_cuerpos as AC
from bpy_extras.object_utils import world_to_camera_view

OUT = os.path.join(HERE, "build", "assets")
os.makedirs(OUT, exist_ok=True)
AB.OUT = OUT
ANCH = os.path.join(OUT, "anchors.json")

BABIES = {
    "mateo": dict(skin=(0.78, 0.48, 0.34), hair=(0.18, 0.09, 0.04), cloth=(0.92, 0.92, 0.9), onesie=False, tuft=True),
    "lucas": dict(skin=(0.62, 0.38, 0.25), hair=(0.06, 0.04, 0.03), cloth=(0.35, 0.6, 0.95), onesie=True, tuft=False),
}

# poses: centro del torso, centro de la cabeza, brazos (codo, mano) por lado, piernas (rodilla, pie)
POSES = {
    "sit": dict(torso=(0, 0, 0.62), head=(0, -0.02, 1.38),
                arm=lambda s: ((s * 0.52, -0.12, 0.6), (s * 0.42, -0.42, 0.42)),
                leg=lambda s: ((s * 0.26, -0.45, 0.22), (s * 0.3, -0.75, 0.14))),
    "stand": dict(torso=(0, 0, 0.92), head=(0, -0.02, 1.68),
                  arm=lambda s: ((s * 0.56, 0.0, 0.85), (s * 0.6, -0.08, 0.6)),
                  leg=lambda s: ((s * 0.2, -0.04, 0.42), (s * 0.22, -0.06, 0.08))),
    "reach": dict(torso=(0, 0, 0.92), head=(0, -0.02, 1.68),
                  arm=lambda s: ((s * 0.7, -0.1, 1.45), (s * 0.72, -0.2, 2.1)),
                  leg=lambda s: ((s * 0.2, -0.04, 0.42), (s * 0.22, -0.06, 0.08))),
    "cheer": dict(torso=(0, 0, 0.62), head=(0, -0.02, 1.38),
                  arm=lambda s: ((s * 0.62, -0.1, 0.95), (s * 0.78, -0.15, 1.5)),
                  leg=lambda s: ((s * 0.26, -0.45, 0.22), (s * 0.3, -0.75, 0.14))),
    "crawl": dict(torso=(0, 0.35, 0.55), head=(0, -0.25, 0.95),
                  arm=lambda s: ((s * 0.42, -0.35, 0.35), (s * 0.4, -0.45, 0.06)),
                  leg=lambda s: ((s * 0.28, 0.55, 0.2), (s * 0.3, 0.8, 0.08))),
    "shh": dict(torso=(0, 0, 0.62), head=(0, -0.02, 1.38),
                arm=lambda s: ((s * 0.52, -0.12, 0.6), (s * 0.42, -0.42, 0.42)) if s < 0 else
                ((0.55, -0.45, 0.85), (0.08, -0.72, 1.12)),
                leg=lambda s: ((s * 0.26, -0.45, 0.22), (s * 0.3, -0.75, 0.14))),
    "sleep": dict(torso=(0, 0, 0.58), head=(0.12, -0.02, 1.28),
                  arm=lambda s: ((s * 0.5, -0.1, 0.5), (s * 0.35, -0.35, 0.3)),
                  leg=lambda s: ((s * 0.26, -0.45, 0.22), (s * 0.3, -0.75, 0.14))),
    "facepalm": dict(torso=(0, 0, 0.62), head=(0, -0.02, 1.38),
                     arm=lambda s: ((s * 0.52, -0.12, 0.6), (s * 0.42, -0.42, 0.42)) if s < 0 else
                     ((0.58, -0.4, 1.0), (0.22, -0.66, 1.5)),
                     leg=lambda s: ((s * 0.26, -0.45, 0.22), (s * 0.3, -0.75, 0.14))),
}
HEAD_R = 0.56


def skin_mat(name, col):
    m = AB.mat(name, col, rough=0.48, sss=0.35, sss_col=(1.0, 0.35, 0.25), sheen=0.15)
    AB.add_noise_color(m, (col[0] * 1.06, col[1] * 0.9, col[2] * 0.88), scale=6, stretch=(1, 1, 1), fac=0.25, bump=0.01, bump_scale=200)
    return m


def build_baby(who, pose):
    B = BABIES[who]
    P = POSES[pose]
    sk = skin_mat(who + "_piel", B["skin"])
    cloth = AB.mat(who + "_ropa", B["cloth"], rough=0.7, sheen=0.5)
    AB.add_noise_color(cloth, tuple(c * 0.92 for c in B["cloth"]), scale=40, stretch=(1, 1, 1), fac=0.3, bump=0.08, bump_scale=300)
    hc = Vector(P["head"]); tc = Vector(P["torso"])
    # cabeza con mejillas
    head = AC.sphere("cabeza", hc, (HEAD_R, HEAD_R * 0.96, HEAD_R * 0.98), sk)
    sb = head.modifiers.new("sb", "SUBSURF"); sb.levels = 1; sb.render_levels = 2
    for sx in (-1, 1):
        AC.sphere("mejilla", hc + Vector((sx * 0.24, -0.36, -0.2)), (0.16, 0.11, 0.13), sk)
        AC.sphere("oreja", hc + Vector((sx * HEAD_R * 0.98, 0.02, -0.02)), (0.07, 0.11, 0.14), sk)
    AC.sphere("nariz", hc + Vector((0, -HEAD_R * 0.98, -0.1)), (0.07, 0.06, 0.055), sk)
    # pelo
    hair = AB.mat(who + "_pelo", B["hair"], rough=0.55, sheen=0.4)
    if B["tuft"]:
        AB.stem("mechon", [hc + Vector((0, -0.1, HEAD_R * 0.95)), hc + Vector((0.05, -0.2, HEAD_R + 0.18)),
                           hc + Vector((-0.1, -0.12, HEAD_R + 0.25)), hc + Vector((-0.08, -0.02, HEAD_R + 0.12))], 0.035, col=B["hair"])
    else:
        cap = AC.sphere("pelo", hc + Vector((0, 0.04, 0.08)), (HEAD_R * 1.01, HEAD_R * 0.97, HEAD_R * 0.93), hair)
        # solo la parte de arriba: se recorta con un booleano sencillo (cubo)
        bpy.ops.mesh.primitive_cube_add(size=2, location=hc + Vector((0, -0.55, -0.55)))
        cut = bpy.context.object
        cut.rotation_euler = (math.radians(35), 0, 0)
        bo = cap.modifiers.new("bo", "BOOLEAN"); bo.object = cut; bo.operation = "DIFFERENCE"
        cut.hide_render = True
    # torso + panal / pijama
    torso = AC.sphere("torso", tc, (0.44, 0.38, 0.5), cloth if B["onesie"] else sk)
    if not B["onesie"]:
        AC.sphere("panal", tc + Vector((0, 0, -0.22)), (0.47, 0.41, 0.32), cloth)
    limbs = []
    lm = cloth if B["onesie"] else sk
    for s in (-1, 1):
        sh = tc + Vector((s * 0.36, -0.02, 0.28))
        el, hd = (Vector(v) for v in P["arm"](s))
        limbs.append(AC.tube(f"brazo{s}", [sh, el, hd], 0.1, lm))
        limbs.append(AC.sphere(f"mano{s}", hd + (hd - el).normalized() * 0.06, (0.1, 0.09, 0.11), sk))
        hip = tc + Vector((s * 0.22, -0.02, -0.3))
        kn, ft = (Vector(v) for v in P["leg"](s))
        limbs.append(AC.tube(f"pierna{s}", [hip, kn, ft], 0.12, lm))
        limbs.append(AC.sphere(f"pie{s}", ft + Vector((0, -0.06, 0)), (0.11, 0.15, 0.09), sk))
    # anclas de la cara sobre la esfera de la cabeza (mirando a -Y)
    def surf(dx, dz):
        return hc + Vector((dx, -math.sqrt(max(0.001, HEAD_R ** 2 - dx * dx - dz * dz)) * 0.96, dz))
    anchors = dict(eye_l=surf(-0.21, 0.04), eye_r=surf(0.21, 0.04), mouth=surf(0.0, -0.27),
                   brow_l=surf(-0.21, 0.22), brow_r=surf(0.21, 0.22), top=hc + Vector((0, 0, HEAD_R + 0.3)), bottom=Vector((0, 0, 0)))
    return anchors, 0.1, limbs


LIGHT_ROOM = [("key", (-3.0, -3.5, 3.5), 700, (0.75, 0.8, 1.0), 2.5), ("rim", (3.0, 3.0, 3.0), 1100, (0.6, 0.7, 1.0), 2.0),
              ("fill", (3.0, -4.0, 1.5), 260, (1.0, 0.8, 0.6), 3.0)]


def render_baby(who, pose, name, res_y=1500, samples=32):
    s = AB.reset()
    AB.world_color((0.03, 0.03, 0.06), 0.5)
    anchors, eye_r, limbs = build_baby(who, pose)
    for (n, loc, e, c, sz) in LIGHT_ROOM:
        AB.area(n, loc, (0, 0, 1.0), e, c, sz)
    top, bot = 2.65, -0.1
    hgt = top - bot
    width = 2.3
    cz = (top + bot) / 2
    s.render.film_transparent = True
    s.render.resolution_y = res_y
    s.render.resolution_x = int(res_y * width / hgt)
    cam = AB.camera((0, -12, cz), (0, 0, cz), lens=85)
    cam.data.sensor_fit = "VERTICAL"; cam.data.sensor_height = 24
    cam.location.y = -(hgt / 2) / math.tan(math.atan(12 / 85))
    cam.location.z = cz; cam.rotation_euler = (math.pi / 2, 0, 0)
    s.cycles.samples = samples
    s.render.filepath = os.path.join(OUT, name + ".png")
    bpy.ops.render.render(write_still=True)
    lset = set(limbs)
    for o in bpy.context.scene.objects:
        if o.type in ("MESH", "CURVE") and o not in lset:
            o.is_holdout = True
    s.render.filepath = os.path.join(OUT, name + "_limbs.png")
    s.cycles.samples = max(16, samples // 2)
    bpy.ops.render.render(write_still=True)
    bpy.context.view_layer.update()
    res = {}
    for k, p in anchors.items():
        co = world_to_camera_view(s, cam, p)
        res[k] = [co.x * s.render.resolution_x, (1 - co.y) * s.render.resolution_y]
    a = world_to_camera_view(s, cam, anchors["eye_l"]); b = world_to_camera_view(s, cam, anchors["eye_l"] + Vector((eye_r, 0, 0)))
    res["eye_rad"] = abs(b.x - a.x) * s.render.resolution_x
    res["size"] = [s.render.resolution_x, s.render.resolution_y]
    res["limbs"] = True
    return res


# ------------------------------------------------------------------ cuarto del bebe
def pastel(name, col, rough=0.8):
    m = AB.mat(name, col, rough=rough)
    AB.add_noise_color(m, tuple(c * 1.08 for c in col), scale=3, stretch=(1, 1, 1), fac=0.4, bump=0.03, bump_scale=60)
    return m


def build_nursery():
    AB.world_color((0.01, 0.012, 0.03), 1.0)
    AB.box("suelo", (0, 4, -0.05), (30, 24, 0.1), AB.wood("suelo", (0.32, 0.2, 0.12)), 0)
    rug = AB.fabric("alfombra", (0.45, 0.6, 0.75), scale=400)
    bpy.ops.mesh.primitive_cylinder_add(radius=3.2, depth=0.04, location=(-1.0, 2.5, 0.02), vertices=96)
    bpy.context.object.data.materials.append(rug)
    wall = pastel("pared", (0.32, 0.42, 0.62))
    AB.box("pared", (0, 9.0, 7.5), (40, 0.4, 15), wall, 0)
    AB.box("pared_izq", (-9.0, 4, 7.5), (0.4, 24, 15), wall, 0)
    # estrellas pintadas en la pared
    star = AB.mat("estrella_p", (0.9, 0.8, 0.4), emit=(1.0, 0.85, 0.5), emit_strength=0.6)
    rnd = random.Random(5)
    for _ in range(24):
        bpy.ops.mesh.primitive_ico_sphere_add(radius=rnd.uniform(0.06, 0.12), location=(rnd.uniform(-8, 8), 8.75, rnd.uniform(3, 9)))
        bpy.context.object.data.materials.append(star)
    # ventana con luna
    sky = AB.mat("cielo", (0, 0, 0), emit=(0.05, 0.1, 0.25), emit_strength=1.3)
    AB.box("ventana", (-5.0, 8.75, 6.0), (2.6, 0.1, 3.2), sky, 0)
    fr = AB.wood("marco", (0.9, 0.9, 0.88))
    for (x, z, sx, sz) in ((-6.3, 6, 0.15, 3.3), (-3.7, 6, 0.15, 3.3), (-5, 7.6, 2.75, 0.15), (-5, 4.4, 2.75, 0.15), (-5, 6, 0.1, 3.2)):
        AB.box("marco", (x, 8.6, z), (sx, 0.2, sz), fr, 0.02)
    moon = AB.mat("luna", (0, 0, 0), emit=(1.0, 0.97, 0.85), emit_strength=6)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.38, location=(-4.4, 9.5, 6.8))
    bpy.context.object.data.materials.append(moon)
    AB.area("luna_luz", (-5, 10.5, 7), (0, 3, 0), 1500, (0.55, 0.68, 1.0), 3.0)
    # lamparita de noche (calida)
    AB.box("mesita", (-6.5, 6.5, 0.8), (1.4, 1.2, 1.6), AB.wood("mesita", (0.85, 0.82, 0.78)), 0.05)
    lamp = AB.mat("lampara", (0.9, 0.7, 0.4), emit=(1.0, 0.65, 0.3), emit_strength=6)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.35, location=(-6.5, 6.5, 1.95))
    bpy.context.object.data.materials.append(lamp)
    AB.point("lampara_luz", (-6.5, 6.0, 2.2), 180, (1.0, 0.65, 0.35), 0.4)
    # cuna (madera blanca): base, colchon, barrotes
    cw = AB.wood("cuna", (0.92, 0.9, 0.86))
    cx, cy = 3.4, 5.4
    AB.box("cuna_base", (cx, cy, 1.0), (4.4, 2.6, 0.25), cw, 0.04)
    AB.box("colchon", (cx, cy, 1.25), (4.2, 2.4, 0.3), AB.fabric("colchon_c", (0.85, 0.85, 0.9)), 0.12, 1)
    front = []
    for side_y, tag in ((cy - 1.3, "front"), (cy + 1.3, "back")):
        AB.box(f"riel_sup_{tag}", (cx, side_y, 3.1), (4.5, 0.14, 0.14), cw, 0.03)
        AB.box(f"riel_inf_{tag}", (cx, side_y, 1.15), (4.5, 0.14, 0.14), cw, 0.03)
        for i in range(13):
            ob = AB.box(f"barrote_{tag}{i}", (cx - 2.1 + i * 0.35, side_y, 2.12), (0.08, 0.08, 1.95), cw, 0.02)
            if tag == "front":
                front.append(ob)
        if tag == "front":
            front += [bpy.context.scene.objects[f"riel_sup_{tag}"], bpy.context.scene.objects[f"riel_inf_{tag}"]]
    for x in (cx - 2.25, cx + 2.25):
        for y in (cy - 1.3, cy + 1.3):
            AB.box("pata", (x, y, 1.6), (0.18, 0.18, 3.2), cw, 0.03)
    # movil de juguete
    AB.box("mobil_eje", (cx, cy, 4.6), (0.04, 0.04, 1.2), cw, 0)
    for k, col in enumerate(((0.9, 0.5, 0.5), (0.5, 0.8, 0.6), (0.9, 0.85, 0.4))):
        a = k * 2.1
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.16, location=(cx + math.cos(a) * 0.6, cy + math.sin(a) * 0.6, 3.75))
        bpy.context.object.data.materials.append(AB.mat(f"mob{k}", col, rough=0.5))
    # bloques de juguete por el suelo
    for k in range(7):
        col = rnd.choice([(0.85, 0.2, 0.2), (0.2, 0.45, 0.85), (0.95, 0.75, 0.15), (0.2, 0.7, 0.35)])
        b = AB.box(f"bloque{k}", (rnd.uniform(-3.5, 0.5), rnd.uniform(0.5, 4.5), 0.25), (0.5, 0.5, 0.5), AB.mat(f"bl{k}", col, rough=0.35, coat=0.3), 0.04)
        b.rotation_euler = (0, 0, rnd.uniform(0, 1.5))
    AB.area("relleno", (2, -6, 5), (0, 4, 1), 260, (0.7, 0.75, 1.0), 6)
    return dict(crib=Vector((cx, cy - 1.3, 1.4)), front=front)


NURSERY_CAMS = {
    "wide": ((0.6, -9.0, 3.6), (0.6, 5.0, 2.0), 30),
    "crib": ((3.4, -2.2, 2.9), (3.4, 5.4, 2.1), 32),
}


def render_nursery(res=(1188, 2112), samples=56):
    s = AB.reset()
    info = build_nursery()
    s.render.resolution_x, s.render.resolution_y = res
    s.cycles.samples = samples
    out = {}
    front = set(info["front"])
    for n, (loc, tgt, lens) in NURSERY_CAMS.items():
        cam = AB.camera(loc, tgt, lens)
        cam.data.sensor_fit = "VERTICAL"; cam.data.sensor_height = 24
        s.render.film_transparent = False
        for o in bpy.context.scene.objects:
            o.is_holdout = False
        s.render.filepath = os.path.join(OUT, f"cuarto_{n}.png")
        bpy.ops.render.render(write_still=True)
        # capa de barrotes delanteros (para meter a un bebe dentro de la cuna)
        s.render.film_transparent = True
        for o in bpy.context.scene.objects:
            if o.type in ("MESH", "CURVE"):
                o.is_holdout = o not in front
        s.cycles.samples = max(24, samples // 2)
        s.render.filepath = os.path.join(OUT, f"cuarto_{n}_barrotes.png")
        bpy.ops.render.render(write_still=True)
        s.cycles.samples = samples
        bpy.context.view_layer.update()
        c = world_to_camera_view(s, cam, info["crib"])
        out[n] = dict(crib=[c.x * res[0], (1 - c.y) * res[1]])
    return out


def render_block(samples=48):
    s = AB.reset()
    AB.world_color((0.03, 0.03, 0.06), 0.6)
    b = AB.box("bloque", (0, 0, 0.5), (1, 1, 1), AB.mat("bl", (0.85, 0.2, 0.2), rough=0.35, coat=0.3), 0.06)
    b.rotation_euler = (0, 0, math.radians(20))
    bpy.ops.object.text_add(location=(-0.25, -0.62, 0.3), rotation=(math.pi / 2, 0, math.radians(20)))
    t = bpy.context.object
    t.data.body = "A"; t.data.size = 0.7; t.data.extrude = 0.02
    t.data.materials.append(AB.mat("letra", (0.95, 0.95, 0.9), rough=0.4))
    for (n, loc, e, c, sz) in LIGHT_ROOM:
        AB.area(n, loc, (0, 0, 0.5), e, c, sz)
    AB.camera((0, -6, 1.6), (0, 0, 0.5), 50)
    s.render.film_transparent = True
    s.render.resolution_x = s.render.resolution_y = 400
    s.cycles.samples = samples
    s.render.filepath = os.path.join(OUT, "bloque.png")
    bpy.ops.render.render(write_still=True)


JOBS = [("mateo", p) for p in ("sit", "crawl", "reach", "cheer", "shh", "sleep", "facepalm", "stand")] + \
       [("lucas", p) for p in ("reach", "stand", "cheer", "sleep")]

if __name__ == "__main__":
    want = _ARGV[_ARGV.index("--") + 1:] if "--" in _ARGV else []
    A = json.load(open(ANCH)) if os.path.exists(ANCH) else {}
    Q = float(os.environ.get("QUICK", "1"))
    for who, pose in JOBS:
        name = f"{who}_{pose}"
        if want and name not in want:
            continue
        A[name] = render_baby(who, pose, name, res_y=int(1500 * Q), samples=max(8, int(32 * Q)))
        json.dump(A, open(ANCH, "w"), indent=1)
        print("listo", name, flush=True)
    if not want or "cuarto" in want:
        A["cuarto"] = render_nursery(res=(int(1188 * Q), int(2112 * Q)), samples=max(8, int(56 * Q)))
        json.dump(A, open(ANCH, "w"), indent=1)
        print("listo cuarto", flush=True)
    if not want or "bloque" in want:
        render_block()
    print("BEBES LISTOS")
