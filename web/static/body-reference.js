const measureKeys = ["chest_girth", "waist_girth", "hip_girth", "shoulder_width"];
const maxJsonBytes = 4 * 1024 * 1024;

function profile(values, label, gender) {
  const measures = {};
  function cm(key) {
    const value = values[key + "_cm"];
    if (value == null) return undefined;
    if (typeof value !== "number" || !Number.isFinite(value) || value <= 0 || value > 300) {
      throw Error("신체 치수가 cm 단위의 양수인지 확인해 주세요.");
    }
    return value;
  }
  for (const key of measureKeys) {
    const value = cm(key);
    if (value !== undefined) measures[key] = value;
  }
  if (!Object.keys(measures).length) {
    throw Error("가슴둘레, 허리둘레, 엉덩이둘레 또는 어깨너비가 있는 신체 파일을 골라 주세요.");
  }
  return {measures, label, height_cm:cm("height"), gender};
}

function fromReport(report, label, gender) {
  if (!report || typeof report !== "object") throw Error("인체 측정 결과가 포함된 FitMe GLB를 골라 주세요.");
  const values = {};
  for (const key of ["height", ...measureKeys]) values[key + "_cm"] = report[key + "_cm"]?.measured;
  return profile(values, label, gender);
}

function readBodyJson(source) {
  // The supplied sizes file uses line comments. Preserve quoted JSON strings.
  const json = source.replace(/^\uFEFF/, "").replace(/("(?:\\.|[^"\\])*")|\/\/[^\r\n]*/g, (_, string) => string ?? "");
  let doc;
  try { doc = JSON.parse(json); }
  catch { throw Error("FitMe 신체 JSON을 읽을 수 없어요. 파일 형식을 확인해 주세요."); }
  if (!doc || typeof doc !== "object") throw Error("신체 치수가 들어 있는 JSON을 골라 주세요.");
  const genders = ["male","female"].filter(key => doc[key] && typeof doc[key] === "object");
  if (genders.length !== 1) throw Error("한 사람의 male 또는 female 치수가 들어 있는 FitMe JSON을 골라 주세요.");
  return profile(doc[genders[0]], "JSON 입력 신체 치수", genders[0]);
}

async function readBodyGlb(file, requiredSurfaceMeasures = []) {
  const header = new DataView(await file.slice(0,20).arrayBuffer());
  if (header.byteLength < 20 || header.getUint32(0,true) !== 0x46546c67 || header.getUint32(4,true) !== 2
      || header.getUint32(8,true) !== file.size || header.getUint32(16,true) !== 0x4e4f534a) {
    throw Error("FitMe 인체 GLB 파일 형식을 확인해 주세요.");
  }
  const length = header.getUint32(12,true);
  if (length > maxJsonBytes || length > file.size - 20) throw Error("GLB 치수 정보를 읽을 수 없어요.");
  let doc;
  try { doc = JSON.parse(await file.slice(20,20+length).text()); }
  catch { throw Error("GLB 치수 정보를 읽을 수 없어요."); }
  if (!Array.isArray(doc?.nodes) || !doc.nodes.some(node => node?.name === "body" && Number.isInteger(node.mesh))) {
    throw Error("몸 치수는 FitMe 인체 모델에서 불러올 수 있어요.");
  }
  const extras = doc.scenes?.[doc.scene ?? 0]?.extras;
  for (const key of requiredSurfaceMeasures) {
    if (extras?.body_geometry_source !== "sam_surface" ||
        extras?.fitme_measurements?.[key + "_cm"]?.surface !== "sam_surface_at_projected_height") {
      throw Error("실제 SAM 단면 치수가 없어 판정을 보류합니다. 신체 측정 결과를 확인해 주세요.");
    }
  }
  return fromReport(extras?.fitme_measurements, "GLB 인체 모델 측정값");
}

export async function readBodyFile(file, requiredSurfaceMeasures = []) {
  if (file.name.toLowerCase().endsWith(".glb")) return readBodyGlb(file, requiredSurfaceMeasures);
  if (!file.name.toLowerCase().endsWith(".json") || file.size > maxJsonBytes) {
    throw Error("FitMe 인체 GLB 또는 4 MB 이하의 신체 JSON을 골라 주세요.");
  }
  return readBodyJson(await file.text());
}

export async function loadExampleBody() {
  const response = await fetch("/static/data/example-body.json");
  if (!response.ok) throw Error("예시 신체 치수를 불러오지 못했어요. 잠시 후 다시 시도해 주세요.");
  const doc = await response.json();
  return fromReport(doc.fitme_measurements, "예시 인체 모델 치수", doc.gender);
}
