// Generation service limits and receipt format are defined in api.py and blob_assets.py.
// 사진은 보내기 전에 긴 쪽 1920px JPEG로 줄인다. 1,600만 화소·3 MiB 제한을 넘는 큰 사진도 그대로 쓸 수 있고 업로드가 빨라진다.
const PHOTO_SIDE = 1920, PHOTO_BYTES = 3 * 1024 * 1024;

export async function readBuyerPhoto(file, signal) {
  if (!file || !file.size) throw Error("구매자 본인의 전신 사진을 선택해 주세요.");
  let bitmap;
  try { bitmap = await createImageBitmap(file, {imageOrientation: "from-image"}); }
  catch { throw Error("사진을 열 수 없어요. JPG 또는 PNG 사진을 골라 주세요."); }
  signal.throwIfAborted();
  const scale = Math.min(1, PHOTO_SIDE / Math.max(bitmap.width, bitmap.height));
  const canvas = document.createElement("canvas");
  canvas.width = Math.max(1, Math.round(bitmap.width * scale));
  canvas.height = Math.max(1, Math.round(bitmap.height * scale));
  canvas.getContext("2d").drawImage(bitmap, 0, 0, canvas.width, canvas.height);
  bitmap.close();
  // 품질 0.9가 기본이고, 아주 복잡한 사진이 3 MiB를 넘을 때만 조금씩 낮춘다.
  let blob = null;
  for (const quality of [.9, .8, .7]) {
    blob = await new Promise(resolve => canvas.toBlob(resolve, "image/jpeg", quality));
    if (blob && blob.size <= PHOTO_BYTES) break;
  }
  if (!blob || blob.size > PHOTO_BYTES) throw Error("사진을 줄이지 못했어요. 다른 사진을 골라 주세요.");
  const bytes = new Uint8Array(await blob.arrayBuffer());
  signal.throwIfAborted();
  // Chunk conversion avoids exceeding the browser's function argument limit.
  const chunks = [];
  for (let i = 0; i < bytes.length; i += 16384) chunks.push(String.fromCharCode(...bytes.subarray(i, i + 16384)));
  return {photo_mime: "image/jpeg", photo_b64: btoa(chunks.join(""))};
}

async function readAsset(url, signal) {
  const target = new URL(url);
  const loopback = ["localhost","127.0.0.1","[::1]"].includes(target.hostname);
  if (target.username || target.password || (target.protocol !== "https:" && !(target.protocol === "http:" && loopback))) {
    throw Error("모델 다운로드 주소가 올바르지 않아요.");
  }
  const response = await fetch(target, {credentials:"omit", cache:"no-store", redirect:"error", signal});
  if (!response.ok) throw Error("모델 파일을 받지 못했어요. 두 모델을 다시 요청해 주세요.");
  return response;
}

function checkAnchors(buffer, meta, side) {
  const view = new DataView(buffer);
  if (buffer.byteLength < 20 || view.getUint32(0) !== 0x676c5446 || view.getUint32(4,true) !== 2
      || view.getUint32(8,true) !== buffer.byteLength || view.getUint32(16) !== 0x4a534f4e) return false;
  const jsonLength = view.getUint32(12,true);
  if (jsonLength > buffer.byteLength - 20) return false;
  const gltf = JSON.parse(new TextDecoder().decode(new Uint8Array(buffer,20,jsonLength)));
  for (const resource of [...(gltf.buffers || []), ...(gltf.images || [])]) {
    if (typeof resource.uri === "string" && !resource.uri.startsWith("data:")) return false;
  }
  const scene = gltf.scenes?.[gltf.scene ?? 0];
  const root = scene?.nodes?.length === 1 && gltf.nodes?.[scene.nodes[0]];
  if (!root || root.name !== meta.parent_node || !Array.isArray(root.children)) return false;
  const children = new Map(root.children.map(i => [gltf.nodes[i]?.name, gltf.nodes[i]]));
  const body = side === "body";
  const end = body ? "wrist" : "cuff";
  const lower = !body && meta.garment?.kind === "slacks";
  const fitting = scene.extras?.fitme_garment;
  if (!body && (fitting?.kind !== meta.garment?.kind ||
      fitting?.fitting_mode !== meta.garment?.fitting_mode ||
      fitting?.body_model_id !== meta.garment?.body_model_id ||
      fitting?.simulation_status !== meta.garment?.simulation_status ||
      JSON.stringify(fitting?.failure_reasons) !== JSON.stringify(meta.garment?.failure_reasons))) return false;
  const names = lower ? ["fit_anchor_waist", "fit_crotch", "fit_hem_L", "fit_hem_R"]
    : ["fit_anchor", "fit_shoulder_L", "fit_shoulder_R", "fit_"+end+"_L", "fit_"+end+"_R"];
  if (body) names.push("fit_anchor_waist");
  return names.every(name => {
    const marker = children.get(name), recorded = meta.anchors?.[name];
    if (!marker || marker.matrix || !recorded) return false;
    return [["translation",[0,0,0]],["rotation",[0,0,0,1]],["scale",[1,1,1]]].every(([prop, fallback]) => {
      const values = recorded[prop], actual = marker[prop] ?? fallback;
      return Array.isArray(values) && values.length === fallback.length && Array.isArray(actual)
        && actual.length === values.length && values.every((v,i) => Number.isFinite(v) && v === actual[i]);
    });
  });
}

// 검증을 마친 모델 바이트와 기준점. 착장할 때 두 모델의 기준점을 함께 쓴다.
export async function verifiedModel(receipt, side, signal, expectedBodyModelId = null) {
  if (!/^[a-f0-9]{64}$/.test(receipt.model_id) || !receipt.glb_url || !receipt.anchors_url) {
    throw Error("모델과 기준점 파일 정보가 부족해요.");
  }
  if (!globalThis.crypto?.subtle) throw Error("3D 모델 확인을 위해 HTTPS 주소에서 열어 주세요.");
  const [buffer, anchors] = await Promise.all([
    readAsset(receipt.glb_url,signal).then(r => r.arrayBuffer()),
    readAsset(receipt.anchors_url,signal).then(r => r.json()),
  ]);
  const digest = new Uint8Array(await crypto.subtle.digest("SHA-256",buffer));
  signal.throwIfAborted();
  const hash = Array.from(digest, byte => byte.toString(16).padStart(2,"0")).join("");
  if (hash !== receipt.model_id || anchors?.schema_version !== 1 || anchors.model_sha256 !== hash
      || !checkAnchors(buffer,anchors,side)) {
    throw Error("모델 파일과 기준점이 일치하지 않아 표시할 수 없어요.");
  }
  if (side === "garment" && expectedBodyModelId !== null &&
      (!["db_cloth_collision", "sam_body_cloth_collision"].includes(anchors.garment?.fitting_mode)
       || anchors.garment.body_model_id !== expectedBodyModelId)) {
    throw Error("이 옷은 다른 신체에서 시뮬레이션한 결과예요. 다시 생성해 주세요.");
  }
  return {buffer, anchors};
}

// 신체 VM이 함께 올려 준 measurements.json (fit-stage가 몸 둘레·높이를 읽는다)
export async function readMeasurements(receipt, signal) {
  if (!receipt?.measurements_url) return null;
  return (await readAsset(receipt.measurements_url, signal)).json();
}
