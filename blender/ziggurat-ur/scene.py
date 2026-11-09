# Ziggurat of Ur build-up (RECONSTRUCTION, cut-away). 1 unit ~ 10 m. One continuous dolly, no cuts. Uses blender/lib/kit.py
import os, sys, math
def build(bpy, d):
    sys.path.insert(0, os.path.join(d, "..", "lib")); import kit
    K = kit.Kit(bpy, d, fps=24, samples=24); T, TE = K.t, K.te
    M_mud = K.brick("mudbrick", (0.52, 0.37, 0.21), (0.45, 0.32, 0.18), (0.30, 0.20, 0.12), scale=(7, 14), mortar_size=0.05)
    M_baked = K.brick("baked", (0.58, 0.22, 0.10), (0.46, 0.17, 0.08), (0.02, 0.018, 0.015), scale=(9, 18), mortar_size=0.07, bump=0.9)
    M_chunk = K.brick("baked_big", (0.58, 0.22, 0.10), (0.46, 0.17, 0.08), (0.02, 0.018, 0.015), scale=(2.4, 3.6), mortar_size=0.03, bump=0.8)
    M_chunk_mud = K.brick("mud_big", (0.52, 0.37, 0.21), (0.45, 0.32, 0.18), (0.30, 0.20, 0.12), scale=(2.4, 3.6), mortar_size=0.05)
    M_reed, M_hole = K.straw("reed"), K.plain("hole", (0.01, 0.008, 0.006), 1.0)
    M_ground = K.noisy("ground", (0.64, 0.52, 0.34), scale=30, contrast=0.3, bump=0.5)
    M_stamp = K.noisy("stampbrick", (0.42, 0.17, 0.08), scale=40, contrast=0.3, bump=0.3); M_paw = K.plain("paw", (0.20, 0.07, 0.03), 1.0)
    K.world(); K.ground(M_ground)
    K.scatter("rock", K.plain("rock", (0.45, 0.36, 0.26), 1.0), 160, (-30, 30, -30, 10), (0.02, 0.07), avoid=lambda x, y: abs(x) < 4 and -2 < y < 4)

    stages = [dict(bx=3.05, dy=2.3, tx=2.8, tdy=2.05, H=1.5, z0=0.0), dict(bx=2.1, dy=1.5, tx=1.85, tdy=1.3, H=1.0, z0=1.5)]
    CT = 0.26
    core, cas, mats, holes, damp = [], [], [], [], []
    dm_mat = K.fade_mat("damp", (0.02, 0.12, 0.55))
    for i, s in enumerate(stages):
        bx, tx, H, z0 = s["bx"], s["tx"], s["H"], s["z0"]; bi, ti = bx - CT, tx - CT
        core.append(K.half_frustum(f"core{i}", bi, s["dy"]-CT, ti, s["tdy"]-CT, H, z0, M_mud))
        shell = K.half_frustum(f"shell{i}", bx, s["dy"], tx, s["tdy"], H, z0, M_baked)
        import bmesh
        bm = bmesh.new(); bm.from_mesh(shell.data); bm.faces.ensure_lookup_table()
        for f in list(bm.faces):
            if f.normal.y < -0.9: bm.faces.remove(f)
        bm.to_mesh(shell.data); bm.free()
        cas += [shell, K.poly(f"cutL{i}", [(-bx, z0), (-bi, z0), (-ti, z0+H), (-tx, z0+H)], M_baked), K.poly(f"cutR{i}", [(bx, z0), (tx, z0+H), (ti, z0+H), (bi, z0)], M_baked)]
        for k in range(5):
            zz = z0 + H*(k+0.6)/5.2; hw = bi + (ti-bi)*(zz-z0)/H
            mats.append((K.mk(f"mat{i}_{k}", [(-hw, -0.012, zz-0.022), (hw, -0.012, zz-0.022), (hw, -0.012, zz+0.022), (-hw, -0.012, zz+0.022)], [(0,1,2,3)], M_reed), i, k))
        for k in range(4):
            zz = z0 + H*(k+0.9)/4.4; fr_ = (zz-z0)/H; xo = bx+(tx-bx)*fr_; xi = bi+(ti-bi)*fr_
            for sg in (-1, 1):
                holes.append(K.mk(f"hole{i}_{k}_{sg}", [(sg*xo, -0.014, zz-0.035), (sg*xi, -0.014, zz-0.035), (sg*xi, -0.014, zz+0.035), (sg*xo, -0.014, zz+0.035)], [(0,1,2,3)], M_hole))
        damp.append(K.mk(f"damp{i}", [(-bi, -0.01, z0), (bi, -0.01, z0), (ti, -0.01, z0+H), (-ti, -0.01, z0+H)], [(0,1,2,3)], dm_mat))

    # magnified chunk (a diorama of the wall section: baked courses + bitumen joints, reed mat, mud core, stamped brick on top)
    CX, CY = 3.5, -3.4
    chunk = [K.box("cb1", 1.0, 0.3, 0.21, (CX, CY, 0), M_chunk), K.box("cr", 1.0, 0.3, 0.03, (CX, CY, 0.21), M_reed), K.box("cb2", 1.0, 0.3, 0.21, (CX, CY, 0.24), M_chunk),
             K.box("cm", 1.0, 0.34, 0.45, (CX, CY+0.32, 0), M_chunk_mud)]
    top = K.box("stampbrick", 0.55, 0.5, 0.07, (CX, CY+0.05, 0.45), M_stamp); chunk.append(top)
    for k, (w, d_, x, y) in enumerate(((0.45, 0.012, 0, -0.16), (0.45, 0.012, 0, 0.0), (0.012, 0.16, -0.225, -0.08), (0.012, 0.16, 0.225, -0.08))):
        chunk.append(K.box(f"cart{k}", w, d_, 0.012, (CX+x, CY+0.05+y+0.08, 0.52), M_stamp))
    for (px, py) in ((-0.13, 0.12), (0.12, 0.12)):
        chunk.append(K.cyl("pad", 0.04, 0.004, (CX+px, CY+0.05+py, 0.521), M_paw, seg=24))
        for a in (-60, -20, 20, 60):
            chunk.append(K.cyl("toe", 0.016, 0.004, (CX+px+0.062*math.sin(math.radians(a)), CY+0.05+py+0.062*math.cos(math.radians(a)), 0.521), M_paw, seg=12))
    # workers carrying bricks past the monument (life + human scale)
    crowd = []
    for n in range(9):
        w = K.person((0, 0, 0), (0.5+0.04*n % 0.3, 0.38, 0.30), carry=M_baked); crowd.append(w)
        x0 = 5.5 - n*1.3; K.walk(w, (x0, -1.15 - 0.15*(n % 3), 0), (x0 - 7.5, -1.15 - 0.15*(n % 3), 0), 0, K.total)
        # pause: they re-enter by looping start offset (keys only span the clip)

    # animation by narration line: 0 'how' / 1 king / 2 rain / 3 casing / 4 damp / 5 holes+mats / 6 whose / 7 stamp / 8 BM / 9 outro
    for o in core: K.rise(o, 0.4, T(1)+0.9, 2.8)
    for o in cas: K.rise(o, T(3), T(3)+1.6, 2.8)
    for o in core:
        K.key(o, "scale", T(2), (1, 1, 1)); K.key(o, "scale", TE(2), (1.07, 1.07, 0.9)); K.key(o, "scale", T(3)+0.2, (1, 1, 1))
    for dm in damp:
        for (tt, v) in ((0, 0), (T(4), 0), (T(4)+1.0, 0.4), (T(5)+0.2, 0.4), (T(5)+1.2, 0)): K.key_socket(dm_mat.node_tree.nodes["fac"].outputs[0], tt, v)
    for (m_, si, k) in mats: K.grow_x(m_, T(5)+0.3+0.12*(k+si*5), T(5)+0.7+0.12*(k+si*5))
    for h_ in holes: K.show(h_, T(5)+0.1+0.4*K.rnd())
    for o in chunk:
        K.show(o, T(5)+1.2); 
    # ONE continuous dolly (no orbit, no cut): wide -> in on the section -> macro chunk -> long pull-back to the start framing
    K.camera([(0.0, (6.0, -27.0, 4.6), (0, 0, 0.9)), (T(2), (4.2, -17.0, 3.2), (0, 0, 1.0)), (T(4), (2.4, -11.0, 2.2), (0, 0, 1.2)),
              (TE(5), (1.8, -8.0, 1.6), (1.0, 0, 1.2)), (T(7), (3.5, -5.6, 0.9), (CX, CY, 0.3)), (T(8), (3.55, -4.6, 0.75), (CX, CY, 0.4)),
              (TE(8), (3.5, -4.3, 0.85), (CX, CY, 0.42)), (T(9), (3.9, -6.5, 1.3), (3.0, -2.0, 0.5)), (K.total, (5.0, -23.0, 4.0), (0, 0, 1.0))])
    K.rain(T(2), T(3)+0.4)   # after K.camera (it parents to the camera)
    return K.finish()
