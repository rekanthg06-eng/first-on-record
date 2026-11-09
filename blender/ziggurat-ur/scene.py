# Ziggurat of Ur build-up (RECONSTRUCTION, cut-away). 1 unit ~ 10 m. One continuous dolly, no cuts.
import json, math, os, random

def build(bpy, d):
    import bmesh
    from mathutils import Vector
    L = json.load(open(os.path.join(d, "lines.json")))
    FPS = 24
    lines = [(x["start"], x["end"]) for x in L["lines"]]
    total = L["duration"]
    frames = int(math.ceil(total * FPS))
    def fr(t): return max(1, int(round(t * FPS)) + 1)
    sc = bpy.context.scene
    sc.frame_start, sc.frame_end = 1, frames
    random.seed(7)

    # ---------- materials ----------
    def mat(name, color, rough=0.9):
        m = bpy.data.materials.new(name); m.use_nodes = True
        b = m.node_tree.nodes["Principled BSDF"]
        b.inputs["Base Color"].default_value = (*color, 1); b.inputs["Roughness"].default_value = rough
        return m
    def brick_mat(name, c1, c2, mortar, scale=(9, 18)):
        m = bpy.data.materials.new(name); m.use_nodes = True
        nt = m.node_tree; b = nt.nodes["Principled BSDF"]
        uv = nt.nodes.new("ShaderNodeTexCoord"); br = nt.nodes.new("ShaderNodeTexBrick")
        mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (scale[0], scale[1], 1)
        br.inputs["Color1"].default_value = (*c1, 1); br.inputs["Color2"].default_value = (*c2, 1)
        br.inputs["Mortar"].default_value = (*mortar, 1); br.inputs["Mortar Size"].default_value = 0.035
        br.inputs["Scale"].default_value = 1.0; br.inputs["Bias"].default_value = 0.0
        br.offset = 0.5; br.offset_frequency = 2; br.squash = 1.0
        nt.links.new(uv.outputs["UV"], mp.inputs["Vector"]); nt.links.new(mp.outputs["Vector"], br.inputs["Vector"])
        nt.links.new(br.outputs["Color"], b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.85
        bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.4
        nt.links.new(br.outputs["Fac"], bump.inputs["Height"]); nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
        return m
    def mud_mat(name, c):
        m = bpy.data.materials.new(name); m.use_nodes = True
        nt = m.node_tree; b = nt.nodes["Principled BSDF"]
        no = nt.nodes.new("ShaderNodeTexNoise"); no.inputs["Scale"].default_value = 18; no.inputs["Detail"].default_value = 8
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].color = (c[0]*0.75, c[1]*0.75, c[2]*0.75, 1); ramp.color_ramp.elements[1].color = (c[0]*1.1, c[1]*1.1, c[2]*1.05, 1)
        nt.links.new(no.outputs["Fac"], ramp.inputs["Fac"]); nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
        bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.5
        nt.links.new(no.outputs["Fac"], bump.inputs["Height"]); nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
        b.inputs["Roughness"].default_value = 1.0
        return m
    M_mud = brick_mat("mudbrick", (0.52, 0.37, 0.21), (0.44, 0.31, 0.17), (0.28, 0.19, 0.11), scale=(5, 10))
    M_brick = brick_mat("baked", (0.55, 0.22, 0.10), (0.46, 0.18, 0.09), (0.03, 0.025, 0.02))
    M_mat = mat("reed", (0.45, 0.38, 0.12), 1.0)
    M_hole = mat("hole", (0.01, 0.008, 0.006), 1.0)
    M_ground = mud_mat("ground", (0.62, 0.50, 0.33))
    M_fig = mat("fig", (0.12, 0.10, 0.09), 0.9)
    M_stamp = mat("stamp", (0.30, 0.13, 0.06), 0.9)

    # ---------- geometry helpers ----------
    def mk(name, verts, faces, m):
        me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces); me.update()
        o = bpy.data.objects.new(name, me); sc.collection.objects.link(o)
        bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        uvl = bm.loops.layers.uv.new("UV")
        for f in bm.faces:
            n = f.normal
            for lp in f.loops:
                v = lp.vert.co
                lp[uvl].uv = ((v.y if abs(n.x) > abs(n.y) else v.x), v.z)
        bm.to_mesh(me); bm.free()
        me.materials.append(m)
        for p in me.polygons: p.use_smooth = False
        return o
    def half_frustum(name, bx, dy, tx, tdy, H, z0, m):
        # half model: y in [0, depth], cut plane y=0. bottom half-width bx, depth dy; top tx, tdy; height H
        v = [(-bx, 0, z0), (bx, 0, z0), (bx, dy, z0), (-bx, dy, z0),
             (-tx, 0, z0+H), (tx, 0, z0+H), (tx, tdy, z0+H), (-tx, tdy, z0+H)]
        f = [(0,1,5,4), (1,2,6,5), (2,3,7,6), (3,0,4,7), (4,5,6,7), (3,2,1,0)]
        return mk(name, v, f, m)
    def strip(name, pts, m, y=0.0):
        return mk(name, [(x, y, z) for x, z in pts], [tuple(range(len(pts)))], m)

    stages = [dict(bx=3.05, dy=2.3, tx=2.8, tdy=2.05, H=1.5, z0=0.0),
              dict(bx=2.1, dy=1.5, tx=1.85, tdy=1.3, H=1.0, z0=1.5)]
    CT = 0.26  # casing thickness
    holder = {}
    core_objs, cas_objs, mats, holes, damp = [], [], [], [], []
    for i, s in enumerate(stages):
        c = half_frustum(f"core{i}", s["bx"]-CT, s["dy"]-CT, s["tx"]-CT, s["tdy"]-CT, s["H"], s["z0"], M_mud)
        core_objs.append(c)
        bx, tx, H, z0 = s["bx"], s["tx"], s["H"], s["z0"]
        bi, ti = bx-CT, tx-CT
        shell = half_frustum(f"shell{i}", bx, s["dy"], tx, s["tdy"], H, z0, M_brick)
        # hollow it: delete the cut face of shell (it would cover the core); rebuild left/right cut strips
        bm = bmesh.new(); bm.from_mesh(shell.data)
        bm.faces.ensure_lookup_table()
        for f in list(bm.faces):
            if f.normal.y < -0.9: bm.faces.remove(f)
        bm.to_mesh(shell.data); bm.free()
        cas_objs.append(shell)
        L_ = strip(f"cutL{i}", [(-bx, z0), (-bi, z0), (-ti, z0+H), (-tx, z0+H)], M_brick)
        R_ = strip(f"cutR{i}", [(bx, z0), (tx, z0+H), (ti, z0+H), (bi, z0)], M_brick)
        cas_objs += [L_, R_]
        # reed mats across the core face
        n = 5
        for k in range(n):
            zz = z0 + H*(k+0.6)/(n+0.2)
            frac = (zz - z0)/H
            hw = (bi + (ti-bi)*frac)
            m_ = mk(f"mat{i}_{k}", [(-hw, -0.012, zz-0.02), (hw, -0.012, zz-0.02), (hw, -0.012, zz+0.02), (-hw, -0.012, zz+0.02)], [(0,1,2,3)], M_mat)
            mats.append((m_, i, k))
        # weep holes through casing strips (dark channels)
        for k in range(4):
            zz = z0 + H*(k+0.9)/4.4
            frac = (zz - z0)/H
            xo = bx + (tx-bx)*frac; xi = bi + (ti-bi)*frac
            for sgn in (-1, 1):
                h_ = mk(f"hole{i}_{k}_{sgn}", [(sgn*xo, -0.014, zz-0.035), (sgn*xi, -0.014, zz-0.035), (sgn*xi, -0.014, zz+0.035), (sgn*xo, -0.014, zz+0.035)], [(0,1,2,3)], M_hole)
                holes.append((h_, sgn))
        # damp overlay
        dm = mk(f"damp{i}", [(-bi, -0.01, z0), (bi, -0.01, z0), (ti, -0.01, z0+H), (-ti, -0.01, z0+H)], [(0,1,2,3)], bpy.data.materials.new(f"dampm{i}"))
        damp.append(dm)
    # damp material: blue translucent, strength keyframed
    dmat = damp[0].data.materials[0]
    for dm in damp:
        mm = dm.data.materials[0]; mm.use_nodes = True
        nt = mm.node_tree; nt.nodes.clear()
        out = nt.nodes.new("ShaderNodeOutputMaterial"); mix = nt.nodes.new("ShaderNodeMixShader")
        tr = nt.nodes.new("ShaderNodeBsdfTransparent"); bl = nt.nodes.new("ShaderNodeBsdfDiffuse")
        bl.inputs["Color"].default_value = (0.02, 0.12, 0.55, 1)
        fac = nt.nodes.new("ShaderNodeValue"); fac.name = "fac"; fac.outputs[0].default_value = 0.0
        nt.links.new(fac.outputs[0], mix.inputs[0]); nt.links.new(tr.outputs[0], mix.inputs[1]); nt.links.new(bl.outputs[0], mix.inputs[2])
        nt.links.new(mix.outputs[0], out.inputs[0])

    # ground
    bpy.ops.mesh.primitive_plane_add(size=600, location=(0, 0, 0)); g = bpy.context.object
    g.data.materials.append(M_ground)
    # scale figure (a worker, 1.7 m)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.035, depth=0.13, location=(-3.9, -1.3, 0.065)); b1 = bpy.context.object; b1.data.materials.append(M_fig)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.03, location=(-3.9, -1.3, 0.16)); b2 = bpy.context.object; b2.data.materials.append(M_fig)
    for o in (b1, b2): o.parent = None

    # stamped brick hero (enlarged for the close-up; stamp pattern illustrative)
    BX, BY = 3.4, -3.6
    hero = mk("hero", [(BX-0.5, BY-0.5, 0), (BX+0.5, BY-0.5, 0), (BX+0.5, BY+0.5, 0), (BX-0.5, BY+0.5, 0),
                       (BX-0.5, BY-0.5, 0.17), (BX+0.5, BY-0.5, 0.17), (BX+0.5, BY+0.5, 0.17), (BX-0.5, BY+0.5, 0.17)],
              [(3,2,1,0), (0,1,5,4), (1,2,6,5), (2,3,7,6), (3,0,4,7), (4,5,6,7)], M_stamp)
    stamps = []
    for r in range(3):
        for c in range(5):
            x0 = BX-0.36+c*0.16; y0 = BY+0.14+ (r-1)*0.13 - 0.0
            w = 0.07 + 0.03*random.random()
            wedge = mk(f"wedge{r}{c}", [(x0, y0, 0.17), (x0+w, y0+0.03, 0.17), (x0, y0+0.06, 0.17), (x0+w*0.6, y0+0.03, 0.2)], [(0,1,3), (1,2,3), (2,0,3), (0,2,1)], M_stamp)
            stamps.append(wedge)
    for cx, cy in ((BX-0.18, BY-0.28), (BX+0.18, BY-0.30)):
        bpy.ops.mesh.primitive_cylinder_add(radius=0.055, depth=0.02, location=(cx, cy, 0.17)); p = bpy.context.object; p.data.materials.append(M_hole)
        for k in range(4):
            ang = math.radians(-70 + k*47)
            bpy.ops.mesh.primitive_cylinder_add(radius=0.022, depth=0.02, location=(cx+0.085*math.cos(ang), cy+0.085*math.sin(ang)+0.03, 0.17)); q = bpy.context.object; q.data.materials.append(M_hole)

    # ---------- world: Nishita sky ----------
    w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
    nt = w.node_tree; sky = nt.nodes.new("ShaderNodeTexSky"); sky.sky_type = "MULTIPLE_SCATTERING"
    sky.sun_elevation = math.radians(9); sky.sun_rotation = math.radians(250); sky.air_density = 1.2; sky.aerosol_density = 1.6; sky.sun_intensity = 0.9
    bg = nt.nodes["Background"]; bg.inputs["Strength"].default_value = 0.22
    nt.links.new(sky.outputs["Color"], bg.inputs["Color"])
    try: sc.view_settings.view_transform = "AgX"
    except Exception: pass
    for lk in ("Medium High Contrast", "AgX - Medium High Contrast"):
        try: sc.view_settings.look = lk; break
        except Exception: pass
    sc.view_settings.exposure = -0.3

    # ---------- camera ----------
    cam_d = bpy.data.cameras.new("cam"); cam_d.lens = 34; cam_d.sensor_width = 36
    cam = bpy.data.objects.new("cam", cam_d); sc.collection.objects.link(cam); sc.camera = cam
    tgt = bpy.data.objects.new("tgt", None); sc.collection.objects.link(tgt)
    tc = cam.constraints.new("TRACK_TO"); tc.target = tgt; tc.track_axis = "TRACK_NEGATIVE_Z"; tc.up_axis = "UP_Y"
    cam_d.dof.use_dof = True; cam_d.dof.focus_object = tgt; cam_d.dof.aperture_fstop = 5.6
    t = lambda k: lines[k][0]; te = lambda k: lines[k][1]
    path = [  # (time, cam pos, target pos)
        (0.0,        (6.0, -27.0, 4.6),  (0.0, 0.0, 0.9)),
        (t(2),       (4.2, -17.0, 3.2),  (0.0, 0.0, 1.0)),
        (t(4),       (2.4, -11.0, 2.2),  (0.0, 0.0, 1.2)),
        (te(5),      (0.8, -8.2, 1.7),   (-0.4, 0.0, 1.3)),
        (t(7),       (2.9, -6.3, 1.2),   (2.9, -3.6, 0.15)),
        (t(8),       (3.3, -5.0, 0.55),  (3.4, -3.6, 0.1)),
        (te(8),      (3.4, -4.6, 0.5),   (3.4, -3.6, 0.1)),
        (t(9),       (3.6, -6.0, 0.9),   (3.0, -2.0, 0.4)),
        (total,      (5.0, -23.0, 4.0),  (0.0, 0.0, 1.0)),
    ]
    for (tt, p, q) in path:
        f = fr(tt); cam.location = p; tgt.location = q
        cam.keyframe_insert("location", frame=f); tgt.keyframe_insert("location", frame=f)

    # ---------- animation ----------
    def key_loc(ob, frame, loc): ob.location = loc; ob.keyframe_insert("location", frame=frame)
    def key_scale(ob, frame, s): ob.scale = s; ob.keyframe_insert("scale", frame=frame)
    def ease(ob, path="location"): pass
    # monument rises out of the ground during hook (core), casing during line 3 (index 3)
    rise_core = (fr(0.4), fr(t(1)+0.9)); rise_cas = (fr(t(3)), fr(t(3)+1.6))
    for o in core_objs:
        key_loc(o, 1, (0, 0, -2.8)); key_loc(o, rise_core[0], (0, 0, -2.8)); key_loc(o, rise_core[1], (0, 0, 0)); ease(o)
    for o in cas_objs:
        key_loc(o, 1, (0, 0, -2.8)); key_loc(o, rise_cas[0], (0, 0, -2.8)); key_loc(o, rise_cas[1], (0, 0, 0)); ease(o)
    # core melt in rain: slump then relax once cased
    for o in core_objs:
        o.scale = (1, 1, 1); o.keyframe_insert("scale", frame=fr(t(2)))
        o.scale = (1.07, 1.07, 0.9); o.keyframe_insert("scale", frame=fr(te(2)))
        o.scale = (1, 1, 1); o.keyframe_insert("scale", frame=fr(t(3)+0.2))
    # damp overlay (line 4) then dry (line 5)
    for dm in damp:
        fv = dm.data.materials[0].node_tree.nodes["fac"].outputs[0]
        for (tt, v) in ((0, 0), (t(4), 0), (t(4)+1.0, 0.4), (t(5)+0.2, 0.4), (t(5)+1.2, 0)):
            fv.default_value = v; fv.keyframe_insert("default_value", frame=fr(tt))
        dm.location = (0, 0, 0)
    # reed mats slide in, holes grow in (line 5)
    for (m_, si, k) in mats:
        a = t(5)+0.3+0.12*(k+si*5)
        m_.scale = (0.001, 1, 1); m_.keyframe_insert("scale", frame=fr(a)-1)
        m_.scale = (1, 1, 1); m_.keyframe_insert("scale", frame=fr(a+0.4))
        m_.hide_render = True; m_.keyframe_insert("hide_render", frame=1)
        m_.hide_render = False; m_.keyframe_insert("hide_render", frame=fr(a)-1)
    for (h_, sgn) in holes:
        a = t(5)+0.1+0.08*random.random()*6
        h_.hide_render = True; h_.keyframe_insert("hide_render", frame=1)
        h_.hide_render = False; h_.keyframe_insert("hide_render", frame=fr(a))
    # worker + stamp brick appear
    for o in [hero] + stamps:
        o.hide_render = True; o.keyframe_insert("hide_render", frame=1)
        o.hide_render = False; o.keyframe_insert("hide_render", frame=fr(t(6)-0.2))
    # stamp wedges 'press in' on line 7
    for o in stamps:
        o.hide_render = True; o.keyframe_insert("hide_render", frame=fr(t(6)-0.2))
        o.hide_render = False; o.keyframe_insert("hide_render", frame=fr(t(7)+0.15))

    # rain curtain parented to camera, scrolling during line 2 (index 2)
    bpy.ops.mesh.primitive_plane_add(size=1); rp = bpy.context.object; rp.name = "rain"
    rp.parent = cam; rp.location = (0, 0, -2.2); rp.scale = (3.2, 5.6, 1)
    rm = bpy.data.materials.new("rain"); rm.use_nodes = True; nt2 = rm.node_tree; nt2.nodes.clear()
    out = nt2.nodes.new("ShaderNodeOutputMaterial"); mix = nt2.nodes.new("ShaderNodeMixShader")
    tr = nt2.nodes.new("ShaderNodeBsdfTransparent"); em = nt2.nodes.new("ShaderNodeEmission"); em.inputs["Color"].default_value = (0.75, 0.85, 1, 1); em.inputs["Strength"].default_value = 1.2
    tco = nt2.nodes.new("ShaderNodeTexCoord"); mp = nt2.nodes.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (500, 2.5, 1)
    no = nt2.nodes.new("ShaderNodeTexNoise"); no.inputs["Scale"].default_value = 1.0; no.inputs["Detail"].default_value = 0
    cr = nt2.nodes.new("ShaderNodeValToRGB"); cr.color_ramp.elements[0].position = 0.66; cr.color_ramp.elements[1].position = 0.72
    mulv = nt2.nodes.new("ShaderNodeMath"); mulv.operation = "MULTIPLY"
    gate = nt2.nodes.new("ShaderNodeValue"); gate.name = "gate"
    nt2.links.new(tco.outputs["UV"], mp.inputs["Vector"]); nt2.links.new(mp.outputs["Vector"], no.inputs["Vector"])
    nt2.links.new(no.outputs["Fac"], cr.inputs["Fac"]); nt2.links.new(cr.outputs["Color"], mulv.inputs[0]); nt2.links.new(gate.outputs[0], mulv.inputs[1])
    nt2.links.new(mulv.outputs[0], mix.inputs[0]); nt2.links.new(tr.outputs[0], mix.inputs[1]); nt2.links.new(em.outputs[0], mix.inputs[2]); nt2.links.new(mix.outputs[0], out.inputs[0])
    rp.data.materials.append(rm)
    gv = gate.outputs[0]
    for (tt, v) in ((0, 0), (t(2)-0.1, 0), (t(2)+0.3, 0.8), (te(2)+0.2, 0.8), (t(3)+0.4, 0)):
        gv.default_value = v; gv.keyframe_insert("default_value", frame=fr(tt))
    bpy.context.preferences.edit.keyframe_new_interpolation_type = "LINEAR"
    mv = mp.inputs["Location"]
    for (tt, v) in ((t(2)-0.1, 0.0), (t(3)+0.4, -12.0)):
        mv.default_value = (0, v, 0); mv.keyframe_insert("default_value", frame=fr(tt))
    bpy.context.preferences.edit.keyframe_new_interpolation_type = "BEZIER"
    rp.hide_render = False
    return dict(fps=FPS, frames=frames, width=1080, height=1920, samples=32)
