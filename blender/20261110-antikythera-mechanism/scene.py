# Antikythera mechanism build-up (RECONSTRUCTION, exploded/cut-away, not to scale). 1 unit ~ 10 cm. One continuous dolly, no cuts. Uses blender/lib/kit.py
import os, sys, math
def build(bpy, d):
    sys.path.insert(0, os.path.join(d, "..", "lib")); import kit
    K = kit.Kit(bpy, d, fps=24, samples=24); T, TE, END = K.t, K.te, None
    END = K.total
    M_wood = K.noisy("wood", (0.36, 0.22, 0.11), scale=6, contrast=0.35, bump=0.25, rough=0.8)
    M_wood.node_tree.nodes["Noise Texture"].inputs["Detail"].default_value = 3
    M_br = K.metal("bronze", (0.72, 0.45, 0.20), rough=0.32)
    M_br2 = K.metal("bronze_dark", (0.48, 0.30, 0.14), rough=0.45)
    M_patina = K.noisy("patina", (0.28, 0.42, 0.34), scale=20, contrast=0.4, bump=0.4)
    M_stone = K.noisy("terrace", (0.42, 0.38, 0.32), scale=3, contrast=0.25, bump=0.3)
    M_sea = K.plain("sea", (0.03, 0.12, 0.20), 0.12)
    M_slot = K.plain("slot", (0.02, 0.015, 0.01), 1.0)
    M_moon = K.noisy("moon", (0.55, 0.58, 0.62), scale=8, contrast=0.3, bump=0.3, rough=1.0)
    M_sun = K.emit("sun", (1.0, 0.45, 0.08), 2.2)
    M_cell = K.metal("cell", (0.60, 0.40, 0.18), rough=0.5); M_ecl = K.emit("ecl", (1.0, 0.75, 0.35), 2.5)
    K.world(sun_el=11, sun_rot=215, strength=0.20, exposure=-0.9)
    K.ground(M_stone, size=60, dunes=False)
    bpy.ops.mesh.primitive_plane_add(size=3000, location=(0, 0, -1.5)); sea = bpy.context.object; sea.name = "sea"; sea.data.materials.append(M_sea)
    # warm key light from front-left so the inside of the case reads
    ld = bpy.data.lights.new("key", "AREA"); ld.energy = 120; ld.size = 4; ld.color = (1.0, 0.86, 0.7)
    lo = bpy.data.objects.new("key", ld); K.sc.collection.objects.link(lo); lo.location = (-4, -7, 7); lo.rotation_euler = (math.radians(50), 0, math.radians(-30))
    # ---- props for scale on the terrace (tools, lamp, stool) ----
    K.cyl("lamp", 0.35, 0.25, (2.6, 1.2, 0.125), K.plain("clay", (0.55, 0.30, 0.18), 0.9), seg=20)
    K.cyl("file", 0.06, 2.2, (-1.4, -1.6, 0.06), M_br2, rot=(0, math.pi/2, 0.4), seg=10)
    K.cyl("awl", 0.04, 1.4, (1.6, -2.2, 0.05), M_br2, rot=(0, math.pi/2, -0.7), seg=8)
    K.scatter("chip", M_br2, 25, (-3, 3, -3, 0.5), (0.03, 0.07), avoid=lambda x, y: abs(x) < 1.3 and abs(y) < 1.0)
    # ---- wooden case, front open (cut-away): portrait 18 x 34 x 9 cm ----
    W, H, D, Z0, tw = 1.8, 3.4, 0.9, 0.15, 0.08
    case = [K.box("back", W, tw, H, (0, D - tw/2, Z0), M_wood), K.box("sideL", tw, D, H, (-W/2 + tw/2, D/2, Z0), M_wood),
            K.box("sideR", tw, D, H, (W/2 - tw/2, D/2, Z0), M_wood), K.box("bot", W, D, tw, (0, D/2, Z0), M_wood), K.box("top", W, D, tw, (0, D/2, Z0 + H - tw), M_wood)]
    for x in (-0.7, 0.7):
        for y in (0.15, 0.75): K.box("foot", 0.18, 0.18, Z0, (x, y, 0), M_wood)
    # crank on the right side (turns about x)
    crank = bpy.data.objects.new("crank", None); K.sc.collection.objects.link(crank); crank.location = (W/2 + 0.02, D/2, 1.75)
    parts = [K.cyl("c_axle", 0.05, 0.35, (W/2 + 0.17, D/2, 1.75), M_br2, rot=(0, math.pi/2, 0), seg=12),
             K.box("c_arm", 0.06, 0.08, 0.55, (W/2 + 0.32, D/2, 1.75), M_br2), K.cyl("c_knob", 0.06, 0.28, (W/2 + 0.45, D/2, 2.25), M_wood, rot=(0, math.pi/2, 0), seg=12)]
    for p in parts: p.parent = crank; p.matrix_parent_inverse = crank.matrix_world.inverted()
    # ---- gear train inside (y layers so nothing intersects); b1 = 223-tooth main wheel ----
    Y1, Y2, Y3 = 0.62, 0.48, 0.34
    G = [dict(n="b1", r=0.62, t=223, p=(0.0, Y1, 1.75)),
         dict(n="c1", r=0.30, t=48, p=(-0.15, Y2, 2.75)), dict(n="e1", r=0.24, t=32, p=(-0.52, Y2, 1.05)),
         dict(n="d1", r=0.20, t=24, p=(0.45, Y2, 0.85)), dict(n="m1", r=0.34, t=96, p=(-0.38, Y3, 2.15)),
         dict(n="l1", r=0.16, t=38, p=(0.40, Y3, 1.40))]
    gears = []
    for i, g in enumerate(G):
        o = K.gear(g["n"], g["r"], g["t"], 0.035, g["p"], M_br if i % 2 == 0 else M_br2)
        ax = K.cyl(g["n"] + "_ax", 0.03, D - 0.1, (g["p"][0], D/2, g["p"][2]), M_br2, rot=(math.pi/2, 0, 0), seg=10)
        gears.append((o, g, ax))
    # spokes on b1 (blank, no inscriptions)
    b1 = gears[0][0]
    for k in range(4):
        sp = K.box("spoke", 0.07, 0.03, 1.1, (0, 0, -0.55), M_br); sp.parent = b1; sp.location = (0, 0, 0); sp.rotation_euler = (0, k * math.pi/4 + math.pi/8, 0)
    # ---- pin-and-slot pair k1/k2 (centres offset; k2 runs unevenly) ----
    KX, KZ, KY = 0.42, 2.85, 0.22
    k1 = K.gear("k1", 0.22, 50, 0.03, (KX, KY + 0.04, KZ), M_br)
    k2 = K.gear("k2", 0.22, 50, 0.03, (KX + 0.06, KY - 0.04, KZ), M_br2)
    pin = K.cyl("pin", 0.025, 0.14, (KX + 0.13, KY, KZ), M_br2, rot=(math.pi/2, 0, 0), seg=10); pin.parent = k1; pin.matrix_parent_inverse = k1.matrix_world.inverted()
    slot = K.box("slot", 0.30, 0.012, 0.05, (KX + 0.06 + 0.04, KY - 0.06, KZ - 0.025), M_slot); slot.parent = k2; slot.matrix_parent_inverse = k2.matrix_world.inverted()
    # magnified chunk of the pin-and-slot on a plinth (the macro dive)
    CX, CY, SC = 3.3, -1.2, 3.2
    plinth = K.box("plinth", 1.8, 1.2, 0.5, (CX, CY + 0.3, 0), M_stone)
    mk1 = K.gear("mk1", 0.22*SC, 50, 0.03*SC, (CX - 0.03*SC, CY + 0.06*SC, 0.5 + 0.26*SC), M_br)
    mk2 = K.gear("mk2", 0.22*SC, 50, 0.03*SC, (CX + 0.03*SC, CY - 0.02*SC, 0.5 + 0.26*SC), M_patina)
    mpin = K.cyl("mpin", 0.025*SC, 0.14*SC, (CX - 0.03*SC + 0.13*SC, CY + 0.02*SC, 0.5 + 0.26*SC), M_br2, rot=(math.pi/2, 0, 0), seg=16)
    mpin.parent = mk1; mpin.matrix_parent_inverse = mk1.matrix_world.inverted()
    mslot = K.box("mslot", 0.30*SC, 0.006*SC, 0.05*SC, (CX + 0.03*SC + 0.04*SC, CY - 0.038*SC, 0.5 + 0.26*SC - 0.025*SC), M_slot)
    mslot.parent = mk2; mslot.matrix_parent_inverse = mk2.matrix_world.inverted()
    mpost = K.cyl("mpost", 0.05*SC, 0.26*SC, (CX, CY + 0.15, 0.5 + 0.13*SC), M_br2, seg=12)
    # ---- sky: sun + moon on an orbit above the case ----
    sun = K.sphere("sunball", 0.34, (0, 0.6, 4.9), M_sun)
    orb = bpy.data.objects.new("orbit", None); K.sc.collection.objects.link(orb); orb.location = (0, 0.5, 4.85)
    moon = K.sphere("moonball", 0.30, (0, -1.0, 4.85), M_moon); moon.parent = orb; moon.matrix_parent_inverse = orb.matrix_world.inverted()
    # ---- exploded back plate: Saros spiral (223 cells, 4 turns), blank cells, eclipse cells glow ----
    PX, PZ = -2.6, 1.85
    plate = K.box("plate", 1.6, 0.08, 2.9, (PX, 0.25, 0.4), M_patina)
    cells, ecl = [], []
    for i in range(223):
        u = i / 223; a = -u * 4 * 2 * math.pi + math.pi/2; r = 0.22 + 0.5 * u
        it = (0.045, 0.02, 0.045, (PX + r * math.cos(a), 0.2, PZ + r * math.sin(a) - 0.022))
        (ecl if (i * 51) % 223 < 51 else cells).append(it)
    M_cells = K.boxes("cells", cells, M_cell); M_ecls = K.boxes("eclcells", ecl, M_ecl)
    ptr = bpy.data.objects.new("ptr", None); K.sc.collection.objects.link(ptr); ptr.location = (PX, 0.17, PZ)
    pb = K.box("pointer", 0.03, 0.02, 0.75, (PX, 0.17, PZ), M_br); pb.parent = ptr; pb.matrix_parent_inverse = ptr.matrix_world.inverted()

    # ===== animation by line: 0 crank / 1 greeks / 2 sky cycles / 3 gears / 4 moon uneven / 5 pin-slot / 6 eclipse / 7 saros / 8 divers / 9 finish
    for o in case: pass   # the case is there from frame 1 (striking first frame: open case + crank)
    tg = T(3)
    for i, (o, g, ax) in enumerate(gears):
        K.pop(o, tg + 0.25 * i, tg + 0.25 * i + 0.45); K.pop(ax, tg + 0.25 * i, tg + 0.25 * i + 0.45)
    t_run = T(3) + 1.8
    K.spin(crank, 0, t_run, 0, 0, idx=0); K.spin(crank, t_run, END, 0, -(END - t_run) * 2.4, idx=0)
    w = 0.9   # b1 rad/s
    for i, (o, g, ax) in enumerate(gears):
        sgn = 1 if i in (0, 4) else -1; rate = w * G[0]["r"] / g["r"] * sgn if i else w
        K.spin(o, t_run, END, 0, rate * (END - t_run))
    # sky: sun/moon appear on line 2; moon orbit (even), uneven on line 4
    K.pop(sun, T(2), T(2) + 0.5); K.pop(moon, T(2), T(2) + 0.5)
    def orbit_ang(t):
        return 1.6 * t
    a4 = 1.6 + 1.6 * (T(4) - T(2))   # start at the side (no early eclipse)
    K.spin(orb, T(2), T(4), 1.6, a4, idx=2)
    K.spin(orb, T(4), T(6), a4, a4 + 6.0, idx=2, fn=lambda u: a4 + 6.0 * u + 0.9 * math.sin(2 * math.pi * 2 * u))
    # eclipse: moon passes in front of the sun on line 6, sun dims
    a6 = a4 + 6.0; frontA = math.ceil((a6) / (2 * math.pi)) * 2 * math.pi   # angle where moon is at y=-1 (front)
    K.spin(orb, T(6), TE(6) + 0.3, a6, frontA, idx=2)
    K.spin(orb, TE(6) + 0.3, END, frontA, frontA + 1.4 * (END - TE(6)), idx=2)
    for (tt, z) in ((0, 5.75), (T(6) - 0.2, 5.75), (T(6) + 0.6, 4.85), (T(7) + 0.3, 4.85), (T(7) + 1.3, 5.75)): K.key(orb, "location", tt, (0, 0.5, z))
    es = M_sun.node_tree.nodes["Emission"].inputs["Strength"]
    for (tt, v) in ((0, 2.2), (T(6) + 0.6, 2.2), (TE(6), 0.25), (TE(6) + 0.6, 0.25), (T(7) + 0.4, 2.2)): K.key_socket(es, tt, v)
    # pin-and-slot appears on line 5 and runs unevenly; magnified chunk too
    for o in (k1, k2): K.pop(o, T(5), T(5) + 0.5)
    for o in (plinth, mk1, mk2, mpost): K.pop(o, T(5) + 0.4, T(5) + 1.0)
    def follow(base):   # k2 angle that keeps its slot on k1's pin (pin radius 0.13, centre offset 0.06)
        def f(u):
            a1 = base * u; a2 = math.atan2(0.13 * math.sin(a1), 0.13 * math.cos(a1) - 0.06)
            return a1 + (a2 - a1 + math.pi) % (2 * math.pi) - math.pi
        return f
    uneven = follow
    ang = 1.3 * (END - T(5))
    K.spin(k1, T(5) + 0.6, END, 0, ang); K.spin(k2, T(5) + 0.6, END, 0, 0, fn=uneven(ang), steps=int((END - T(5)) * 6))
    K.spin(mk1, T(5) + 1.0, END, 0, ang); K.spin(mk2, T(5) + 1.0, END, 0, 0, fn=uneven(ang), steps=int((END - T(5)) * 6))
    # Saros plate on line 7; pointer sweeps the spiral
    for o in (plate, M_cells, M_ecls): K.pop(o, T(7), T(7) + 0.6)
    K.pop(pb, T(7) + 0.3, T(7) + 0.8); K.spin(ptr, T(7) + 0.8, END, 0, -(END - T(7)) * 1.5)
    # ===== ONE continuous dolly: wide -> sky -> in on gears -> macro pin-and-slot -> eclipse -> Saros plate -> pull back to start
    K.camera([(0.0, (0.9, -9.0, 2.6), (0.2, 0.4, 2.1)), (T(2), (0.5, -9.5, 3.4), (0, 0.4, 3.0)),
              (T(3) + 0.4, (0.4, -6.0, 2.4), (0, 0.45, 1.9)), (T(4), (0.3, -6.6, 3.2), (0.1, 0.3, 3.2)),
              (T(5) + 0.3, (0.6, -4.4, 3.0), (KX - 0.2, KY, KZ - 0.2)), (T(5) + 1.6, (3.1, -4.6, 1.6), (CX, CY, 1.3)),
              (TE(5) + 0.2, (3.3, -3.9, 1.45), (CX, CY, 1.3)), (T(6) + 0.3, (0.3, -8.0, 3.8), (0, 0.4, 4.4)), (TE(6) + 0.3, (0.2, -7.8, 3.9), (0, 0.4, 4.5)),
              (T(7) + 0.3, (-2.9, -6.0, 2.3), (PX, 0.2, PZ)), (TE(7), (-2.9, -5.0, 2.1), (PX, 0.2, PZ)),
              (T(9), (0.3, -8.6, 2.7), (-0.2, 0.4, 2.2)), (END, (0.9, -9.0, 2.6), (0.2, 0.4, 2.1))], lens=32, fstop=4.0)
    return K.finish()
