"""Real-scan look helpers (v2, 2026-11-10): grade_scan(material) uses the scan's own baked AO for albedo contrast and roughness;
bottom_shade(K, cam) darkens the caption band (72-82 % of the height) with a camera-parented gradient card (no compositor needed)."""
import math

def grade_scan(m, rough=(0.85, 0.42), spec=0.6):
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
        mr = nt.nodes.new("ShaderNodeMapRange"); mr.inputs["To Min"].default_value = rough[0]; mr.inputs["To Max"].default_value = rough[1]
        nt.links.new(ao, mr.inputs["Value"]); nt.links.new(mr.outputs["Result"], b.inputs["Roughness"])
    else:
        mul.inputs["B"].default_value = (0.8, 0.8, 0.8, 1); b.inputs["Roughness"].default_value = 0.55
    hs = nt.nodes.new("ShaderNodeHueSaturation"); hs.inputs["Value"].default_value = 0.82; hs.inputs["Saturation"].default_value = 0.92
    nt.links.new(mul.outputs["Result"], hs.inputs["Color"]); nt.links.new(hs.outputs["Color"], b.inputs["Base Color"])
    try: b.inputs["Specular IOR Level"].default_value = spec
    except Exception: pass

def bottom_shade(K, cam, strength=0.8):
    """camera-parented gradient card: darkens the lower frame (caption band 72-82 %) by up to ~60 %; a grade, not a texture"""
    bpy = K.bpy; dist = 0.25; fh = 2 * dist * 18 / cam.data.lens; fw = fh * 9 / 16   # assumes sensor_fit VERTICAL, 36 mm (or AUTO in portrait)
    bpy.ops.mesh.primitive_plane_add(size=1); p = bpy.context.object; p.name = "shade"; p.parent = cam
    p.location = (0, 0, -dist); p.scale = (fw * 1.1, fh * 1.02, 1)
    m = bpy.data.materials.new("shade"); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial"); mix = nt.nodes.new("ShaderNodeMixShader")
    tr = nt.nodes.new("ShaderNodeBsdfTransparent"); bk = nt.nodes.new("ShaderNodeEmission"); bk.inputs["Color"].default_value = (0, 0, 0, 1)
    tc = nt.nodes.new("ShaderNodeTexCoord"); sx = nt.nodes.new("ShaderNodeSeparateXYZ"); cr = nt.nodes.new("ShaderNodeValToRGB")
    nt.links.new(tc.outputs["UV"], sx.inputs["Vector"]); nt.links.new(sx.outputs["Y"], cr.inputs["Fac"])
    els = cr.color_ramp.elements; els[0].position = 0.08; els[0].color = (strength * 0.78, strength * 0.78, strength * 0.78, 1); els[1].position = 0.46; els[1].color = (0, 0, 0, 1)
    e = els.new(0.24); e.color = (strength, strength, strength, 1)
    nt.links.new(cr.outputs["Color"], mix.inputs[0]); nt.links.new(tr.outputs[0], mix.inputs[1]); nt.links.new(bk.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs[0]); p.data.materials.append(m)
    p.visible_shadow = False; p.visible_diffuse = False; p.visible_glossy = False; p.visible_transmission = False
    try: m.blend_method = "BLEND"
    except Exception: pass
    return p
