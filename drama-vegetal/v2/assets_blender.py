# -*- coding: utf-8 -*-
"""DRAMA VEGETAL v2 — recursos 3D realistas renderizados con Blender (Cycles).

Ejecutar:  blender -b -P assets_blender.py -- <grupo>
grupos: chars | eyes | rooms | phone | all

Salida en build/assets/: sprites RGBA de los personajes con iluminacion
fisica, ojos (rejilla de direcciones de mirada), fondos de la habitacion,
plano del telefono y anclas (coordenadas 2D de ojos, boca, etc.) en JSON.
"""
import bpy, bmesh, math, json, os, sys, random
from mathutils import Vector, Matrix
from bpy_extras.object_utils import world_to_camera_view

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "build", "assets")
os.makedirs(OUT, exist_ok=True)
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else ["all"]
GROUP = ARGS[0]
Q = float(os.environ.get("QUICK", "1"))  # <1 para pruebas rapidas
ANCHORS_PATH = os.path.join(OUT, "anchors.json")


# ------------------------------------------------------------------ util
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    s = bpy.context.scene
    s.render.engine = "CYCLES"
    s.cycles.device = "CPU"
    s.cycles.use_denoising = False
    s.cycles.max_bounces = 6
    s.view_settings.view_transform = "Filmic" if "Filmic" in [i.identifier for i in s.view_settings.bl_rna.properties["view_transform"].enum_items] else "AgX"
    s.view_settings.look = "None"
    s.render.image_settings.file_format = "PNG"
    s.render.image_settings.color_mode = "RGBA"
    w = bpy.data.worlds.new("w")
    s.world = w
    w.use_nodes = True
    return s


def world_color(col, strength):
    bg = bpy.context.scene.world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (*col, 1)
    bg.inputs[1].default_value = strength


def mat(name, base, rough=0.3, coat=0.0, sss=0.0, sss_col=None, sheen=0.0, emit=None, emit_strength=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*base, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Coat Weight"].default_value = coat
    b.inputs["Coat Roughness"].default_value = 0.04
    b.inputs["Subsurface Weight"].default_value = sss
    if sss_col:
        b.inputs["Subsurface Radius"].default_value = sss_col
    b.inputs["Sheen Weight"].default_value = sheen
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1)
        b.inputs["Emission Strength"].default_value = emit_strength
    return m


def add_noise_color(m, col2, scale=6.0, stretch=(1, 1, 4), fac=0.5, bump=0.03, bump_scale=60.0):
    """Variacion de color (vetas) + micro relieve."""
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = stretch
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = scale
    nz.inputs["Detail"].default_value = 6
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], nz.inputs["Vector"])
    rr = nt.nodes.new("ShaderNodeMapRange")
    rr.inputs["From Min"].default_value = 0.35
    rr.inputs["From Max"].default_value = 0.75
    nt.links.new(nz.outputs["Fac"], rr.inputs["Value"])
    mt = nt.nodes.new("ShaderNodeMath"); mt.operation = "MULTIPLY"; mt.inputs[1].default_value = fac
    nt.links.new(rr.outputs["Result"], mt.inputs[0])
    nt.links.new(mt.outputs[0], mix.inputs["Factor"])
    mix.inputs[6].default_value = b.inputs["Base Color"].default_value[:]
    mix.inputs[7].default_value = (*col2, 1)
    nt.links.new(mix.outputs[2], b.inputs["Base Color"])
    if bump:
        nz2 = nt.nodes.new("ShaderNodeTexNoise")
        nz2.inputs["Scale"].default_value = bump_scale
        nt.links.new(tc.outputs["Object"], nz2.inputs["Vector"])
        bp = nt.nodes.new("ShaderNodeBump")
        bp.inputs["Strength"].default_value = bump
        nt.links.new(nz2.outputs["Fac"], bp.inputs["Height"])
        nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m


def lathe(name, prof, segs=96):
    """prof: lista de (radio, z) de arriba a abajo. Devuelve objeto suavizado."""
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    rings = []
    for (r, z) in prof:
        ring = []
        for i in range(segs):
            a = i / segs * 2 * math.pi
            ring.append(bm.verts.new((math.cos(a) * r, math.sin(a) * r, z)))
        rings.append(ring)
    for k in range(len(rings) - 1):
        for i in range(segs):
            a, b = rings[k][i], rings[k][(i + 1) % segs]
            c, d = rings[k + 1][(i + 1) % segs], rings[k + 1][i]
            bm.faces.new((a, b, c, d))
    top = bm.verts.new((0, 0, prof[0][1] + 0.002))
    bot = bm.verts.new((0, 0, prof[-1][1] - 0.002))
    for i in range(segs):
        bm.faces.new((top, rings[0][(i + 1) % segs], rings[0][i]))
        bm.faces.new((bot, rings[-1][i], rings[-1][(i + 1) % segs]))
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(ob)
    for p in me.polygons:
        p.use_smooth = True
    sub = ob.modifiers.new("sub", "SUBSURF")
    sub.levels = 2
    sub.render_levels = 2
    return ob


def leaf(name, ang, length, width, z0, droop, r0=0.05, rough=0.55, col=(0.05, 0.16, 0.04), curl=0.15, seed=0):
    """Hoja del caliz que cae sobre la superficie."""
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    NU, NV = 14, 7
    grid = []
    rnd = random.Random(seed)
    jitter = rnd.uniform(-0.15, 0.15)
    for iu in range(NU + 1):
        u = iu / NU
        row = []
        wdt = width * math.sin(math.pi * min(1, u * 1.1)) ** 0.7 * (1 - 0.35 * u)
        for iv in range(NV + 1):
            v = iv / NV * 2 - 1
            R = r0 + length * u
            a = ang + jitter * u + v * wdt / max(R, 0.05)
            x, y = math.cos(a) * R, math.sin(a) * R
            z = z0 - droop * u * u + curl * (1 - v * v) * 0.12 * u
            row.append(bm.verts.new((x, y, z)))
        grid.append(row)
    for iu in range(NU):
        for iv in range(NV):
            bm.faces.new((grid[iu][iv], grid[iu][iv + 1], grid[iu + 1][iv + 1], grid[iu + 1][iv]))
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(ob)
    for p in me.polygons:
        p.use_smooth = True
    so = ob.modifiers.new("so", "SOLIDIFY"); so.thickness = 0.012
    sb = ob.modifiers.new("sub", "SUBSURF"); sb.levels = 1; sb.render_levels = 2
    m = mat(name + "_m", col, rough=rough, sheen=0.4, sss=0.05)
    add_noise_color(m, (col[0] * 1.8, col[1] * 1.6, col[2] * 1.5), scale=8, stretch=(1, 1, 1), fac=0.6, bump=0.08, bump_scale=120)
    ob.data.materials.append(m)
    return ob


def stem(name, pts, radius, col=(0.12, 0.16, 0.06)):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = radius
    cu.bevel_resolution = 6
    sp = cu.splines.new("BEZIER")
    sp.bezier_points.add(len(pts) - 1)
    for i, p in enumerate(pts):
        bp = sp.bezier_points[i]
        bp.co = p
        bp.handle_left_type = bp.handle_right_type = "AUTO"
    ob = bpy.data.objects.new(name, cu)
    bpy.context.collection.objects.link(ob)
    m = mat(name + "_m", col, rough=0.6)
    add_noise_color(m, (col[0] * 1.7, col[1] * 1.5, col[2]), scale=12, stretch=(1, 1, 6), fac=0.5, bump=0.1)
    ob.data.materials.append(m)
    return ob


# ------------------------------------------------------------------ personajes
def eggplant_profile():
    prof = []
    N = 70
    for i in range(N + 1):
        t = i / N
        if t < 0.06:
            r = 0.34 * math.sin(t / 0.06 * math.pi / 2) ** 0.6
        elif t < 0.75:
            k = (t - 0.06) / 0.69
            r = 0.34 + 0.46 * math.sin(k * math.pi / 2) ** 2.4
        else:
            k = (t - 0.75) / 0.25
            r = 0.80 * math.sqrt(max(0.0, 1 - k ** 2)) ** 0.9
        r = max(r, 0.004)
        prof.append((r, 2.2 * (1 - t)))
    return prof


def build_berenjena():
    prof = eggplant_profile()
    body = lathe("berenjena", prof)
    # leve inclinacion organica
    for v in body.data.vertices:
        t = 1 - v.co.z / 2.2
        v.co.x += 0.06 * math.sin(t * math.pi)
        v.co.y *= 0.96
    m = mat("ber_m", (0.028, 0.004, 0.045), rough=0.16, coat=0.9, sss=0.05, sss_col=(0.5, 0.1, 0.6))
    add_noise_color(m, (0.07, 0.015, 0.10), scale=5, stretch=(1, 1, 0.25), fac=0.5, bump=0.012, bump_scale=80)
    body.data.materials.append(m)
    ztop = 2.2
    for k in range(6):
        leaf(f"bl{k}", k / 6 * 2 * math.pi + 0.3, 0.62, 0.30, ztop - 0.02, 0.62, r0=0.08, seed=k)
    for k in range(5):
        leaf(f"bm{k}", k / 5 * 2 * math.pi + 0.9, 0.42, 0.24, ztop + 0.02, 0.38, r0=0.06, col=(0.07, 0.2, 0.05), seed=10 + k)
    stem("bstem", [(0, 0, ztop - 0.05), (0.03, 0, ztop + 0.2), (0.14, 0.0, ztop + 0.36)], 0.06)
    # anclas de la cara (sobre la superficie frontal, -Y)
    def surf(z, dx):
        t = 1 - z / 2.2
        idx = min(len(prof) - 1, int(t * (len(prof) - 1)))
        r = prof[idx][0]
        x = dx + 0.06 * math.sin(t * math.pi)
        y = -math.sqrt(max(0.001, r * r - dx * dx)) * 0.96
        return Vector((x, y, z))
    anchors = dict(eye_l=surf(1.02, -0.27), eye_r=surf(1.02, 0.27), mouth=surf(0.68, 0.0),
                   brow_l=surf(1.30, -0.27), brow_r=surf(1.30, 0.27), top=Vector((0, 0, 2.6)), bottom=Vector((0, 0, 0)))
    return anchors, 0.15  # radio del ojo (unidades)


def build_tomate():
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.8, segments=96, ring_count=48, location=(0, 0, 0.7))
    ob = bpy.context.object
    ob.name = "tomate"
    for v in ob.data.vertices:
        p = v.co.copy()
        phi = math.atan2(p.y, p.x)
        h = p.z / 0.8
        rr = 1 + 0.03 * math.cos(5 * phi) * (1 - abs(h)) + 0.0
        v.co.x *= rr * 1.05
        v.co.y *= rr * 1.05
        v.co.z *= 0.86
        if h > 0.85:  # hundimiento superior
            v.co.z -= (h - 0.85) * 0.5
    bpy.ops.object.shade_smooth()
    sub = ob.modifiers.new("sub", "SUBSURF"); sub.levels = 1; sub.render_levels = 2
    m = mat("tom_m", (0.40, 0.012, 0.006), rough=0.14, coat=0.6, sss=0.25, sss_col=(1.0, 0.2, 0.1))
    add_noise_color(m, (0.55, 0.07, 0.01), scale=3, stretch=(1, 1, 1), fac=0.35, bump=0.01, bump_scale=150)
    ob.data.materials.append(m)
    ztop = 0.7 + 0.8 * 0.86 - 0.07
    for k in range(5):
        leaf(f"tl{k}", k / 5 * 2 * math.pi - 0.3, 0.30, 0.07, ztop + 0.02, 0.10, r0=0.03, col=(0.06, 0.2, 0.05), seed=20 + k)
    stem("tstem", [(0, 0, ztop), (0.0, 0.01, ztop + 0.1), (-0.04, 0.02, ztop + 0.16)], 0.025)
    def surf(z, dx):
        cz = 0.7
        h = (z - cz) / (0.8 * 0.86)
        r = 0.8 * 1.05 * math.sqrt(max(0.0, 1 - h * h))
        return Vector((dx, -math.sqrt(max(0.001, r * r - dx * dx)), z))
    anchors = dict(eye_l=surf(0.82, -0.25), eye_r=surf(0.82, 0.25), mouth=surf(0.52, 0.0),
                   brow_l=surf(1.02, -0.25), brow_r=surf(1.02, 0.25), top=Vector((0, 0, 1.45)), bottom=Vector((0, 0, -0.05)))
    return anchors, 0.13


def build_pepino():
    prof = []
    N = 60
    L = 2.6
    for i in range(N + 1):
        t = i / N
        if t < 0.12:
            r = 0.33 * math.sin(t / 0.12 * math.pi / 2) ** 0.7
        elif t > 0.88:
            r = 0.33 * math.sin((1 - t) / 0.12 * math.pi / 2) ** 0.7
        else:
            r = 0.33 + 0.02 * math.sin(t * math.pi)
        prof.append((max(r, 0.004), L * (1 - t)))
    ob = lathe("pepino", prof, segs=96)
    for v in ob.data.vertices:
        t = 1 - v.co.z / L
        v.co.x += 0.08 * math.sin(t * math.pi)
    m = mat("pep_m", (0.03, 0.12, 0.03), rough=0.32, coat=0.3, sss=0.1, sss_col=(0.3, 0.8, 0.3))
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    # rayas claras longitudinales + verrugas
    tc = nt.nodes.new("ShaderNodeTexCoord")
    wv = nt.nodes.new("ShaderNodeTexWave")
    wv.wave_type = "BANDS"; wv.bands_direction = "X"
    wv.inputs["Scale"].default_value = 3.0
    wv.inputs["Distortion"].default_value = 1.5
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], wv.inputs["Vector"])
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"
    mix.inputs[6].default_value = (0.015, 0.06, 0.015, 1)
    mix.inputs[7].default_value = (0.06, 0.16, 0.04, 1)
    rr = nt.nodes.new("ShaderNodeMapRange")
    rr.inputs["From Min"].default_value = 0.6; rr.inputs["From Max"].default_value = 1.0
    nt.links.new(wv.outputs["Fac"], rr.inputs["Value"])
    nt.links.new(rr.outputs["Result"], mix.inputs["Factor"])
    nt.links.new(mix.outputs[2], b.inputs["Base Color"])
    vor = nt.nodes.new("ShaderNodeTexVoronoi")
    vor.inputs["Scale"].default_value = 14
    nt.links.new(tc.outputs["Object"], vor.inputs["Vector"])
    inv = nt.nodes.new("ShaderNodeMapRange")
    inv.inputs["From Min"].default_value = 0.0; inv.inputs["From Max"].default_value = 0.12
    inv.inputs["To Min"].default_value = 1.0; inv.inputs["To Max"].default_value = 0.0
    nt.links.new(vor.outputs["Distance"], inv.inputs["Value"])
    bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.5; bp.inputs["Distance"].default_value = 0.02
    nt.links.new(inv.outputs["Result"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    ob.data.materials.append(m)
    stem("pstem", [(0.0, 0, L - 0.02), (0.0, 0, L + 0.06)], 0.05, col=(0.25, 0.22, 0.1))

    def surf(z, dx):
        t = 1 - z / L
        r = 0.34
        return Vector((dx + 0.08 * math.sin(t * math.pi), -math.sqrt(max(0.001, r * r - dx * dx)), z))
    anchors = dict(eye_l=surf(1.98, -0.15), eye_r=surf(1.98, 0.15), mouth=surf(1.66, 0.0),
                   brow_l=surf(2.2, -0.15), brow_r=surf(2.2, 0.15), top=Vector((0, 0, 2.75)), bottom=Vector((0, 0, 0)))
    return anchors, 0.11


BUILDERS = dict(berenjena=build_berenjena, tomate=build_tomate, pepino=build_pepino)


def area(name, loc, target, energy, color, size=2.0):
    ld = bpy.data.lights.new(name, "AREA")
    ld.energy = energy
    ld.color = color
    ld.size = size
    ld.shape = "DISK"
    ob = bpy.data.objects.new(name, ld)
    bpy.context.collection.objects.link(ob)
    ob.location = loc
    d = Vector(target) - Vector(loc)
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return ob


def point(name, loc, energy, color, radius=0.1):
    ld = bpy.data.lights.new(name, "POINT")
    ld.energy = energy; ld.color = color; ld.shadow_soft_size = radius
    ob = bpy.data.objects.new(name, ld)
    bpy.context.collection.objects.link(ob)
    ob.location = loc
    return ob


def camera(loc, target, lens=50):
    cd = bpy.data.cameras.new("cam")
    cd.lens = lens
    ob = bpy.data.objects.new("cam", cd)
    bpy.context.collection.objects.link(ob)
    ob.location = loc
    d = Vector(target) - Vector(loc)
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = ob
    return ob


LIGHTING = {
    # luz de luna fria por la izquierda, contraluz azul, relleno calido muy bajo
    "moon": [("key", (-3.5, -3.0, 4.0), 900, (0.62, 0.72, 1.0), 2.5), ("rim", (3.0, 3.0, 3.0), 1500, (0.55, 0.65, 1.0), 2.0),
             ("fill", (3.0, -4.0, 1.2), 120, (1.0, 0.75, 0.55), 3.0)],
    # luz del telefono (cian) desde abajo a la derecha
    "phone": [("key", (1.6, -1.6, 0.6), 520, (0.45, 0.85, 1.0), 0.6), ("rim", (-3.0, 3.0, 3.0), 900, (0.5, 0.6, 1.0), 2.0),
              ("fill", (-3.0, -4.0, 2.0), 60, (0.6, 0.6, 1.0), 3.0)],
    # atardecer calido (para la foto)
    "sunset": [("key", (3.0, -3.0, 2.5), 900, (1.0, 0.65, 0.4), 3.0), ("rim", (-3.0, 3.0, 2.0), 900, (1.0, 0.4, 0.5), 2.0),
               ("fill", (-3.0, -4.0, 2.0), 200, (0.6, 0.7, 1.0), 3.0)],
    # silueta a contraluz de luna (pepino en la ventana)
    "back": [("rim", (0, 4.0, 3.0), 2500, (0.6, 0.7, 1.0), 3.0), ("key", (-3.0, -3.0, 2.0), 60, (0.5, 0.6, 1.0), 2.0)],
}


def render_char(kind, light, res_y, out_name, samples=64):
    s = reset()
    world_color((0.02, 0.025, 0.06), 0.4 if light != "back" else 0.1)
    anchors, eye_r = BUILDERS[kind]()
    for (n, loc, e, c, sz) in LIGHTING[light]:
        area(n, loc, (0, 0, 1.0), e, c, sz)
    top = anchors["top"].z
    cz = top / 2
    cam = camera((0, -9.0, cz + 0.2), (0, 0, cz), lens=85)
    s.render.film_transparent = True
    aspect = 0.75 if kind == "berenjena" else (1.3 if kind == "tomate" else 0.5)
    res_y = int(res_y * Q)
    s.render.resolution_y = res_y
    s.render.resolution_x = int(res_y * aspect)
    cam.data.sensor_fit = "VERTICAL"
    cam.data.sensor_height = 24
    # encuadre: altura del personaje + margen
    dist = 9.0
    hfov = 2 * math.atan(12 / 85)
    need = top * 1.12
    cam.location.y = -(need / 2) / math.tan(hfov / 2)
    s.cycles.samples = max(8, int(samples * Q))
    s.render.filepath = os.path.join(OUT, out_name + ".png")
    bpy.ops.render.render(write_still=True)
    bpy.context.view_layer.update()
    res = {}
    for k, p in anchors.items():
        co = world_to_camera_view(s, cam, p)
        res[k] = [co.x * s.render.resolution_x, (1 - co.y) * s.render.resolution_y]
    # radio del ojo en pixeles
    p0 = anchors["eye_l"]
    p1 = p0 + Vector((eye_r, 0, 0))
    a = world_to_camera_view(s, cam, p0); b = world_to_camera_view(s, cam, p1)
    res["eye_rad"] = abs(b.x - a.x) * s.render.resolution_x
    res["size"] = [s.render.resolution_x, s.render.resolution_y]
    return res


def render_eyes(kind, iris, out_prefix, res=320, samples=32):
    s = reset()
    world_color((0.02, 0.02, 0.04), 0.3)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1, segments=96, ring_count=48)
    eye = bpy.context.object
    bpy.ops.object.shade_smooth()
    m = bpy.data.materials.new("eye"); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    b.inputs["Roughness"].default_value = 0.05
    b.inputs["Coat Weight"].default_value = 1.0
    b.inputs["Coat Roughness"].default_value = 0.0
    b.inputs["Subsurface Weight"].default_value = 0.15
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], sep.inputs[0])
    neg = nt.nodes.new("ShaderNodeMath"); neg.operation = "MULTIPLY"; neg.inputs[1].default_value = -1
    nt.links.new(sep.outputs["Y"], neg.inputs[0])
    # fibras del iris
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 30; nz.inputs["Detail"].default_value = 4
    mpp = nt.nodes.new("ShaderNodeMapping"); mpp.inputs["Scale"].default_value = (6, 1, 6)
    nt.links.new(tc.outputs["Object"], mpp.inputs[0]); nt.links.new(mpp.outputs[0], nz.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    cr = ramp.color_ramp
    cr.interpolation = "EASE"
    e = cr.elements
    e[0].position = 0.0; e[0].color = (0.92, 0.88, 0.86, 1)
    e[1].position = 0.66; e[1].color = (0.95, 0.94, 0.93, 1)
    for pos, col in ((0.695, (iris[0] * 0.2, iris[1] * 0.2, iris[2] * 0.2, 1)), (0.72, (*iris, 1)),
                     (0.92, (iris[0] * 1.6, iris[1] * 1.6, iris[2] * 1.5, 1)), (0.95, (0.01, 0.01, 0.01, 1)), (1.0, (0.0, 0.0, 0.0, 1))):
        el = cr.elements.new(pos); el.color = col
    nt.links.new(neg.outputs[0], ramp.inputs[0])
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"; mix.blend_type = "MULTIPLY"
    mix.inputs["Factor"].default_value = 0.35
    nt.links.new(ramp.outputs[0], mix.inputs[6]); nt.links.new(nz.outputs["Color"], mix.inputs[7])
    nt.links.new(mix.outputs[2], b.inputs["Base Color"])
    eye.data.materials.append(m)
    area("key", (-3, -4, 4), (0, 0, 0), 600, (0.85, 0.9, 1.0), 1.2)
    area("fill", (3, -4, -1), (0, 0, 0), 80, (1.0, 0.85, 0.7), 3.0)
    cam = camera((0, -8, 0), (0, 0, 0), lens=100)
    s.render.film_transparent = True
    s.render.resolution_x = s.render.resolution_y = res
    cam.data.sensor_fit = "VERTICAL"; cam.data.sensor_height = 24
    cam.location.y = -1.12 / math.tan(math.atan(12 / 100))
    s.cycles.samples = samples
    for gy in (-1, 0, 1):
        for gx in (-2, -1, 0, 1, 2):
            eye.rotation_euler = (math.radians(gy * 14), 0, math.radians(-gx * 14))
            s.render.filepath = os.path.join(OUT, f"{out_prefix}_{gx}_{gy}.png")
            bpy.ops.render.render(write_still=True)


# ------------------------------------------------------------------ habitacion
def fabric(name, col, rough=0.8, scale=200):
    m = mat(name, col, rough=rough, sheen=0.6)
    add_noise_color(m, tuple(c * 1.5 for c in col), scale=4, stretch=(1, 1, 1), fac=0.3, bump=0.15, bump_scale=scale)
    return m


def wood(name, col):
    m = mat(name, col, rough=0.45, coat=0.2)
    nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    wv = nt.nodes.new("ShaderNodeTexWave"); wv.wave_type = "RINGS"
    wv.inputs["Scale"].default_value = 1.5; wv.inputs["Distortion"].default_value = 8; wv.inputs["Detail"].default_value = 4
    mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (1, 12, 1)
    nt.links.new(tc.outputs["Object"], mp.inputs[0]); nt.links.new(mp.outputs[0], wv.inputs["Vector"])
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"
    mix.inputs[6].default_value = (*col, 1); mix.inputs[7].default_value = (col[0] * 0.55, col[1] * 0.5, col[2] * 0.45, 1)
    nt.links.new(wv.outputs["Fac"], mix.inputs["Factor"]); nt.links.new(mix.outputs[2], b.inputs["Base Color"])
    return m


def box(name, loc, size, m, bevel=0.03, sub=0):
    bpy.ops.mesh.primitive_cube_add(location=loc)
    ob = bpy.context.object; ob.name = name
    ob.scale = (size[0] / 2, size[1] / 2, size[2] / 2)
    bpy.ops.object.transform_apply(scale=True)
    if bevel:
        bv = ob.modifiers.new("bv", "BEVEL"); bv.width = bevel; bv.segments = 4
    if sub:
        sb = ob.modifiers.new("sb", "SUBSURF"); sb.levels = sub; sb.render_levels = sub
    bpy.ops.object.shade_smooth()
    ob.data.materials.append(m)
    return ob


def build_room():
    """Dormitorio de noche. Escala: 1 unidad ~ 1 berenjena de 2.2 de alto => cama baja de juguete."""
    s = bpy.context.scene
    world_color((0.01, 0.012, 0.03), 1.0)
    floor_m = wood("suelo", (0.16, 0.08, 0.045))
    box("suelo", (0, 4, -0.05), (30, 24, 0.1), floor_m, bevel=0)
    wall_m = mat("pared", (0.10, 0.12, 0.22), rough=0.9)
    add_noise_color(wall_m, (0.13, 0.15, 0.27), scale=2, stretch=(1, 1, 1), fac=0.5, bump=0.05, bump_scale=40)
    # pared trasera con hueco de ventana (4 piezas)
    wx0, wx1, wz0, wz1, wy = -6.4, -2.2, 3.0, 8.0, 9.0
    box("pared_izq", (-12.2, wy, 7.5), (11.6, 0.4, 15), wall_m, 0)
    box("pared_der", (5.4, wy, 7.5), (15.2, 0.4, 15), wall_m, 0)
    box("pared_inf", ((wx0 + wx1) / 2, wy, wz0 / 2), (wx1 - wx0, 0.4, wz0), wall_m, 0)
    box("pared_sup", ((wx0 + wx1) / 2, wy, (wz1 + 15) / 2), (wx1 - wx0, 0.4, 15 - wz1), wall_m, 0)
    # marco y cruceta de la ventana
    frame_m = wood("marco", (0.3, 0.2, 0.12))
    for (x, z, sx, sz) in ((wx0, (wz0 + wz1) / 2, 0.25, wz1 - wz0), (wx1, (wz0 + wz1) / 2, 0.25, wz1 - wz0),
                           ((wx0 + wx1) / 2, wz0, wx1 - wx0 + 0.25, 0.25), ((wx0 + wx1) / 2, wz1, wx1 - wx0 + 0.25, 0.25),
                           ((wx0 + wx1) / 2, (wz0 + wz1) / 2, 0.15, wz1 - wz0), ((wx0 + wx1) / 2, (wz0 + wz1) / 2, wx1 - wx0, 0.15)):
        box("marco", (x, wy - 0.15, z), (sx, 0.3, sz), frame_m, 0.02)
    # cielo nocturno y luna detras de la ventana
    sky = mat("cielo", (0, 0, 0), emit=(0.05, 0.1, 0.28), emit_strength=1.2)
    box("cielo", ((wx0 + wx1) / 2, wy + 3.0, 6), (12, 0.1, 10), sky, 0)
    moon = mat("luna", (0, 0, 0), emit=(1.0, 0.97, 0.88), emit_strength=8)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.55, location=(-3.4, wy + 2.8, 7.0))
    bpy.context.object.data.materials.append(moon)
    rnd = random.Random(4)
    star = mat("estrella", (0, 0, 0), emit=(1, 1, 1), emit_strength=6)
    for _ in range(60):
        bpy.ops.mesh.primitive_ico_sphere_add(radius=rnd.uniform(0.015, 0.035), location=(rnd.uniform(-9, 1), wy + 2.9, rnd.uniform(3, 9.5)))
        bpy.context.object.data.materials.append(star)
    # luz de luna entrando por la ventana
    area("luna_luz", ((wx0 + wx1) / 2, wy + 2.0, 7.5), (0.5, 1.0, 0.0), 2600, (0.55, 0.68, 1.0), 4.0)
    # cortinas onduladas
    cur_m = fabric("cortina", (0.22, 0.04, 0.18), scale=300)
    for cx in (wx0 - 0.9, wx1 + 0.9):
        bpy.ops.mesh.primitive_plane_add(size=1, location=(cx, wy - 0.45, 5.6))
        c = bpy.context.object
        c.scale = (1.6, 1, 6.2); c.rotation_euler = (math.pi / 2, 0, 0)
        bpy.ops.object.transform_apply(scale=True, rotation=True)
        sb = c.modifiers.new("sb", "SUBDIVIDE" if False else "SUBSURF"); sb.levels = 3; sb.render_levels = 3; sb.subdivision_type = "SIMPLE"
        tx = bpy.data.textures.new("ond", "WOOD"); tx.wood_type = "BANDNOISE" if False else "BANDS"; tx.noise_basis_2 = "SIN"
        dp = c.modifiers.new("dp", "DISPLACE"); dp.texture = tx; dp.strength = 0.25; dp.direction = "Y"
        so = c.modifiers.new("so", "SOLIDIFY"); so.thickness = 0.03
        bpy.ops.object.shade_smooth()
        c.data.materials.append(cur_m)
    # cama
    bed_x, bed_y = 3.6, 5.2
    box("cabecero", (bed_x, bed_y + 2.5, 2.2), (6.4, 0.35, 4.4), wood("cab", (0.28, 0.15, 0.08)), 0.12)
    box("base", (bed_x, bed_y, 0.55), (6.2, 5.0, 1.1), wood("baseb", (0.24, 0.13, 0.07)), 0.08)
    box("colchon", (bed_x, bed_y, 1.35), (6.0, 4.8, 0.6), fabric("colchon", (0.75, 0.75, 0.8)), 0.2, 1)
    box("manta", (bed_x, bed_y - 0.6, 1.75), (6.25, 3.8, 0.35), fabric("manta", (0.16, 0.09, 0.32), scale=260), 0.18, 2)
    box("almohada", (bed_x, bed_y + 1.75, 1.95), (3.2, 1.0, 0.55), fabric("almohada", (0.55, 0.6, 0.78), scale=300), 0.3, 2)
    # mesita y lampara apagada
    box("mesita", (-1.2, 6.6, 1.0), (1.8, 1.6, 2.0), wood("mes", (0.22, 0.12, 0.07)), 0.05)
    bpy.ops.mesh.primitive_cone_add(radius1=0.55, radius2=0.3, depth=0.7, location=(-1.2, 6.6, 3.0))
    bpy.context.object.data.materials.append(fabric("pantalla", (0.7, 0.6, 0.45)))
    bpy.ops.mesh.primitive_cylinder_add(radius=0.05, depth=0.9, location=(-1.2, 6.6, 2.4))
    bpy.context.object.data.materials.append(mat("metal", (0.6, 0.55, 0.45), rough=0.3))
    # relleno muy tenue calido desde el pasillo
    area("pasillo", (8, -6, 4), (2, 5, 1), 150, (1.0, 0.7, 0.45), 6)
    return dict(pillow=Vector((bed_x, bed_y + 1.75, 2.2)), window=Vector(((wx0 + wx1) / 2, wy, (wz0 + wz1) / 2)))


ROOM_CAMS = {
    # nombre: (posicion, objetivo, lente)
    "wide": ((-0.5, -11.0, 4.2), (0.2, 6.0, 3.2), 26),
    "bed": ((3.0, -3.0, 3.2), (3.4, 6.5, 2.2), 32),
    "window": ((-3.2, -2.5, 4.4), (-4.2, 9.0, 5.4), 35),
    "corner": ((-3.0, -6.0, 3.0), (-1.5, 6.0, 2.6), 32),
}


def render_rooms(names, res=(1188, 2112), samples=int(os.environ.get("ROOM_SAMPLES", 64))):
    s = reset()
    info = build_room()
    s.render.film_transparent = False
    res = (int(res[0] * Q), int(res[1] * Q))
    s.render.resolution_x, s.render.resolution_y = res
    s.cycles.samples = max(8, int(samples * Q))
    out = {}
    for n in names:
        loc, tgt, lens = ROOM_CAMS[n]
        cam = camera(loc, tgt, lens)
        cam.data.sensor_fit = "VERTICAL"; cam.data.sensor_height = 24
        s.render.filepath = os.path.join(OUT, f"room_{n}.png")
        bpy.ops.render.render(write_still=True)
        bpy.context.view_layer.update()
        out[n] = {k: [world_to_camera_view(s, cam, v).x * res[0], (1 - world_to_camera_view(s, cam, v).y) * res[1]] for k, v in info.items()}
    return out


def render_phone(res=(1188, 2112), samples=int(os.environ.get("ROOM_SAMPLES", 64))):
    """Telefono sobre la manta, plano cenital ligeramente inclinado. Exporta las esquinas de la pantalla."""
    s = reset()
    world_color((0.005, 0.006, 0.015), 1.0)
    bpy.ops.mesh.primitive_plane_add(size=30, location=(0, 0, 0))
    pl = bpy.context.object
    sb = pl.modifiers.new("sb", "SUBSURF"); sb.levels = 4; sb.render_levels = 4; sb.subdivision_type = "SIMPLE"
    tx = bpy.data.textures.new("arrugas", "CLOUDS"); tx.noise_scale = 1.6
    dp = pl.modifiers.new("dp", "DISPLACE"); dp.texture = tx; dp.strength = 0.35
    bpy.ops.object.shade_smooth()
    pl.data.materials.append(fabric("manta", (0.16, 0.09, 0.32), scale=180))
    W_, H_, T = 1.5, 3.1, 0.16
    body = box("phone", (0, 0, 0.6), (W_, H_, T), mat("ph", (0.02, 0.02, 0.025), rough=0.25, coat=0.6), 0.12)
    body.rotation_euler = (0, 0, math.radians(-8))
    scr = mat("pantalla", (0, 0, 0), rough=0.05, coat=1.0, emit=(0.15, 0.35, 0.55), emit_strength=2.5)
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, 0.6 + T / 2 + 0.002))
    sp = bpy.context.object
    sp.scale = (W_ * 0.9, H_ * 0.93, 1)
    sp.rotation_euler = (0, 0, math.radians(-8))
    bpy.ops.object.transform_apply(scale=True)
    sp.data.materials.append(scr)
    point("glow", (0, 0, 1.6), 60, (0.45, 0.8, 1.0), 0.8)
    area("luna", (-6, 4, 8), (0, 0, 0), 500, (0.55, 0.65, 1.0), 4)
    cam = camera((0.35, -2.4, 6.0), (0, 0.1, 0.5), 40)
    cam.data.sensor_fit = "VERTICAL"; cam.data.sensor_height = 24
    cam.data.dof.use_dof = True; cam.data.dof.focus_object = sp; cam.data.dof.aperture_fstop = 2.2
    res = (int(res[0] * Q), int(res[1] * Q))
    s.render.resolution_x, s.render.resolution_y = res
    s.cycles.samples = max(8, int(samples * Q))
    s.render.filepath = os.path.join(OUT, "phone_plate.png")
    bpy.ops.render.render(write_still=True)
    bpy.context.view_layer.update()
    corners = []
    mw = sp.matrix_world
    for v in ((-0.5, 0.5, 0), (0.5, 0.5, 0), (0.5, -0.5, 0), (-0.5, -0.5, 0)):  # TL TR BR BL
        p = mw @ Vector(v)
        c = world_to_camera_view(s, cam, p)
        corners.append([c.x * res[0], (1 - c.y) * res[1]])
    return corners


def load_anchors():
    if os.path.exists(ANCHORS_PATH):
        return json.load(open(ANCHORS_PATH))
    return {}


def save_anchors(a):
    json.dump(a, open(ANCHORS_PATH, "w"), indent=1)


if __name__ == "__main__":
    A = load_anchors()
    if GROUP in ("chars", "all"):
        for (kind, light, res, name) in (("berenjena", "moon", 2000, "ber_moon"), ("berenjena", "phone", 2000, "ber_phone"),
                                         ("tomate", "moon", 900, "tom_moon"), ("tomate", "sunset", 900, "tom_sunset"),
                                         ("pepino", "sunset", 1400, "pep_sunset"), ("pepino", "back", 1400, "pep_back"),
                                         ("pepino", "moon", 1400, "pep_moon")):
            if os.path.exists(os.path.join(OUT, name + ".png")) and name in A:
                continue
            A[name] = render_char(kind, light, res, name, samples=int(os.environ.get("CHAR_SAMPLES", 64)))
            save_anchors(A)
    if GROUP in ("eyes", "all"):
        render_eyes("berenjena", (0.28, 0.13, 0.04), "eye_ber")
        render_eyes("tomate", (0.05, 0.3, 0.12), "eye_tom")
        render_eyes("pepino", (0.55, 0.38, 0.05), "eye_pep")
    if GROUP in ("rooms", "all"):
        A["rooms"] = render_rooms(list(ROOM_CAMS))
        save_anchors(A)
    if GROUP in ("phone", "all"):
        A["phone"] = render_phone()
        save_anchors(A)
    print("RECURSOS LISTOS", GROUP)
