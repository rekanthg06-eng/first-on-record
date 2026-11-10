# Ling fangyi (Smithsonian NMAA F1930.54a-b): the REAL museum 3D scan (body + lid, CC0), museum-vitrine set, one continuous dolly.
# Route: SCAN. h = 1.0 (vessel 35.3 cm tall). Body top ~0.52, lid 0.47-1.0. Front (taotie face + long side of the hip-roof lid) faces -y.
# QA round 2: camera-parented bottom shade (caption band), AO-driven grade on the scan textures, stronger rim, lid lifts on
# "how do you cast words?" so the camera looks INTO the vessel (where the writing is cast; not legible in the scan, never faked),
# macro moved to "carved masks and all".
import os, sys, math
def build(bpy, d):
    sys.path.insert(0, os.path.join(d, "..", "lib")); import kit
    K = kit.Kit(bpy, d, fps=24, samples=24); T, TE, END = K.t, K.te, K.total
    # ---- light + set (oxblood-black cyc, cool rim on the flanges, warm raking key) ----
    hd = K.asset("hdri")
    if hd: K.hdri(hd, strength=0.20, rot_deg=40, exposure=-0.35)
    else: K.dark_world(exposure=-0.6)
    K.backdrop(1.0, c=(0.012, 0.006, 0.006), stone=(0.016, 0.016, 0.019))
    key, rim, fill = K.studio(1.0, warm=(1.0, 0.76, 0.52), rim=(0.50, 0.82, 1.0))
    rim.data.energy = key.data.energy * 3.2
    K.area("kick", (1.9, 0.9, 1.1), (0, 0, 0.75), key.data.energy * 1.0, size=0.4, color=(0.55, 0.80, 1.0))
    K.area("kick2", (-1.9, 1.0, 1.2), (0, 0, 0.8), key.data.energy * 0.6, size=0.4, color=(1.0, 0.80, 0.6))
    fill.data.energy = key.data.energy * 0.05
    K.area("glow", (0, 2.6, 1.3), (0, 3.4, 1.1), 5, size=1.4, color=(1.0, 0.45, 0.32))
    inner = K.area("inner", (0.0, -0.15, 1.75), (0, 0, 0.1), 0, size=0.35, color=(1.0, 0.85, 0.7))   # lights the open vessel
    # ---- hero: real scan, two parts sharing one coordinate frame ----
    k = 1.0 / 0.3536
    roots = {}
    for part in ("body", "hero"):
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=K.asset(part))
        new = [o for o in bpy.data.objects if o not in before]
        r = bpy.data.objects.new("root_" + part, None); K.sc.collection.objects.link(r)
        for o in new:
            if o.parent is None: o.parent = r
            if o.type == "MESH":
                for p in o.data.polygons: p.use_smooth = True
                for m in o.data.materials: grade_scan(m)
        r.scale = (k, k, k); r.rotation_euler = (0, 0, math.radians(-90)); r.location = (0, 0, 0.1768 * k)
        roots[part] = r
    body, lid = roots["body"], roots["hero"]
    a0 = math.radians(-90); deg = 18
    fn = lambda u: a0 + math.radians(deg) * (1 - math.cos(math.pi * u)) / 2
    K.spin(body, 0, END, a0, a0 + math.radians(deg), idx=2, fn=fn)
    K.spin(lid, 0, END, a0, a0 + math.radians(deg), idx=2, fn=fn)
    # lid: lifts on "how do you cast words?" (look inside), hovers through the mould beats, lands on "carved masks and all"
    z0 = lid.location.z
    for tt, dz in ((0, 0), (T(3) - 0.3, 0), (T(4) - 0.1, 0.20), (T(7) - 0.2, 0.22), (T(7) + 1.4, 0)):
        K.key(lid, "location", tt, (0, 0, z0 + dz))
    for tt, e in ((0, 0), (T(3), 0), (T(4) - 0.2, 20), (TE(4) + 0.3, 20), (T(5) + 0.6, 0)):
        inner.data.energy = e; inner.data.keyframe_insert("energy", frame=K.fr(tt))
    # ---- camera ----
    c0, g0 = (0.42, -2.05, 0.40), (0.0, 0.0, 0.37)       # low 3/4: taotie body face large, hip-roof lid above
    def rot(p, a):
        ca, sa = math.cos(a), math.sin(a); return (p[0] * ca - p[1] * sa, p[0] * sa + p[1] * ca, p[2])
    ra = math.radians(deg)
    path = [
        (0.0, c0, g0),
        (T(1), (0.30, -2.20, 0.62), (0.0, 0.0, 0.38)),
        (T(3), (-0.10, -2.20, 1.00), (0.0, 0.0, 0.40)),
        (T(4) + 0.2, (0.22, -1.95, 1.30), (0.0, 0.0, 0.48)),    # high: looking down into the open vessel
        (TE(4) + 0.2, (0.18, -1.88, 1.26), (0.0, 0.0, 0.48)),
        (T(6), (0.34, -2.25, 0.85), (0.0, 0.0, 0.48)),             # wide: two cast parts, lid hovering
        (T(7) + 0.5, (0.12, -1.05, 0.30), (0.04, -0.30, 0.27)),    # macro: taotie mask on the body
        (TE(7) + 0.3, (0.12, -1.00, 0.29), (0.04, -0.30, 0.27)),
        (T(8) + 1.2, (-0.30, -2.15, 0.62), (0.0, 0.0, 0.38)),
        (END, rot(c0, ra), rot(g0, ra)),
    ]
    cam = K.camera(path, lens=50, fstop=5.6)
    cam.data.sensor_fit = "VERTICAL"; cam.data.sensor_height = 36
    for tt, f in ((0, 5.6), (T(7), 5.6), (T(7) + 0.5, 4.5), (TE(7) + 0.3, 4.5), (T(8) + 0.6, 5.6)):
        cam.data.dof.aperture_fstop = f; cam.data.dof.keyframe_insert("aperture_fstop", frame=K.fr(tt))
    bottom_shade(K, cam)
    return K.finish()

def grade_scan(m):
    """darken + add contrast to the scanned albedo with its own baked AO, AO-driven roughness (worn high points shinier)"""
    if not m or not m.use_nodes: return
    nt = m.node_tree; b = nt.nodes.get("Principled BSDF")
    if not b or not b.inputs["Base Color"].links: return
    src = b.inputs["Base Color"].links[0].from_socket
    ao = None
    for n in nt.nodes:
        if n.type == "SEPARATE_COLOR": ao = n.outputs["Red"]
    bc = nt.nodes.new("ShaderNodeBrightContrast"); bc.inputs["Bright"].default_value = -0.06; bc.inputs["Contrast"].default_value = 0.08
    nt.links.new(src, bc.inputs["Color"])
    mul = nt.nodes.new("ShaderNodeMix"); mul.data_type = "RGBA"; mul.blend_type = "MULTIPLY"; mul.inputs["Factor"].default_value = 1.0
    nt.links.new(bc.outputs["Color"], mul.inputs["A"])
    if ao is not None:
        gm = nt.nodes.new("ShaderNodeMath"); gm.operation = "POWER"; gm.inputs[1].default_value = 1.6
        nt.links.new(ao, gm.inputs[0]); nt.links.new(gm.outputs[0], mul.inputs["B"])
        mr = nt.nodes.new("ShaderNodeMapRange"); mr.inputs["To Min"].default_value = 0.85; mr.inputs["To Max"].default_value = 0.42
        nt.links.new(ao, mr.inputs["Value"]); nt.links.new(mr.outputs["Result"], b.inputs["Roughness"])
    else:
        mul.inputs["B"].default_value = (0.8, 0.8, 0.8, 1); b.inputs["Roughness"].default_value = 0.55
    hs = nt.nodes.new("ShaderNodeHueSaturation"); hs.inputs["Value"].default_value = 0.82; hs.inputs["Saturation"].default_value = 0.92
    nt.links.new(mul.outputs["Result"], hs.inputs["Color"]); nt.links.new(hs.outputs["Color"], b.inputs["Base Color"])
    try: b.inputs["Specular IOR Level"].default_value = 0.6
    except Exception: pass

def bottom_shade(K, cam):
    """camera-parented gradient card: darkens the lower frame (caption band 72-82 %) by up to ~60 %; a grade, not a texture"""
    bpy = K.bpy; dist = 0.25; fh = 2 * dist * math.tan(math.atan(18 / 50)); fw = fh * 9 / 16
    bpy.ops.mesh.primitive_plane_add(size=1); p = bpy.context.object; p.name = "shade"; p.parent = cam
    p.location = (0, 0, -dist); p.scale = (fw * 1.1, fh * 1.02, 1)
    m = bpy.data.materials.new("shade"); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial"); mix = nt.nodes.new("ShaderNodeMixShader")
    tr = nt.nodes.new("ShaderNodeBsdfTransparent"); bk = nt.nodes.new("ShaderNodeEmission"); bk.inputs["Color"].default_value = (0, 0, 0, 1)
    tc = nt.nodes.new("ShaderNodeTexCoord"); sx = nt.nodes.new("ShaderNodeSeparateXYZ"); cr = nt.nodes.new("ShaderNodeValToRGB")
    nt.links.new(tc.outputs["UV"], sx.inputs["Vector"]); nt.links.new(sx.outputs["Y"], cr.inputs["Fac"])
    els = cr.color_ramp.elements; els[0].position = 0.08; els[0].color = (0.62, 0.62, 0.62, 1); els[1].position = 0.46; els[1].color = (0, 0, 0, 1)
    e = els.new(0.24); e.color = (0.80, 0.80, 0.80, 1)
    nt.links.new(cr.outputs["Color"], mix.inputs[0]); nt.links.new(tr.outputs[0], mix.inputs[1]); nt.links.new(bk.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs[0]); p.data.materials.append(m)
    p.visible_shadow = False; p.visible_diffuse = False; p.visible_glossy = False; p.visible_transmission = False
    try: m.blend_method = "BLEND"
    except Exception: pass
    return p
