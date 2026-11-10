"""Scene kit for headless Blender Shorts (bpy 5.x, Cycles CPU). 1 unit = 10 m.
Usage in blender/<scene>/scene.py:
    import sys, os; sys.path.insert(0, os.path.join(d, '..', 'lib')); import kit
    K = kit.Kit(bpy, d)            # reads <scene>/lines.json (start/end per narration line, duration)
    ... build with K.* ...         # K.t(i)/K.te(i) = start/end seconds of narration line i
    return K.finish()              # dict for tools/blender_render.py
Everything animated is keyed in SECONDS via K.key(); no cuts: one camera path via K.camera([...]).
"""
import json, math, os, random
import bmesh

class Kit:
    def __init__(s, bpy, d, fps=24, samples=24):
        s.bpy, s.d, s.fps, s.samples = bpy, d, fps, samples
        L = json.load(open(os.path.join(d, "lines.json")))
        s.lines = [(x["start"], x["end"]) for x in L["lines"]]
        s.total = L["duration"]; s.frames = int(math.ceil(s.total * fps))
        s.sc = bpy.context.scene; s.sc.frame_start, s.sc.frame_end = 1, s.frames
        random.seed(11); s.rnd = random.random
    # ---- time ----
    def t(s, i): return s.lines[i][0]
    def te(s, i): return s.lines[i][1]
    def fr(s, t): return max(1, int(round(t * s.fps)) + 1)
    # ---- keys ----
    def key(s, ob, prop, t, val, interp=None):
        setattr(ob, prop, val); ob.keyframe_insert(prop, frame=s.fr(t))
    def key_socket(s, sock, t, val):
        sock.default_value = val; sock.keyframe_insert("default_value", frame=s.fr(t))
    def linear(s, on):
        s.bpy.context.preferences.edit.keyframe_new_interpolation_type = "LINEAR" if on else "BEZIER"
    def show(s, ob, t_on, t_off=None):
        ob.hide_render = True; ob.keyframe_insert("hide_render", frame=1)
        ob.hide_render = False; ob.keyframe_insert("hide_render", frame=s.fr(t_on))
        if t_off is not None:
            ob.hide_render = True; ob.keyframe_insert("hide_render", frame=s.fr(t_off))
    def rise(s, ob, t0, t1, dz):          # grows out of the ground (ground plane hides what is below z=0)
        z = ob.location.z
        s.key(ob, "location", 0, (ob.location.x, ob.location.y, z - dz)); s.key(ob, "location", t0, (ob.location.x, ob.location.y, z - dz))
        s.key(ob, "location", t1, (ob.location.x, ob.location.y, z))
    def grow_x(s, ob, t0, t1):
        ob.scale = (0.001, 1, 1); ob.keyframe_insert("scale", frame=s.fr(t0) - 1)
        ob.scale = (1, 1, 1); ob.keyframe_insert("scale", frame=s.fr(t1))
        s.show(ob, t0)
    # ---- materials ----
    def plain(s, name, c, rough=0.9):
        m = s.bpy.data.materials.new(name); m.use_nodes = True
        b = m.node_tree.nodes["Principled BSDF"]; b.inputs["Base Color"].default_value = (*c, 1); b.inputs["Roughness"].default_value = rough
        return m
    def noisy(s, name, c, scale=14, contrast=0.35, bump=0.6, rough=1.0):
        m = s.bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; b = nt.nodes["Principled BSDF"]
        co = nt.nodes.new("ShaderNodeTexCoord"); no = nt.nodes.new("ShaderNodeTexNoise"); no.inputs["Scale"].default_value = scale; no.inputs["Detail"].default_value = 10
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].color = (c[0]*(1-contrast), c[1]*(1-contrast), c[2]*(1-contrast), 1)
        ramp.color_ramp.elements[1].color = (min(1, c[0]*(1+contrast*0.5)), min(1, c[1]*(1+contrast*0.5)), min(1, c[2]*(1+contrast*0.5)), 1)
        nt.links.new(co.outputs["Object"], no.inputs["Vector"]); nt.links.new(no.outputs["Fac"], ramp.inputs["Fac"]); nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
        bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = bump
        nt.links.new(no.outputs["Fac"], bp.inputs["Height"]); nt.links.new(bp.outputs["Normal"], b.inputs["Normal"]); b.inputs["Roughness"].default_value = rough
        return m
    def brick(s, name, c1, c2, mortar, scale=(9, 18), mortar_size=0.04, bump=0.7, dirt=0.25):
        """UV-mapped brick pattern (UV = metres-ish: u along the wall, v up). per-brick colour variation + dirt noise + chips."""
        m = s.bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; b = nt.nodes["Principled BSDF"]
        uv = nt.nodes.new("ShaderNodeTexCoord"); mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (scale[0], scale[1], 1)
        br = nt.nodes.new("ShaderNodeTexBrick"); br.inputs["Color1"].default_value = (*c1, 1); br.inputs["Color2"].default_value = (*c2, 1)
        br.inputs["Mortar"].default_value = (*mortar, 1); br.inputs["Mortar Size"].default_value = mortar_size; br.inputs["Bias"].default_value = 0.0
        br.offset = 0.5; br.offset_frequency = 2; br.inputs["Scale"].default_value = 1.0
        no = nt.nodes.new("ShaderNodeTexNoise"); no.inputs["Scale"].default_value = 6; no.inputs["Detail"].default_value = 12
        mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"; mix.blend_type = "MULTIPLY"; mix.inputs[0].default_value = dirt
        vor = nt.nodes.new("ShaderNodeTexVoronoi"); vor.inputs["Scale"].default_value = 14
        add = nt.nodes.new("ShaderNodeMath"); add.operation = "ADD"; add.inputs[1].default_value = 0.0
        nt.links.new(uv.outputs["UV"], mp.inputs["Vector"]); nt.links.new(mp.outputs["Vector"], br.inputs["Vector"]); nt.links.new(mp.outputs["Vector"], vor.inputs["Vector"])
        nt.links.new(uv.outputs["Object"], no.inputs["Vector"])
        nt.links.new(br.outputs["Color"], mix.inputs[6]); nt.links.new(no.outputs["Color"], mix.inputs[7]); nt.links.new(mix.outputs[2], b.inputs["Base Color"])
        h = nt.nodes.new("ShaderNodeMath"); h.operation = "MULTIPLY_ADD"; h.inputs[1].default_value = 0.08; 
        nt.links.new(br.outputs["Fac"], h.inputs[0]); nt.links.new(vor.outputs["Distance"], h.inputs[2])
        bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = bump; bp.inputs["Distance"].default_value = 0.01
        nt.links.new(h.outputs[0], bp.inputs["Height"]); nt.links.new(bp.outputs["Normal"], b.inputs["Normal"]); b.inputs["Roughness"].default_value = 0.88
        return m
    def straw(s, name):
        m = s.bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; b = nt.nodes["Principled BSDF"]
        co = nt.nodes.new("ShaderNodeTexCoord"); wv = nt.nodes.new("ShaderNodeTexWave"); wv.inputs["Scale"].default_value = 90; wv.inputs["Distortion"].default_value = 6
        ramp = nt.nodes.new("ShaderNodeValToRGB"); ramp.color_ramp.elements[0].color = (0.30, 0.22, 0.05, 1); ramp.color_ramp.elements[1].color = (0.72, 0.58, 0.20, 1)
        nt.links.new(co.outputs["Object"], wv.inputs["Vector"]); nt.links.new(wv.outputs["Fac"], ramp.inputs["Fac"]); nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.95
        return m
    def fade_mat(s, name, color):
        """translucent overlay whose opacity is keyed via K.key_socket(m.node_tree.nodes['fac'].outputs[0], t, v)"""
        m = s.bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
        out = nt.nodes.new("ShaderNodeOutputMaterial"); mix = nt.nodes.new("ShaderNodeMixShader")
        tr = nt.nodes.new("ShaderNodeBsdfTransparent"); df = nt.nodes.new("ShaderNodeBsdfDiffuse"); df.inputs["Color"].default_value = (*color, 1)
        fac = nt.nodes.new("ShaderNodeValue"); fac.name = "fac"
        nt.links.new(fac.outputs[0], mix.inputs[0]); nt.links.new(tr.outputs[0], mix.inputs[1]); nt.links.new(df.outputs[0], mix.inputs[2]); nt.links.new(mix.outputs[0], out.inputs[0])
        return m
    # ---- geometry ----
    def mk(s, name, verts, faces, m, smooth=False):
        me = s.bpy.data.meshes.new(name); me.from_pydata(verts, [], faces); me.update()
        o = s.bpy.data.objects.new(name, me); s.sc.collection.objects.link(o)
        bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        uvl = bm.loops.layers.uv.new("UV")
        for f in bm.faces:
            n = f.normal
            for lp in f.loops:
                v = lp.vert.co
                lp[uvl].uv = ((v.y if abs(n.x) > abs(n.y) else v.x) if abs(n.z) < 0.7 else v.x, v.z if abs(n.z) < 0.7 else v.y)
        bm.to_mesh(me); bm.free(); me.materials.append(m)
        for p in me.polygons: p.use_smooth = smooth
        return o
    def box(s, name, w, d, h, loc, m):
        x, y, z = loc; hw, hd = w/2, d/2
        v = [(x-hw, y-hd, z), (x+hw, y-hd, z), (x+hw, y+hd, z), (x-hw, y+hd, z), (x-hw, y-hd, z+h), (x+hw, y-hd, z+h), (x+hw, y+hd, z+h), (x-hw, y+hd, z+h)]
        return s.mk(name, v, [(3,2,1,0), (0,1,5,4), (1,2,6,5), (2,3,7,6), (3,0,4,7), (4,5,6,7)], m)
    def half_frustum(s, name, bx, dy, tx, tdy, H, z0, m):
        """half model cut at y=0 (cut face is the camera-facing section). half-widths bx (bottom) tx (top), depth dy/tdy."""
        v = [(-bx, 0, z0), (bx, 0, z0), (bx, dy, z0), (-bx, dy, z0), (-tx, 0, z0+H), (tx, 0, z0+H), (tx, tdy, z0+H), (-tx, tdy, z0+H)]
        return s.mk(name, v, [(0,1,5,4), (1,2,6,5), (2,3,7,6), (3,0,4,7), (4,5,6,7), (3,2,1,0)], m)
    def poly(s, name, pts_xz, m, y=0.0): return s.mk(name, [(x, y, z) for x, z in pts_xz], [tuple(range(len(pts_xz)))], m)
    def cyl(s, name, r, h, loc, m, rot=(0, 0, 0), seg=24):
        s.bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=h, location=loc, rotation=rot, vertices=seg)
        o = s.bpy.context.object; o.name = name; o.data.materials.append(m); return o
    def sphere(s, name, r, loc, m, scale=(1, 1, 1)):
        s.bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=loc, segments=24, ring_count=12)
        o = s.bpy.context.object; o.name = name; o.scale = scale; o.data.materials.append(m)
        for p in o.data.polygons: p.use_smooth = True
        return o
    def person(s, loc, tunic, carry=None, height=0.17):
        """stylised worker ~1.7 m. returns (body, head, extra list); body is the parent."""
        sk = s.plain("skin", (0.36, 0.22, 0.14), 0.8); tn = s.plain("tun%0.2f" % tunic[0], tunic, 0.9)
        x, y, z = loc
        body = s.cyl("w_body", 0.028, height*0.62, (x, y, z + height*0.35), tn, seg=10)
        legs = s.cyl("w_legs", 0.020, height*0.38, (x, y, z + height*0.19), sk, seg=8)
        head = s.sphere("w_head", 0.024, (x, y, z + height*0.76), sk)
        parts = [legs, head]
        if carry:
            parts.append(s.box("w_brick", 0.06, 0.035, 0.03, (x, y, z + height*0.82), carry))
        for p in parts: p.parent = body; p.matrix_parent_inverse = body.matrix_world.inverted()
        return body
    def walk(s, body, p0, p1, t0, t1, bob=0.004):
        """linear walk with footfall bob"""
        s.linear(True); s.key(body, "location", t0, p0); s.key(body, "location", t1, p1); s.linear(False); s.force_linear(body, "location")
    def scatter(s, name, mat, n, area, size=(0.01, 0.04), avoid=None):
        x0, x1, y0, y1 = area; out = []
        for i in range(n):
            x, y = x0 + s.rnd()*(x1-x0), y0 + s.rnd()*(y1-y0)
            if avoid and avoid(x, y): continue
            r = size[0] + s.rnd()*(size[1]-size[0])
            o = s.sphere(f"{name}{i}", r, (x, y, r*0.3), mat, scale=(1, 0.8 + s.rnd()*0.4, 0.6)); o.rotation_euler = (0, 0, s.rnd()*6.28); out.append(o)
        return out
    # ---- world ----
    def world(s, sun_el=9, sun_rot=250, strength=0.22, haze=0.0, exposure=-0.3):
        bpy = s.bpy; w = bpy.data.worlds.new("w"); s.sc.world = w; w.use_nodes = True; nt = w.node_tree
        sky = nt.nodes.new("ShaderNodeTexSky"); sky.sky_type = "MULTIPLE_SCATTERING"
        sky.sun_elevation = math.radians(sun_el); sky.sun_rotation = math.radians(sun_rot); sky.air_density = 1.2; sky.aerosol_density = 1.6; sky.sun_intensity = 0.9
        bg = nt.nodes["Background"]; bg.inputs["Strength"].default_value = strength; nt.links.new(sky.outputs["Color"], bg.inputs["Color"])
        if haze:
            vs = nt.nodes.new("ShaderNodeVolumeScatter"); vs.inputs["Density"].default_value = haze; vs.inputs["Anisotropy"].default_value = 0.35; vs.inputs["Color"].default_value = (0.95, 0.85, 0.7, 1)
            nt.links.new(vs.outputs[0], nt.nodes["World Output"].inputs["Volume"])
        try: s.sc.view_settings.view_transform = "AgX"
        except Exception: pass
        for lk in ("Medium High Contrast", "AgX - Medium High Contrast"):
            try: s.sc.view_settings.look = lk; break
            except Exception: pass
        s.sc.view_settings.exposure = exposure
    def ground(s, mat, size=600, dunes=True):
        s.bpy.ops.mesh.primitive_plane_add(size=size, location=(0, 0, 0)); g = s.bpy.context.object; g.name = "ground"; g.data.materials.append(mat)
        if dunes:   # low far dunes break the flat horizon
            for i in range(14):
                a = s.rnd()*6.28; r = 120 + s.rnd()*80
                o = s.sphere(f"dune{i}", 1, (r*math.cos(a), r*math.sin(a), -2), mat, scale=(40 + s.rnd()*40, 18 + s.rnd()*20, 5 + s.rnd()*6))
        return g
    # ---- camera ----
    def camera(s, path, lens=34, fstop=5.6, focus_follow=True):
        """path = [(t_seconds, (cx,cy,cz), (tx,ty,tz)), ...]; one smooth Bezier path, Track-To target. NO cuts, no orbit."""
        bpy = s.bpy
        cd = bpy.data.cameras.new("cam"); cd.lens = lens; cd.sensor_width = 36
        cam = bpy.data.objects.new("cam", cd); s.sc.collection.objects.link(cam); s.sc.camera = cam
        tg = bpy.data.objects.new("tgt", None); s.sc.collection.objects.link(tg)
        c = cam.constraints.new("TRACK_TO"); c.target = tg; c.track_axis = "TRACK_NEGATIVE_Z"; c.up_axis = "UP_Y"
        cd.dof.use_dof = True; cd.dof.focus_object = tg; cd.dof.aperture_fstop = fstop
        for (tt, p, q) in path:
            s.key(cam, "location", tt, p); s.key(tg, "location", tt, q)
        s.cam, s.tgt = cam, tg
        return cam
    def rain(s, t0, t1, strength=1.2):
        """camera-parented streak curtain, visible t0..t1 (call AFTER camera())"""
        bpy = s.bpy
        bpy.ops.mesh.primitive_plane_add(size=1); rp = bpy.context.object; rp.name = "rain"; rp.parent = s.cam; rp.location = (0, 0, -2.2); rp.scale = (3.2, 5.6, 1)
        rm = bpy.data.materials.new("rain"); rm.use_nodes = True; nt = rm.node_tree; nt.nodes.clear()
        out = nt.nodes.new("ShaderNodeOutputMaterial"); mix = nt.nodes.new("ShaderNodeMixShader")
        tr = nt.nodes.new("ShaderNodeBsdfTransparent"); em = nt.nodes.new("ShaderNodeEmission"); em.inputs["Color"].default_value = (0.75, 0.85, 1, 1); em.inputs["Strength"].default_value = strength
        tc = nt.nodes.new("ShaderNodeTexCoord"); mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (500, 2.5, 1)
        no = nt.nodes.new("ShaderNodeTexNoise"); no.inputs["Scale"].default_value = 1.0; no.inputs["Detail"].default_value = 0
        cr = nt.nodes.new("ShaderNodeValToRGB"); cr.color_ramp.elements[0].position = 0.66; cr.color_ramp.elements[1].position = 0.72
        mu = nt.nodes.new("ShaderNodeMath"); mu.operation = "MULTIPLY"; ga = nt.nodes.new("ShaderNodeValue")
        nt.links.new(tc.outputs["UV"], mp.inputs["Vector"]); nt.links.new(mp.outputs["Vector"], no.inputs["Vector"]); nt.links.new(no.outputs["Fac"], cr.inputs["Fac"])
        nt.links.new(cr.outputs["Color"], mu.inputs[0]); nt.links.new(ga.outputs[0], mu.inputs[1]); nt.links.new(mu.outputs[0], mix.inputs[0])
        nt.links.new(tr.outputs[0], mix.inputs[1]); nt.links.new(em.outputs[0], mix.inputs[2]); nt.links.new(mix.outputs[0], out.inputs[0]); rp.data.materials.append(rm)
        for (tt, v) in ((0, 0), (t0 - 0.1, 0), (t0 + 0.3, 0.8), (t1, 0.8), (t1 + 0.5, 0)): s.key_socket(ga.outputs[0], tt, v)
        s.linear(True)
        for (tt, v) in ((t0 - 0.1, 0.0), (t1 + 0.5, -12.0)): s.key_socket(mp.inputs["Location"], tt, (0, v, 0))
        s.linear(False)
        return rp
    # ---- machines (added 2026-11-09 for the Antikythera Short) ----
    def metal(s, name, c, rough=0.35, metallic=1.0):
        m = s.plain(name, c, rough); m.node_tree.nodes["Principled BSDF"].inputs["Metallic"].default_value = metallic; return m
    def gear(s, name, r, teeth, thick, loc, m, tooth=None, axis="y", hub=0.0):
        """flat spur gear with triangular teeth (one mesh). axis 'y' = gear faces the camera (-y); spin it via rotation_euler[1].
        origin at the gear centre. tooth = tooth height (default ~2.2x pitch/2)."""
        tooth = tooth or max(0.006, 2.2 * math.pi * r / teeth / 2)
        pts = []
        for k in range(teeth * 2):
            a = math.pi * k / teeth; rr = r + (tooth if k % 2 == 0 else 0)
            pts.append((rr * math.cos(a), rr * math.sin(a)))
        n = len(pts); h = thick / 2
        if axis == "y": v = [(x, -h, z) for x, z in pts] + [(x, h, z) for x, z in pts]
        else: v = [(x, y, -h) for x, y in pts] + [(x, y, h) for x, y in pts]
        f = [tuple(range(n)), tuple(range(2*n - 1, n - 1, -1))] + [(i, (i+1) % n, n + (i+1) % n, n + i) for i in range(n)]
        o = s.mk(name, v, f, m); o.location = loc
        if hub: s.cyl(name + "_hub", hub, thick * 1.6, loc, m, rot=(math.pi/2, 0, 0) if axis == "y" else (0, 0, 0), seg=16).parent = o; o.children[0].location = (0, 0, 0); o.children[0].rotation_euler = (math.pi/2, 0, 0) if axis == "y" else (0, 0, 0)
        return o
    def spin(s, ob, t0, t1, a0, a1, idx=1, steps=None, fn=None):
        """rotation_euler[idx] from a0 to a1 (radians), linear; with fn(u)->angle keys every 1/6 s (uneven motion)"""
        s.linear(True)
        if fn is None:
            r = list(ob.rotation_euler); r[idx] = a0; s.key(ob, "rotation_euler", t0, tuple(r)); r[idx] = a1; s.key(ob, "rotation_euler", t1, tuple(r))
        else:
            n = steps or max(2, int((t1 - t0) * 6))
            for k in range(n + 1):
                u = k / n; r = list(ob.rotation_euler); r[idx] = fn(u); s.key(ob, "rotation_euler", t0 + u * (t1 - t0), tuple(r))
        s.linear(False); s.force_linear(ob, "rotation_euler")
    def force_linear(s, ob, path):
        """set LINEAR on every key of ob.<path> (the preferences route in linear() does not reach keys in the bpy module)"""
        ad = ob.animation_data
        if not ad or not ad.action: return
        fcs = []
        try:
            for ly in ad.action.layers:
                for st in ly.strips:
                    for cb in st.channelbags: fcs += list(cb.fcurves)
        except Exception:
            fcs = list(getattr(ad.action, "fcurves", []))
        for fc in fcs:
            if fc.data_path == path:
                for kp in fc.keyframe_points: kp.interpolation = "LINEAR"
    def pop(s, ob, t0, t1, full=None):
        """scale in from nothing (for parts that appear mid-air, where rise() would pass through other parts)"""
        full = full or tuple(ob.scale)
        ob.scale = (0.001, 0.001, 0.001); ob.keyframe_insert("scale", frame=max(1, s.fr(t0) - 1))
        ob.scale = full; ob.keyframe_insert("scale", frame=s.fr(t1)); s.show(ob, t0)
    def boxes(s, name, items, m):
        """many small boxes as ONE mesh: items = [(w,d,h,(x,y,z)), ...] (z = bottom)"""
        v, f = [], []
        for (w, d, h, (x, y, z)) in items:
            b = len(v); hw, hd = w/2, d/2
            v += [(x-hw, y-hd, z), (x+hw, y-hd, z), (x+hw, y+hd, z), (x-hw, y+hd, z), (x-hw, y-hd, z+h), (x+hw, y-hd, z+h), (x+hw, y+hd, z+h), (x-hw, y+hd, z+h)]
            f += [tuple(b+i for i in q) for q in ((3,2,1,0), (0,1,5,4), (1,2,6,5), (2,3,7,6), (3,0,4,7), (4,5,6,7))]
        return s.mk(name, v, f, m)
    def emit(s, name, c, strength=4.0):
        """emission material; animate via K.key_socket(m.node_tree.nodes['Emission'].inputs['Strength'], t, v)"""
        m = s.bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
        out = nt.nodes.new("ShaderNodeOutputMaterial"); e = nt.nodes.new("ShaderNodeEmission"); e.name = "Emission"
        e.inputs["Color"].default_value = (*c, 1); e.inputs["Strength"].default_value = strength; nt.links.new(e.outputs[0], out.inputs[0]); return m
    # ---- LOOK upgrade (2026-11-10, after the user rejected the flat "cardboard" Antikythera Short). EXPERIMENTAL: one test did not yet pass visual QA; tune, then log what worked ----
    def look(s, sun_el=14, sun_az=215, sun_power=4.5, sky=0.12, exposure=-0.4):
        """hard raking key sun (crisp, dark shadows) + dim sky fill + punchy grade. Call AFTER world()."""
        bpy = s.bpy; ld = bpy.data.lights.new("sunkey", "SUN"); ld.energy = sun_power; ld.angle = math.radians(1.2); ld.color = (1.0, 0.82, 0.62)
        o = bpy.data.objects.new("sunkey", ld); s.sc.collection.objects.link(o)
        o.rotation_euler = (math.radians(90 - sun_el), 0, math.radians(sun_az))
        s.sc.world.node_tree.nodes["Background"].inputs["Strength"].default_value = sky
        s.sc.view_settings.exposure = exposure
        for lk in ("AgX - Punchy", "Punchy", "AgX - High Contrast", "High Contrast"):
            try: s.sc.view_settings.look = lk; break
            except Exception: pass
        return o
    def bevel(s, ob, w=0.02, seg=2):
        """rounded edges catch highlights; flat 90-degree CG edges are the #1 'placeholder' tell"""
        m = ob.modifiers.new("bev", "BEVEL"); m.width = w; m.segments = seg; m.limit_method = "ANGLE"; return ob
    def wood(s, name, c=(0.30, 0.16, 0.07), scale=3.0, rough=0.6):
        """wood grain (stretched wave + noise), varied colour and a little bump"""
        m = s.bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; b = nt.nodes["Principled BSDF"]
        co = nt.nodes.new("ShaderNodeTexCoord"); mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (scale, scale, scale * 12)
        wv = nt.nodes.new("ShaderNodeTexWave"); wv.inputs["Scale"].default_value = 2.0; wv.inputs["Distortion"].default_value = 9; wv.inputs["Detail"].default_value = 6
        no = nt.nodes.new("ShaderNodeTexNoise"); no.inputs["Scale"].default_value = 30
        ramp = nt.nodes.new("ShaderNodeValToRGB"); ramp.color_ramp.elements[0].color = (c[0]*0.45, c[1]*0.45, c[2]*0.45, 1); ramp.color_ramp.elements[1].color = (min(1, c[0]*1.5), min(1, c[1]*1.5), min(1, c[2]*1.5), 1)
        nt.links.new(co.outputs["Object"], mp.inputs["Vector"]); nt.links.new(mp.outputs["Vector"], wv.inputs["Vector"]); nt.links.new(wv.outputs["Fac"], ramp.inputs["Fac"]); nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
        bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.25; nt.links.new(wv.outputs["Fac"], bp.inputs["Height"]); nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
        nt.links.new(co.outputs["Object"], no.inputs["Vector"]); nt.links.new(no.outputs["Fac"], b.inputs["Roughness"]); return m
    def bronze(s, name, c=(0.62, 0.36, 0.14), patina=(0.16, 0.36, 0.28), amount=0.35, scale=9):
        """polished bronze with noisy roughness and green patina in the crevices (noise mask); metallic needs dark surroundings to read"""
        m = s.bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; b = nt.nodes["Principled BSDF"]
        co = nt.nodes.new("ShaderNodeTexCoord"); no = nt.nodes.new("ShaderNodeTexNoise"); no.inputs["Scale"].default_value = scale; no.inputs["Detail"].default_value = 12
        ramp = nt.nodes.new("ShaderNodeValToRGB"); ramp.color_ramp.elements[0].position = 1 - amount; ramp.color_ramp.elements[1].position = 1 - amount + 0.08
        mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"; mix.inputs[6].default_value = (*c, 1); mix.inputs[7].default_value = (*patina, 1)
        met = nt.nodes.new("ShaderNodeMath"); met.operation = "SUBTRACT"; met.inputs[0].default_value = 1.0
        rg = nt.nodes.new("ShaderNodeMapRange"); rg.inputs["To Min"].default_value = 0.22; rg.inputs["To Max"].default_value = 0.75
        nt.links.new(co.outputs["Object"], no.inputs["Vector"]); nt.links.new(no.outputs["Fac"], ramp.inputs["Fac"]); nt.links.new(ramp.outputs["Color"], mix.inputs[0])
        nt.links.new(mix.outputs[2], b.inputs["Base Color"]); nt.links.new(ramp.outputs["Color"], met.inputs[1]); nt.links.new(met.outputs[0], b.inputs["Metallic"])
        nt.links.new(no.outputs["Fac"], rg.inputs["Value"]); nt.links.new(rg.outputs["Result"], b.inputs["Roughness"])
        bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.2; nt.links.new(no.outputs["Fac"], bp.inputs["Height"]); nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
        return m
    # ---- v2 REAL-OBJECT ROUTES (2026-11-10): the hero is a real museum scan or a real museum photo, never code primitives ----
    # assets come from fetch_assets.yml (licences in <scene>/assets/manifest.json); path helper:
    def asset(s, stem):
        """path of <scene>/assets/<stem>.* (first match), or None"""
        ad = os.path.join(s.d, "assets")
        if not os.path.isdir(ad): return None
        for f in sorted(os.listdir(ad)):
            if os.path.splitext(f)[0] == stem: return os.path.join(ad, f)
        return None
    def hdri(s, path, strength=0.4, rot_deg=0.0, exposure=-0.7, blur_bg=True):
        """image-based lighting from a CC0 HDRI (real reflections on scans and metals). The HDRI lights the scene but the camera
        sees a dark backdrop (Light Path 'Is Camera Ray' mix), so frames never show a busy or empty photo sky."""
        bpy = s.bpy; w = bpy.data.worlds.new("w"); s.sc.world = w; w.use_nodes = True; nt = w.node_tree
        bg = nt.nodes["Background"]; out = nt.nodes["World Output"]
        tc = nt.nodes.new("ShaderNodeTexCoord"); mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Rotation"].default_value = (0, 0, math.radians(rot_deg))
        env = nt.nodes.new("ShaderNodeTexEnvironment"); env.image = bpy.data.images.load(path)
        nt.links.new(tc.outputs["Generated"], mp.inputs["Vector"]); nt.links.new(mp.outputs["Vector"], env.inputs["Vector"]); nt.links.new(env.outputs["Color"], bg.inputs["Color"])
        bg.inputs["Strength"].default_value = strength
        if blur_bg:
            dark = nt.nodes.new("ShaderNodeBackground"); dark.inputs["Color"].default_value = (0.012, 0.010, 0.009, 1)
            lp = nt.nodes.new("ShaderNodeLightPath"); mx = nt.nodes.new("ShaderNodeMixShader")
            nt.links.new(lp.outputs["Is Camera Ray"], mx.inputs[0]); nt.links.new(bg.outputs[0], mx.inputs[1]); nt.links.new(dark.outputs[0], mx.inputs[2])
            nt.links.new(mx.outputs[0], out.inputs["Surface"])
        s.grade(exposure)
    def grade(s, exposure=-0.2):
        try: s.sc.view_settings.view_transform = "AgX"
        except Exception: pass
        for lk in ("AgX - Medium High Contrast", "Medium High Contrast"):
            try: s.sc.view_settings.look = lk; break
            except Exception: pass
        s.sc.view_settings.exposure = exposure
    def dark_world(s, c=(0.012, 0.010, 0.009), strength=1.0, exposure=-0.2):
        """fallback when no HDRI was fetched: near-black world; the studio lights do the work"""
        w = s.bpy.data.worlds.new("w"); s.sc.world = w; w.use_nodes = True
        bg = w.node_tree.nodes["Background"]; bg.inputs["Color"].default_value = (*c, 1); bg.inputs["Strength"].default_value = strength; s.grade(exposure)
    def area(s, name, loc, target, power, size=1.0, color=(1, 1, 1)):
        bpy = s.bpy; ld = bpy.data.lights.new(name, "AREA"); ld.energy = power; ld.size = size; ld.color = color
        o = bpy.data.objects.new(name, ld); s.sc.collection.objects.link(o); o.location = loc
        c = o.constraints.new("TRACK_TO"); tg = bpy.data.objects.new(name + "_t", None); s.sc.collection.objects.link(tg); tg.location = target
        c.target = tg; c.track_axis = "TRACK_NEGATIVE_Z"; c.up_axis = "UP_Y"; return o
    def studio(s, h=1.0, warm=(1.0, 0.86, 0.70), rim=(0.70, 0.82, 1.0), key_power=None):
        """museum-display lighting scaled to hero height h: warm hard-ish key from front-left-above, cool rim from behind
        (separates the object from the dark backdrop: the single biggest 'looks real' cue), weak fill. Returns (key, rim, fill)."""
        kp = key_power or 170 * h * h
        key = s.area("key", (-1.6*h, -2.2*h, 2.2*h), (0, 0, 0.5*h), kp, size=0.6*h, color=warm)
        rl = s.area("rim", (1.5*h, 2.4*h, 1.9*h), (0, 0, 0.6*h), kp * 1.3, size=0.9*h, color=rim)
        fill = s.area("fill", (2.4*h, -1.8*h, 0.6*h), (0, 0, 0.4*h), kp * 0.18, size=2.0*h, color=(1, 0.95, 0.9))
        return key, rl, fill
    def backdrop(s, h=1.0, c=(0.010, 0.009, 0.008), plinth=True, stone=(0.05, 0.045, 0.042)):
        """curved seamless backdrop (cyclorama) + a stone plinth: the 'museum vitrine' set. Dark, textured, never empty white."""
        bpy = s.bpy; m = s.noisy("backdrop", c, scale=3, contrast=0.25, bump=0.05)
        v, f = [], []; R = 2.0*h; W = 6*h; n = 12
        for i in range(n + 1):                 # floor -> quarter circle -> wall, in y-z, extruded along x
            a = math.pi/2 * i / n; y = 1.2*h + R*math.sin(a); z = R - R*math.cos(a)
            v += [(-W, y, z), (W, y, z)]
        v = [(-W, -6*h, 0), (W, -6*h, 0)] + v + [(-W, 1.2*h + R, 8*h), (W, 1.2*h + R, 8*h)]
        fz = -0.35*h if plinth else 0.0            # floor sits under the plinth; the hero stands on z=0 either way
        v = [(x, y, z + fz) for x, y, z in v]
        for i in range(len(v)//2 - 1): f.append((2*i, 2*i+1, 2*i+3, 2*i+2))
        cyc = s.mk("cyc", v, f, m, smooth=True)
        out = [cyc]
        if plinth:
            pm = s.noisy("plinth", stone, scale=9, contrast=0.3, bump=0.25, rough=0.85)
            p = s.box("plinth", 1.4*h, 1.4*h, 0.35*h, (0, 0, -0.35*h), pm); s.bevel(p, 0.02*h, 3); out.append(p)
            for poly in p.data.polygons: poly.use_smooth = False
        return out
    def stand(s, top_z=None, h=1.0, base=(0.55, 0.55, 0.22)):
        """museum mount for a fragment: stone base on the floor + a thin dark rod up to the object (objects never float).
        top_z defaults to the bottom of the last photo_relief cut-out + 4 % so the rod enters the object."""
        if top_z is None: top_z = getattr(s, "hero_bottom_z", 0.4) + 0.04 * h
        pm = s.noisy("standstone", (0.045, 0.04, 0.038), scale=9, contrast=0.3, bump=0.25, rough=0.85)
        b = s.box("standbase", base[0]*h, base[1]*h, base[2]*h, (0, 0.05*h, 0), pm); s.bevel(b, 0.015*h, 3)
        for p in b.data.polygons: p.use_smooth = False
        rod = s.cyl("rod", 0.012*h, top_z - base[2]*h + 0.02*h, (0, 0.05*h, (top_z + base[2]*h) / 2), s.metal("rodm", (0.05, 0.05, 0.05), 0.4), seg=12)
        return b, rod
    def hero_glb(s, path, height=1.0, rot=(0, 0, 0), z=0.0):
        """import a real scan (GLB/GLTF/OBJ/PLY), keep its scanned textures, scale it to `height`, centre it on x/y, stand it on z.
        Returns the parent empty (animate that). Big scans are decimated to ~400k faces so CPU render stays fast."""
        bpy = s.bpy; before = set(bpy.data.objects)
        ext = os.path.splitext(path)[1].lower()
        if ext in (".glb", ".gltf"): bpy.ops.import_scene.gltf(filepath=path)
        elif ext == ".obj": bpy.ops.wm.obj_import(filepath=path)
        elif ext == ".ply": bpy.ops.wm.ply_import(filepath=path)
        elif ext == ".stl": bpy.ops.wm.stl_import(filepath=path)
        else: raise SystemExit(f"unsupported scan format {ext}")
        obs = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
        if not obs: raise SystemExit("scan has no mesh")
        tops = [o for o in bpy.data.objects if o not in before and o.parent is None]
        root = bpy.data.objects.new("hero", None); s.sc.collection.objects.link(root)
        for o in tops: o.parent = root
        root.rotation_euler = rot; bpy.context.view_layer.update()
        import mathutils
        pts = [o.matrix_world @ mathutils.Vector(c) for o in obs for c in o.bound_box]
        lo = mathutils.Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
        hi = mathutils.Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
        k = height / max(1e-6, hi.z - lo.z); root.scale = (k, k, k)
        root.location = (-(lo.x + hi.x) / 2 * k, -(lo.y + hi.y) / 2 * k, z - lo.z * k)
        faces = sum(len(o.data.polygons) for o in obs)
        if faces > 400000:
            for o in obs:
                d = o.modifiers.new("dec", "DECIMATE"); d.ratio = 400000 / faces
        for o in obs:
            for p in o.data.polygons: p.use_smooth = True
        s.hero_size = (k * (hi.x - lo.x), k * (hi.y - lo.y), height)
        return root
    def turn(s, ob, t0, t1, deg):
        """slow linear turntable (z) so the scan shows its depth; 15-40 degrees over a Short reads as 'real object', more is a gimmick"""
        r0 = ob.rotation_euler.z; s.spin(ob, t0, t1, r0, r0 + math.radians(deg), idx=2)
    def photo_relief(s, img, depth=None, cut=None, width=1.0, relief=0.12, y=0.0, res=256, z=0.0):
        """2.5D parallax from ONE real photo: a finely subdivided card standing in the x-z plane (facing -y), photo as colour,
        depth map pushes near parts toward the camera, cut-out alpha removes the background. A blurred, darker copy of the
        photo sits behind as the plate. Returns (card, plate). Move the camera slowly (dolly + small lateral drift) for parallax."""
        bpy = s.bpy; im = bpy.data.images.load(img); W, H = im.size; h = width * H / W
        bpy.ops.mesh.primitive_grid_add(x_subdivisions=res, y_subdivisions=int(res * H / W), size=1)
        card = bpy.context.object; card.name = "photo"; card.scale = (width, h, 1); card.rotation_euler = (math.pi/2, 0, 0); card.location = (0, y, z + h/2)
        m = bpy.data.materials.new("photo"); m.use_nodes = True; nt = m.node_tree; b = nt.nodes["Principled BSDF"]
        tx = nt.nodes.new("ShaderNodeTexImage"); tx.image = im; tx.interpolation = "Cubic"
        nt.links.new(tx.outputs["Color"], b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.75
        em = b.inputs.get("Emission Color") or b.inputs.get("Emission"); nt.links.new(tx.outputs["Color"], em)
        b.inputs["Emission Strength"].default_value = 0.35          # keeps the photo's own lighting readable under the studio lights
        if cut:
            ct = nt.nodes.new("ShaderNodeTexImage"); ct.image = bpy.data.images.load(cut); nt.links.new(ct.outputs["Alpha"], b.inputs["Alpha"])
            try:   # lowest opaque row -> where the object really ends (stand() uses it so the rod touches the object)
                import numpy as np
                cw, chh = ct.image.size; a = np.array(ct.image.pixels[:], dtype="float32").reshape(chh, cw, 4)[:, :, 3]
                rows = np.where(a.max(axis=1) > 0.5)[0]; s.hero_bottom_z = z + h * (rows.min() / chh) if len(rows) else z
            except Exception: s.hero_bottom_z = z
            try: m.blend_method = "HASHED"
            except Exception: pass
        card.data.materials.append(m)
        if depth:
            dt = bpy.data.textures.new("depth", "IMAGE"); dt.image = bpy.data.images.load(depth); dt.image.colorspace_settings.name = "Non-Color"
            d = card.modifiers.new("relief", "DISPLACE"); d.texture = dt; d.texture_coords = "UV"; d.strength = relief; d.mid_level = 0.0
            d.direction = "Z"; card.modifiers.new("smooth", "SMOOTH").factor = 0.5
            for p in card.data.polygons: p.use_smooth = True
        # plate: same photo, bigger, darker, blurred-looking (low-res sampling) far behind
        bpy.ops.mesh.primitive_plane_add(size=1); plate = bpy.context.object; plate.name = "plate"
        plate.scale = (width * 2.6, h * 2.6, 1); plate.rotation_euler = (math.pi/2, 0, 0); plate.location = (0, y + 1.6 * width, h * 0.6)
        pm = bpy.data.materials.new("plate"); pm.use_nodes = True; pt = pm.node_tree; pt.nodes.clear()
        o = pt.nodes.new("ShaderNodeOutputMaterial"); e = pt.nodes.new("ShaderNodeEmission"); t2 = pt.nodes.new("ShaderNodeTexImage"); t2.image = im; t2.interpolation = "Closest"
        hsv = pt.nodes.new("ShaderNodeHueSaturation"); hsv.inputs["Value"].default_value = 0.25; hsv.inputs["Saturation"].default_value = 0.6
        pt.links.new(t2.outputs["Color"], hsv.inputs["Color"]); pt.links.new(hsv.outputs["Color"], e.inputs["Color"]); e.inputs["Strength"].default_value = 0.6; pt.links.new(e.outputs[0], o.inputs[0])
        plate.data.materials.append(pm)
        s.hero_size = (width, 0.0, h)
        return card, plate
    def finish(s, width=1080, height=1920):
        return dict(fps=s.fps, frames=s.frames, width=width, height=height, samples=s.samples)
