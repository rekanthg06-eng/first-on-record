# Proto-cuneiform tablet with seal impressions (The Met 1988.433.1): REAL Met 3D scan (CC0). Route: SCAN.
# Night-archive look: indigo-black void, warm oil-lamp raking key, lapis-blue double rim, black basalt plinth.
# Turntable: front (signs, number holes) -> eased turn to the reverse (rolled seal, raking light) -> eased turn back to the front (loop).
import os, sys, math
def build(bpy, d):
    sys.path.insert(0, os.path.join(d, "..", "lib")); import kit, scanlook
    K = kit.Kit(bpy, d, fps=24, samples=24); T, TE, END = K.t, K.te, K.total
    hd = K.asset("hdri")
    if hd: K.hdri(hd, strength=0.12, rot_deg=120, exposure=-0.5)
    else: K.dark_world(exposure=-0.5)
    K.backdrop(1.0, c=(0.010, 0.011, 0.018), stone=(0.022, 0.021, 0.020))
    key = K.area("key", (-2.0, -1.1, 1.15), (0.0, -0.3, 0.6), 60, size=0.5, color=(1.0, 0.72, 0.45))
    K.area("rimL", (-1.2, 1.6, 1.5), (0, 0, 0.6), 120, size=0.5, color=(0.50, 0.64, 1.0))
    K.area("rimR", (1.35, 1.5, 1.25), (0, 0, 0.55), 72, size=0.5, color=(0.50, 0.64, 1.0))
    fill = K.area("fill", (1.8, -2.2, 0.6), (0, 0, 0.4), 5, size=1.0, color=(0.33, 0.37, 0.50))
    rake = K.area("rake", (1.7, -0.50, 0.55), (-0.3, -0.42, 0.50), 0, size=0.25, color=(1.0, 0.76, 0.52))
    # ---- hero ----
    hero = K.hero_glb(K.asset("hero"), height=1.0)
    hero.location.z -= 0.05      # pillow-shaped base: sink it a little so it sits ON the plinth (no floating gap)
    for o in hero.children:
        if o.type == "MESH":
            for m in o.data.materials: scanlook.grade_scan(m, rough=(0.92, 0.72), spec=0.3)
    # turntable: (time, degrees); eased (smoothstep) between keys
    keys = [(0.0, -20), (T(1), -12), (T(2), -4), (TE(2), 0), (T(4), 4), (TE(4), 6), (T(6), 180), (T(7), 183), (TE(7), 186),
            (T(8) + 0.9, 330), (END, 340)]
    def ang(t):
        for (t0, a0), (t1, a1) in zip(keys, keys[1:]):
            if t <= t1:
                u = 0 if t1 <= t0 else max(0.0, min(1.0, (t - t0) / (t1 - t0)))
                fast = abs(a1 - a0) > 60
                w = u * u * (3 - 2 * u) if fast else u
                return math.radians(a0 + (a1 - a0) * w)
        return math.radians(keys[-1][1])
    K.spin(hero, 0, END, 0, 0, idx=2, steps=int(END * 8), fn=lambda u: ang(u * END))
    # light cues: seal reverse gets a raking light, key dims
    for tt, r, kp, fp in ((0, 0, 60, 5), (TE(4), 0, 60, 5), (TE(4) + 0.6, 30, 6, 0), (T(6) + 0.6, 38, 0, 0), (TE(7), 38, 0, 0), (TE(7) + 0.8, 0, 60, 5)):
        rake.data.energy = r; rake.data.keyframe_insert("energy", frame=K.fr(tt))
        key.data.energy = kp; key.data.keyframe_insert("energy", frame=K.fr(tt))
        fill.data.energy = fp; fill.data.keyframe_insert("energy", frame=K.fr(tt))
    # ---- camera: low 3/4 drift-in -> signs -> macro on number holes -> wide during the turn -> macro on the seal -> back to frame 0 ----
    c0, g0 = (0.85, -3.05, 1.05), (0.04, 0.0, 0.30)
    path = [
        (0.0, c0, g0),
        (T(1), (0.45, -3.15, 1.02), (0.02, 0.0, 0.30)),
        (T(2) + 0.3, (0.06, -3.00, 0.95), (0.0, 0.0, 0.32)),
        (TE(2) + 0.3, (-0.10, -2.70, 1.00), (0.03, 0.0, 0.40)),
        (T(4) + 0.3, (0.05, -1.75, 1.45), (0.16, -0.30, 0.70)),     # macro: round number marks, top right of the front
        (TE(4) + 0.2, (0.03, -1.65, 1.42), (0.16, -0.30, 0.70)),
        (T(6), (-0.20, -3.20, 0.95), (0.0, 0.0, 0.30)),             # wide while it turns
        (T(7) + 0.3, (-0.05, -2.95, 0.70), (0.0, -0.40, 0.42)),     # macro: rolled seal relief on the reverse
        (TE(7), (0.12, -2.85, 0.70), (0.04, -0.40, 0.42)),
        (T(8) + 0.9, (0.62, -3.10, 1.02), (0.03, 0.0, 0.30)),
        (END, c0, g0),
    ]
    cam = K.camera(path, lens=65, fstop=4.5)
    cam.data.sensor_fit = "VERTICAL"; cam.data.sensor_height = 36
    for tt, f in ((0, 4.5), (T(4) - 0.4, 4.5), (T(4) + 0.3, 8.0), (TE(4) + 0.2, 8.0), (T(6) - 0.2, 4.5), (T(7) - 0.4, 4.5), (T(7) + 0.3, 8.0), (TE(7), 8.0), (TE(7) + 0.8, 4.5)):
        cam.data.dof.aperture_fstop = f; cam.data.dof.keyframe_insert("aperture_fstop", frame=K.fr(tt))
    scanlook.bottom_shade(K, cam, 0.88)
    return K.finish()
