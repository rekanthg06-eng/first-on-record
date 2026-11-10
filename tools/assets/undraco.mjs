// Decompress Draco (and meshopt-free) GLBs so Blender's pip build (no Draco library) can import them.
// node tools/assets/undraco.mjs in.glb out.glb   (needs: npm i @gltf-transform/core @gltf-transform/extensions draco3dgltf)
import { NodeIO } from '@gltf-transform/core';
import { ALL_EXTENSIONS } from '@gltf-transform/extensions';
import draco3d from 'draco3dgltf';
const [, , inp, out] = process.argv;
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({ 'draco3d.decoder': await draco3d.createDecoderModule() });
const doc = await io.read(inp);
for (const ext of doc.getRoot().listExtensionsUsed()) if (ext.extensionName === 'KHR_draco_mesh_compression') ext.dispose();
await io.write(out, doc);
console.log('undraco ok', out);
