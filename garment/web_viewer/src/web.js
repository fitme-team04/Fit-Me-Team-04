// 역할: 신체와 의류 모델을 불러와 종류별 앵커로 정렬합니다.
import {compareSleeves} from './pose.js';
// Configure once per signed-in viewer. Container endpoints are deployment configuration.
export function createFitMeViewer(loader, {onReady = () => {}} = {}) {
  async function loadPair(response, kind) {
    if (!response.ok) throw new Error(await response.text());
    const receipt = await response.json();
    if (receipt.status !== "ready" || !/^[a-f0-9]{64}$/.test(receipt.model_id))
      throw new Error("Invalid generation receipt");
    onReady(kind, receipt);
    async function read(file) {
      const url = new URL(receipt.urls[file]);
      if (url.protocol !== "https:") throw new Error("Expected an HTTPS Blob URL");
      const result = await fetch(url, {credentials:"omit", cache:"no-store", redirect:"error"});
      if (!result.ok) throw new Error(file+" could not be read ("+result.status+")");
      return result;
    }
    const [bytes, metadata] = await Promise.all([
      read("model.glb").then(r=>r.arrayBuffer()),
      read("anchors.json").then(r=>r.json())
    ]);
    const hash = await crypto.subtle.digest("SHA-256",bytes);
    const hex = Array.from(new Uint8Array(hash), b=>b.toString(16).padStart(2,"0")).join("");
    if (hex !== receipt.model_id || metadata.model_sha256 !== hex || metadata.schema_version !== 1)
      throw new Error("Model and anchor JSON do not match");
    const gltf = await loader.parseAsync(bytes,"");
    const root = gltf.scene.getObjectByName(metadata.parent_node);
    const fitting = gltf.scene.userData.fitme_garment;
    const lower = kind === "garments" && fitting?.kind === "slacks";
    if (kind === "garments" && fitting) {
      if (metadata.garment?.kind !== fitting.kind || metadata.garment?.fit_anchor !== fitting.fit_anchor ||
          metadata.garment?.template_id !== fitting.template_id)
        throw new Error("Garment fitting metadata does not match GLB");
      if (!["crewneck", "slacks"].includes(fitting.kind)) throw new Error("Unsupported garment kind");
    }
    const names = lower ? ["fit_anchor_waist", "fit_crotch", "fit_hem_L", "fit_hem_R"]
      : kind === "avatars" ? ["fit_anchor", "fit_anchor_waist"] : ["fit_anchor"];
    if (!lower) {
      const end = kind === "avatars" ? "wrist" : "cuff";
      for (const side of ["L","R"]) names.push("fit_shoulder_"+side,"fit_"+end+"_"+side);
    }
    for (const name of names) {
      const node = root?.children.find(child=>child.name===name);
      const anchor = metadata.anchors?.[name];
      if (!node || !anchor) throw new Error("Missing anchor: "+name);
      node.position.fromArray(anchor.translation);
      node.quaternion.fromArray(anchor.rotation);
      node.scale.fromArray(anchor.scale);
      node.updateMatrix();
    }
    return {...gltf, anchors:metadata, modelId:hex, measurements:gltf.scene.userData.fitme_measurements};
  }
  return {
    async loadFitMeAvatar({photo,height_cm,weight_kg},url="/api/avatars") {
      const r=await fetch(url,{method:"POST",headers:{"Content-Type":photo.type,
        "height-cm":String(height_cm),"weight-kg":String(weight_kg)},body:photo});
      return loadPair(r,"avatars");
    },
    async loadFitMeGarment(garmentId,sizeId,url="/api/garments") {
      const r=await fetch(url,{method:"POST",headers:{"Content-Type":"application/json"},
        body:JSON.stringify({garment_id:Number(garmentId),size_id:Number(sizeId)})});
      return loadPair(r,"garments");
    }
  };
}

function sleeveDirections(root, end) {
  const anchor = root.getObjectByName('fit_anchor');
  const directions = {};
  for (const side of ['L', 'R']) {
    const local = tag => {
      const node = root.getObjectByName('fit_' + tag + '_' + side);
      if (!node) throw Error('Missing landmark: fit_' + tag + '_' + side);
      return anchor.worldToLocal(node.getWorldPosition(node.position.clone()));
    };
    directions[side] = local(end).sub(local('shoulder')).toArray();
  }
  return directions;
}

// Both models must have the same anchor convention. This rigid transform preserves size.
export function fitGarment(body, garment, lowerBody) {
  if (lowerBody === undefined) lowerBody = garment.userData.fitme_garment?.kind === "slacks";
  const name = lowerBody ? "fit_anchor_waist" : "fit_anchor";
  const target = body.getObjectByName(name);
  const source = garment.getObjectByName(name);
  if (!target || !source) throw new Error("Missing fitting anchor: " + name);
  body.updateWorldMatrix(true, true);
  garment.updateWorldMatrix(true, true);
  if (!lowerBody) {
    const pose = body.userData.fitme_pose;
    const policy = pose && {angle: pose.arm_angle_deg, tolerance: pose.sleeve_tolerance_deg};
    const checks = compareSleeves(sleeveDirections(body,'wrist'), sleeveDirections(garment,'cuff'), policy ?? undefined);
    if (checks.some(check => !check.ok)) throw Error('상의 피팅 중단 · 좌우 팔과 소매의 A 자세 각도를 확인하세요.');
  }
  const localAnchor = garment.matrixWorld.clone().invert().multiply(source.matrixWorld);
  target.add(garment);
  localAnchor.invert().decompose(garment.position, garment.quaternion, garment.scale);
  garment.updateWorldMatrix(true, true);
}
