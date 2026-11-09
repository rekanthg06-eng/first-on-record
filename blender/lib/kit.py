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
        s.linear(True); s.key(body, "location", t0, p0); s.key(body, "location", t1, p1); s.linear(False)
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
    def finish(s, width=1080, height=1920):
        return dict(fps=s.fps, frames=s.frames, width=width, height=height, samples=s.samples)
