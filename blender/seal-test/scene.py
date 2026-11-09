import math, os
def build(bpy, d):
    bpy.ops.import_scene.gltf(filepath=os.path.join(d, "seal.glb"))
    bpy.ops.object.light_add(type="SUN", location=(2, -2, 4)); bpy.context.object.data.energy = 4
    bpy.ops.object.camera_add(location=(0, -5, 1.4), rotation=(1.4, 0, 0))
    cam = bpy.context.object; bpy.context.scene.camera = cam
    cam.keyframe_insert("location", frame=1)
    cam.location = (0, -2.6, 1.0); cam.keyframe_insert("location", frame=150)
    return dict(fps=30, frames=150, width=1080, height=1920, samples=32)
