/* 신체 GLB에 의류 GLB를 입혀 한 파일로 만든다.
   3D팀 뷰어(src/web.js의 fitGarment)와 같은 규칙: 의류의 fit_anchor를 신체의 fit_anchor
   (하의는 fit_anchor_waist)에 겹치는 강체 변환이며 크기는 바꾸지 않는다. */

function parse(buffer) {
  const view = new DataView(buffer);
  if (buffer.byteLength < 20 || view.getUint32(0, true) !== 0x46546c67 || view.getUint32(4, true) !== 2) {
    throw Error("GLB 파일 형식이 아니에요.");
  }
  const jsonLength = view.getUint32(12, true);
  const json = JSON.parse(new TextDecoder().decode(new Uint8Array(buffer, 20, jsonLength)));
  const binStart = 20 + jsonLength;
  let bin = new Uint8Array(0);
  if (binStart + 8 <= buffer.byteLength) {
    const length = view.getUint32(binStart, true);
    if (view.getUint32(binStart + 4, true) !== 0x004e4942) throw Error("GLB 데이터 영역을 읽을 수 없어요.");
    bin = new Uint8Array(buffer, binStart + 8, length);
  }
  if ((json.buffers?.length ?? 0) > 1 || json.buffers?.[0]?.uri) throw Error("외부 버퍼를 쓰는 GLB는 합칠 수 없어요.");
  return {json, bin};
}

// 열 우선 4x4 행렬 (glTF 규칙)
function multiply(a, b) {
  const out = new Array(16).fill(0);
  for (let c = 0; c < 4; c++) for (let r = 0; r < 4; r++) for (let k = 0; k < 4; k++) out[c * 4 + r] += a[k * 4 + r] * b[c * 4 + k];
  return out;
}

function fromTrs({translation: t = [0, 0, 0], rotation: q = [0, 0, 0, 1], scale: s = [1, 1, 1]} = {}) {
  const [x, y, z, w] = q;
  return [
    (1 - 2 * (y * y + z * z)) * s[0], 2 * (x * y + z * w) * s[0], 2 * (x * z - y * w) * s[0], 0,
    2 * (x * y - z * w) * s[1], (1 - 2 * (x * x + z * z)) * s[1], 2 * (y * z + x * w) * s[1], 0,
    2 * (x * z + y * w) * s[2], 2 * (y * z - x * w) * s[2], (1 - 2 * (x * x + y * y)) * s[2], 0,
    t[0], t[1], t[2], 1,
  ];
}

// 아핀 변환(마지막 행 0,0,0,1)의 역행렬
function invert(m) {
  const [a, b, c, , d, e, f, , g, h, i, , tx, ty, tz] = m;
  const A = e * i - f * h, B = f * g - d * i, C = d * h - e * g;
  const det = a * A + b * B + c * C;
  if (!Number.isFinite(det) || Math.abs(det) < 1e-12) throw Error("기준점 변환을 계산할 수 없어요.");
  const r = [A / det, (c * h - b * i) / det, (b * f - c * e) / det,
    B / det, (a * i - c * g) / det, (c * d - a * f) / det,
    C / det, (b * g - a * h) / det, (a * e - b * d) / det];
  return [r[0], r[1], r[2], 0, r[3], r[4], r[5], 0, r[6], r[7], r[8], 0,
    -(r[0] * tx + r[3] * ty + r[6] * tz), -(r[1] * tx + r[4] * ty + r[7] * tz), -(r[2] * tx + r[5] * ty + r[8] * tz), 1];
}

const nodeMatrix = node => node.matrix ?? fromTrs(node);

function rootOf(json, name) {
  const scene = json.scenes?.[json.scene ?? 0];
  const index = scene?.nodes?.length === 1 ? scene.nodes[0] : -1;
  const node = json.nodes?.[index];
  if (!node || node.name !== name) throw Error("모델의 기준 노드를 찾을 수 없어요.");
  return {index, node};
}

function anchorOf(json, root, name) {
  const index = (root.children ?? []).find(child => json.nodes[child]?.name === name);
  if (index === undefined) throw Error("피팅 기준점이 없어요: " + name);
  return index;
}

export function mergeFitted(bodyBuffer, bodyAnchors, garmentBuffer, garmentAnchors, lowerBody = false) {
  const body = parse(bodyBuffer), garment = parse(garmentBuffer);
  const blocked = [...(garment.json.extensionsRequired ?? []), ...(body.json.extensionsRequired ?? [])];
  if (blocked.length) throw Error("압축된 모델은 합칠 수 없어요: " + blocked.join(", "));
  const out = body.json, add = garment.json;
  const fitting = add.scenes?.[add.scene ?? 0]?.extras?.fitme_garment;
  if (["db_cloth_collision", "sam_body_cloth_collision"].includes(fitting?.fitting_mode)
      && fitting.body_model_id !== bodyAnchors.model_sha256)
    throw Error("이 옷은 다른 신체에서 시뮬레이션한 결과예요. 다시 생성해 주세요.");
  const offset = Math.ceil(body.bin.byteLength / 4) * 4;
  const base = {};
  for (const key of ["bufferViews", "accessors", "images", "samplers", "textures", "materials", "meshes", "nodes", "skins"]) {
    base[key] = out[key]?.length ?? 0;
  }
  const shift = (object, key, kind) => { if (Number.isInteger(object?.[key])) object[key] += base[kind]; };
  const copy = value => JSON.parse(JSON.stringify(value ?? []));

  const bufferViews = copy(add.bufferViews);
  for (const view of bufferViews) { view.buffer = 0; view.byteOffset = (view.byteOffset ?? 0) + offset; }
  const accessors = copy(add.accessors);
  for (const accessor of accessors) {
    shift(accessor, "bufferView", "bufferViews");
    shift(accessor.sparse?.indices, "bufferView", "bufferViews");
    shift(accessor.sparse?.values, "bufferView", "bufferViews");
  }
  const images = copy(add.images);
  for (const image of images) shift(image, "bufferView", "bufferViews");
  const textures = copy(add.textures);
  for (const texture of textures) { shift(texture, "source", "images"); shift(texture, "sampler", "samplers"); }
  const materials = copy(add.materials);
  for (const material of materials) {
    for (const info of [material.pbrMetallicRoughness?.baseColorTexture, material.pbrMetallicRoughness?.metallicRoughnessTexture,
      material.normalTexture, material.occlusionTexture, material.emissiveTexture]) shift(info, "index", "textures");
  }
  const meshes = copy(add.meshes);
  for (const mesh of meshes) {
    for (const primitive of mesh.primitives ?? []) {
      shift(primitive, "indices", "accessors");
      shift(primitive, "material", "materials");
      for (const set of [primitive.attributes, ...(primitive.targets ?? [])]) {
        for (const key of Object.keys(set ?? {})) set[key] += base.accessors;
      }
    }
  }
  const skins = copy(add.skins);
  for (const skin of skins) {
    shift(skin, "inverseBindMatrices", "accessors");
    shift(skin, "skeleton", "nodes");
    skin.joints = (skin.joints ?? []).map(joint => joint + base.nodes);
  }
  const nodes = copy(add.nodes);
  for (const node of nodes) {
    shift(node, "mesh", "meshes");
    shift(node, "skin", "skins");
    delete node.camera;
    if (node.children) node.children = node.children.map(child => child + base.nodes);
  }

  const anchorName = lowerBody ? "fit_anchor_waist" : "fit_anchor";
  const bodyRoot = rootOf(out, bodyAnchors.parent_node);
  const garmentRoot = rootOf(add, garmentAnchors.parent_node);
  const target = anchorOf(out, bodyRoot.node, anchorName);
  const source = add.nodes[anchorOf(add, garmentRoot.node, anchorName)];
  // 의류 장면에서 본 의류 기준점의 역변환을 신체 기준점 아래에 둔다.
  const fitted = invert(multiply(nodeMatrix(garmentRoot.node), nodeMatrix(source)));

  for (const [key, list] of Object.entries({bufferViews, accessors, images, samplers: copy(add.samplers), textures, materials, meshes, skins, nodes})) {
    if (list.length) out[key] = [...(out[key] ?? []), ...list];
  }
  const holder = out.nodes.length;
  out.nodes.push({name: "fit_garment", matrix: fitted, children: [garmentRoot.index + base.nodes]});
  (out.nodes[target].children ??= []).push(holder);
  delete out.animations;

  const binLength = offset + Math.ceil(garment.bin.byteLength / 4) * 4;
  out.buffers = [{byteLength: binLength}];
  const json = new TextEncoder().encode(JSON.stringify(out));
  const jsonLength = Math.ceil(json.byteLength / 4) * 4;
  const bytes = new Uint8Array(28 + jsonLength + binLength);
  const header = new DataView(bytes.buffer);
  header.setUint32(0, 0x46546c67, true); header.setUint32(4, 2, true); header.setUint32(8, bytes.length, true);
  header.setUint32(12, jsonLength, true); header.setUint32(16, 0x4e4f534a, true);
  bytes.fill(32, 20, 20 + jsonLength); bytes.set(json, 20);
  header.setUint32(20 + jsonLength, binLength, true); header.setUint32(24 + jsonLength, 0x004e4942, true);
  bytes.set(body.bin, 28 + jsonLength);
  bytes.set(garment.bin, 28 + jsonLength + offset);
  return new Blob([bytes], {type: "model/gltf-binary"});
}
