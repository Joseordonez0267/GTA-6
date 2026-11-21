# -*- coding: utf-8 -*-
"""DRAMA VEGETAL Ep. 2 — recursos 3D nuevos (Blender): Mama Calabaza, sus ojos y el huerto.

blender -b -P assets_ep2.py
Los archivos se guardan junto a los del episodio 1 (../v2/build/assets/).
"""
import bpy, math, os, sys, random, json
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "v2"))
_ARGV = list(sys.argv)
sys.argv = [sys.argv[0], "--", "none"]
import assets_blender as AB


def build_calabaza():
    prof = []
    N = 60
    for i in range(N + 1):
        t = i / N
        r = 1.05 * math.sin(math.pi * t) ** 0.45
        z = 1.2 * (1 - t)
        prof.append((max(r, 0.01), z))
    ob = AB.lathe("calabaza", prof, segs=120)
    for v in ob.data.vertices:
        phi = math.atan2(v.co.y, v.co.x)
        rib = 1 + 0.07 * abs(math.cos(5 * phi)) - 0.035
        v.co.x *= rib * 1.08
        v.co.y *= rib * 1.08
        h = v.co.z / 1.2
        rr = math.hypot(v.co.x, v.co.y)
        if h > 0.8:          # hundimiento alrededor del tallo
            v.co.z -= (h - 0.8) * 0.9 * max(0.0, 1 - rr / 0.6)
    m = AB.mat("cal_m", (0.62, 0.17, 0.012), rough=0.38, coat=0.25, sss=0.08, sss_col=(1.0, 0.5, 0.1))
    AB.add_noise_color(m, (0.75, 0.32, 0.03), scale=4, stretch=(1, 1, 0.3), fac=0.45, bump=0.03, bump_scale=70)
    ob.data.materials.append(m)
    AB.stem("cstem", [(0, 0, 1.0), (0.04, 0, 1.3), (0.2, 0.02, 1.45)], 0.1, col=(0.2, 0.15, 0.06))
    for k in range(3):
        AB.leaf(f"cl{k}", k * 2.1 + 0.4, 0.5, 0.22, 1.12, 0.25, r0=0.1, col=(0.06, 0.18, 0.05), seed=40 + k)

    def surf(z, dx):
        h = z / 1.2
        r = 1.05 * math.sin(math.pi * (1 - h)) ** 0.45 * 1.08
        return Vector((dx, -math.sqrt(max(0.001, r * r - dx * dx)), z))
    anchors = dict(eye_l=surf(0.72, -0.34), eye_r=surf(0.72, 0.34), mouth=surf(0.42, 0.0),
                   brow_l=surf(0.92, -0.34), brow_r=surf(0.92, 0.34), top=Vector((0, 0, 1.5)), bottom=Vector((0, 0, 0)))
    return anchors, 0.16


AB.BUILDERS["calabaza"] = build_calabaza
_orig_render_char = AB.render_char


def render_char2(kind, light, res_y, out_name, samples=40):
    if kind == "calabaza":
        # mismo encuadre que el tomate pero mas ancho
        s = AB.reset()
        AB.world_color((0.02, 0.025, 0.06), 0.4)
        anchors, eye_r = build_calabaza()
        for (n, loc, e, c, sz) in AB.LIGHTING[light]:
            AB.area(n, loc, (0, 0, 0.8), e, c, sz)
        top = anchors["top"].z
        cam = AB.camera((0, -9.0, top / 2 + 0.2), (0, 0, top / 2), lens=85)
        s.render.film_transparent = True
        s.render.resolution_y = res_y
        s.render.resolution_x = int(res_y * 1.25)
        cam.data.sensor_fit = "VERTICAL"; cam.data.sensor_height = 24
        cam.location.y = -(top * 1.12 / 2) / math.tan(math.atan(12 / 85))
        s.cycles.samples = samples
        s.render.filepath = os.path.join(AB.OUT, out_name + ".png")
        bpy.ops.render.render(write_still=True)
        bpy.context.view_layer.update()
        from bpy_extras.object_utils import world_to_camera_view
        res = {}
        for k, p in anchors.items():
            co = world_to_camera_view(s, cam, p)
            res[k] = [co.x * s.render.resolution_x, (1 - co.y) * s.render.resolution_y]
        a = world_to_camera_view(s, cam, anchors["eye_l"]); b = world_to_camera_view(s, cam, anchors["eye_l"] + Vector((eye_r, 0, 0)))
        res["eye_rad"] = abs(b.x - a.x) * s.render.resolution_x
        res["size"] = [s.render.resolution_x, s.render.resolution_y]
        return res
    return _orig_render_char(kind, light, res_y, out_name, samples)


def render_huerto(res=(1188, 2112), samples=56):
    s = AB.reset()
    AB.world_color((0.015, 0.02, 0.04), 1.0)
    # tierra con surcos
    bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 8, 0))
    pl = bpy.context.object
    sb = pl.modifiers.new("sb", "SUBSURF"); sb.levels = 5; sb.render_levels = 5; sb.subdivision_type = "SIMPLE"
    tx = bpy.data.textures.new("surcos", "WOOD"); tx.wood_type = "BANDS"; tx.noise_basis_2 = "SIN"; tx.turbulence = 3
    dp = pl.modifiers.new("dp", "DISPLACE"); dp.texture = tx; dp.strength = 0.35
    tx2 = bpy.data.textures.new("grumos", "CLOUDS"); tx2.noise_scale = 0.4
    dp2 = pl.modifiers.new("dp2", "DISPLACE"); dp2.texture = tx2; dp2.strength = 0.12
    bpy.ops.object.shade_smooth()
    soil = AB.mat("tierra", (0.07, 0.04, 0.025), rough=0.95)
    AB.add_noise_color(soil, (0.12, 0.07, 0.04), scale=8, stretch=(1, 1, 1), fac=0.6, bump=0.4, bump_scale=60)
    pl.data.materials.append(soil)
    # brotes
    rnd = random.Random(3)
    for i in range(70):
        x, y = rnd.uniform(-9, 9), rnd.uniform(2, 24)
        for k in range(2):
            AB.leaf(f"br{i}{k}", rnd.uniform(0, 6.28), rnd.uniform(0.25, 0.45), 0.12, 0.35, -0.1, r0=0.0, col=(0.05, 0.2, 0.04), seed=i * 3 + k)
            ob = bpy.context.scene.objects[f"br{i}{k}"]
            ob.location = (x, y, 0)
    # valla de madera
    wood = AB.wood("valla", (0.25, 0.16, 0.09))
    for i in range(-12, 13):
        AB.box("poste", (i * 0.9, 18, 1.0), (0.18, 0.18, 2.0 + 0.2 * (i % 2)), wood, 0.03)
    AB.box("trav1", (0, 18, 1.4), (24, 0.12, 0.16), wood, 0.02)
    AB.box("trav2", (0, 18, 0.6), (24, 0.12, 0.16), wood, 0.02)
    # cielo tormentoso y luna
    sky = AB.mat("cielo", (0, 0, 0), emit=(0.06, 0.08, 0.16), emit_strength=1.0)
    AB.box("cielo", (0, 40, 10), (80, 0.1, 30), sky, 0)
    moon = AB.mat("luna", (0, 0, 0), emit=(1.0, 0.95, 0.85), emit_strength=6)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1.4, location=(5, 38, 13))
    bpy.context.object.data.materials.append(moon)
    AB.area("luna_luz", (6, 30, 14), (0, 6, 0), 3500, (0.6, 0.7, 1.0), 6)
    AB.area("relleno", (-8, -4, 6), (0, 6, 0), 300, (0.5, 0.55, 0.8), 6)
    cam = AB.camera((0, -4, 2.2), (0, 8, 1.2), 30)
    cam.data.sensor_fit = "VERTICAL"; cam.data.sensor_height = 24
    s.render.resolution_x, s.render.resolution_y = res
    s.cycles.samples = samples
    s.render.filepath = os.path.join(AB.OUT, "huerto.png")
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    A = AB.load_anchors()
    A["cal_moon"] = render_char2("calabaza", "moon", 1300, "cal_moon")
    A["cal_sunset"] = render_char2("calabaza", "sunset", 1300, "cal_sunset")
    AB.save_anchors(A)
    if "--solo-calabaza" not in _ARGV:
        AB.render_eyes("calabaza", (0.35, 0.18, 0.05), "eye_cal")
        render_huerto()
    print("RECURSOS EP2 LISTOS")
