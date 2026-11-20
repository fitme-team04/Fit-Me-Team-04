// Run with: node web/tests/test_fit_room_sam_failures.cjs
// Exercise the real room handlers with rejected API/GLB/viewer operations.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "../static/fit-room.js"), "utf8");
function handler(name, next) {
  const start = source.search(new RegExp(`\\n  (?:async )?function ${name}\\(`));
  assert.ok(start >= 0, name);
  const tail = source.slice(start);
  const end = tail.search(new RegExp(`\\n  (?:async )?function ${next}\\(`));
  assert.ok(end > 0, next);
  return tail.slice(0, end);
}
function until(name, endMarker) {
  const start = source.search(new RegExp(`\\n  (?:async )?function ${name}\\(`));
  const end = source.indexOf(endMarker, start);
  assert.ok(start >= 0 && end > start, name);
  return source.slice(start, end);
}

function fixture() {
  const state = {specs: [], notes: [], steps: [], mountedCloth: [], model: true, urls: [], samCalls: 0, judgeCalls: 0};
  const size = {region: "KR", label: "M", measures: {"가슴단면": 60, "어깨너비": 50, "총장": 70, "소매길이": 60}};
  const stage = {children: [], append(node) { this.children.push(node); }};
  const fakeStage = {
    setGarment(spec) { state.specs.push(spec); state.spec = spec; },
    clearGarmentModel() { state.model = false; if (state.spec) state.specs.push(state.spec); },
    async setGarmentModel(buffer) {
      if (state.rejectModel) throw Error("기준점 정렬 실패");
      state.model = true;
      state.mountedCloth.push(buffer);
    },
    hasGarmentModel() { return state.model; },
    setColor() {}, destroy() { state.model = false; },
  };
  const context = vm.createContext({
    AbortController, Error, TypeError, performance, console,
    bodyModelId: "a".repeat(64), fitStage: fakeStage, garmentSwap: null,
    preview: false, serviceCheckTask: null, serviceError: "", signal: new AbortController().signal,
    approxNote: "실측표로 만든 근사 옷을 보여드려요.",
    bodyOnlyNote: "옷 모델을 표시하지 못해 신체만 보여드려요. 신체 정보 다시 입력을 눌러 재시도해 주세요.",
    viewHint: "회전", caption: {}, color: "#fff", colorChosen: false,
    category: "상의·아우터", tryon: {garment_id: 6},
    catalogSize: () => ({size_id: 3}), catalogSizes: [], sizes: [size],
    garment: {item_code: "E422992"}, shot: {},
    height: {validity: {valid: true}, valueAsNumber: 170},
    weight: {validity: {valid: true}, valueAsNumber: 65}, sizePick: {value: "0"},
    submit: {firstChild: {}, setAttribute() {}, removeAttribute() {}}, status: {},
    photoBox: {}, consent: {checked: true}, job: null,
    report(_target, text) { state.notes.push(text); },
    step(name, value) { state.steps.push([name, value]); },
    syncPanel() {}, renderVerdict() {}, stageLoading() {}, stopCamera() {}, showPanel() {},
    async judge() { state.judgeCalls++; },
    async wait() {},
    async fetch(url) { state.urls.push(url); return {ok: true, arrayBuffer: async () => new ArrayBuffer(4)}; },
    async readJson() { return {items: [{size_id: 3, region: "KR", size_label: "M"}]}; },
    async readBuyerPhoto() { return {}; },
    async readMeasurements() { return {height_cm: 170}; },
    async loadThree() {},
    stage, document: {
      createElement() { const node = {style: {}, remove() { stage.children = stage.children.filter(child => child !== node); }}; return node; },
    },
    window: {FitStage: {mount(_holder, opts) {
      state.specs.push(opts.garment);
      state.spec = opts.garment;
      state.model = false;
      opts.onReady();
      return fakeStage;
    }}},
    stageNote(text) { state.notes.push(text); }, esc: value => value,
  });
  vm.runInContext(`
    const missingGarmentNote = () => preview && !bodyModelId ? approxNote : bodyOnlyNote;
    ${source.slice(source.indexOf("  const failLabels ="), source.indexOf("  function clothNote("))}
    ${handler("clothNote", "catalogSize")}
    ${handler("showMissingGarment", "swapGarment")}
    ${handler("swapGarment", "garmentSpec")}
    ${handler("garmentSpec", "mountStage")}
    ${handler("mountStage", "showPanel")}
    ${handler("dress", "run")}
    ${handler("checkService", "refreshService")}
    ${until("refreshService", "\n  refreshService();")}
    ${until("run", "\n  form.onsubmit =")}
  `, context);
  const cloth = new ArrayBuffer(8);
  context.requestPair = async () => ({
    body: {status: "ready", model_id: "a".repeat(64)},
    garment: {status: "ready"},
  });
  context.verifiedModel = async (_receipt, side) => ({
    buffer: cloth,
    anchors: {garment: {fitting_mode: "sam_body_cloth_collision", simulation_status: "passed"}},
  });
  return {context, state, size, cloth, signal: new AbortController().signal};
}

function noApprox(state) {
  assert.equal(state.specs.filter(Boolean).length, 0, "SAM failure must never create a catalog-sized approximation");
}

const tests = {
  "SAM missing garment clears both previous model and approximation"() {
    const {context, state, size} = fixture();
    context.showMissingGarment(size);
    assert.equal(state.model, false);
    noApprox(state);
  },
  "example body retains its explicit approximation"() {
    const {context, state, size} = fixture();
    context.bodyModelId = null;
    context.preview = true;
    assert.ok(context.showMissingGarment(size));
    assert.ok(state.specs.some(Boolean));
  },
  async "size request HTTP failure clears the old garment and reports body-only error"() {
    const {context, state, size} = fixture();
    context.requestPair = async () => { throw Error("의류 데이터베이스에 연결할 수 없어요."); };
    await context.swapGarment(size);
    noApprox(state);
    assert.equal(state.model, false);
    assert.ok(state.notes.at(-1).includes("데이터베이스"));
    assert.ok(state.notes.at(-1).includes("신체만"));
    assert.deepEqual(state.steps.at(-1), ["tryon", "error"]);
  },
  async "size GLB verification failure remains visible and removes the old garment"() {
    const {context, state, size} = fixture();
    context.verifiedModel = async () => { throw Error("모델 파일과 기준점이 일치하지 않아요."); };
    await context.swapGarment(size);
    noApprox(state);
    assert.equal(state.model, false);
    assert.ok(state.notes.at(-1).includes("기준점"));
  },
  async "size missing from catalog clears the old garment without approximation"() {
    const {context, state, size} = fixture();
    context.catalogSize = () => null;
    await context.swapGarment(size);
    noApprox(state);
    assert.equal(state.model, false);
    assert.ok(state.notes.at(-1).includes("신체만"));
  },
  async "size failed simulation still displays its saved failure GLB"() {
    const {context, state, size, cloth} = fixture();
    context.requestPair = async () => ({garment: {status: "error", preview_available: true}});
    context.verifiedModel = async () => ({buffer: cloth, anchors: {garment: {
      fitting_mode: "sam_body_cloth_collision", simulation_status: "failed", failure_reasons: ["sam_sizing_failed"],
    }}});
    await context.swapGarment(size);
    noApprox(state);
    assert.equal(state.mountedCloth[0], cloth);
    assert.equal(state.model, true);
    assert.ok(state.notes.at(-1).includes("착장 시뮬레이션 실패"));
  },
  async "viewer placement failure shows body only rather than fabricating a garment"() {
    const {context, state, size, cloth, signal} = fixture();
    state.rejectModel = true;
    await context.mountStage(new ArrayBuffer(4), {}, size, "", signal, cloth);
    noApprox(state);
    assert.equal(state.model, false);
    assert.ok(state.notes.at(-1).includes("기준점 정렬 실패"));
    assert.ok(state.notes.at(-1).includes("신체만"));
  },
  async "initial SAM GLB rejection keeps the verification error and body-only state"() {
    const {context, state, size, cloth, signal} = fixture();
    context.verifiedModel = async (_receipt, side) => {
      if (side === "garment") throw Error("모델 해시가 일치하지 않아요.");
      return {buffer: cloth};
    };
    await context.dress(size, {height_cm: 170, weight_kg: 65}, signal);
    noApprox(state);
    assert.equal(state.model, false);
    assert.ok(state.notes.at(-1).includes("모델 해시"));
    assert.ok(state.notes.at(-1).includes("신체만"));
    assert.deepEqual(state.steps.at(-1), ["tryon", "error"]);
  },
  async "initial failed simulation preserves its valid preview and failure status"() {
    const {context, state, size, cloth, signal} = fixture();
    context.requestPair = async () => ({body: {status: "ready", model_id: "a".repeat(64)},
      garment: {status: "error", preview_available: true}});
    context.verifiedModel = async () => ({buffer: cloth, anchors: {garment: {
      fitting_mode: "sam_body_cloth_collision", simulation_status: "failed", failure_reasons: ["body_penetration"],
    }}});
    await context.dress(size, {height_cm: 170, weight_kg: 65}, signal);
    noApprox(state);
    assert.equal(state.mountedCloth[0], cloth);
    assert.equal(state.model, true);
    assert.ok(state.notes.at(-1).includes("신체 관통"));
    assert.deepEqual(state.steps.at(-1), ["tryon", "error"]);
  },
  async "unready normal capture never mounts an example body or calls SAM"() {
    const {context, state, size, signal} = fixture();
    context.tryon = null;
    context.requestPair = async () => { state.samCalls++; throw Error("Unexpected SAM request"); };
    await context.dress(size, {height_cm: 170, weight_kg: 65}, signal);
    assert.equal(state.urls.length, 0);
    assert.equal(state.samCalls, 0);
    noApprox(state);
    assert.ok(state.notes.at(-1).includes("3D 피팅 연결"));
  },
  async "unconfigured service still judges measurements without fabricating a body"() {
    const {context, state} = fixture();
    context.tryon = null;
    context.readJson = async url => { state.urls.push(url); return {configured: false, authenticated: true}; };
    context.requestPair = async () => { state.samCalls++; throw Error("Unexpected SAM request"); };
    await context.run();
    assert.equal(state.samCalls, 0);
    assert.equal(state.judgeCalls, 1);
    assert.ok(state.urls.every(url => !url.includes("example-")));
    assert.equal(state.mountedCloth.length, 0);
    noApprox(state);
    assert.ok(state.notes.at(-1).includes("서버가 아직 연결되지"));
    assert.equal(context.submit.disabled, false);
  },
  async "pending readiness is awaited without starting SAM or an example"() {
    const {context, state} = fixture();
    context.tryon = null;
    let release;
    const pending = new Promise(resolve => { release = resolve; });
    context.readJson = async url => { state.urls.push(url); return pending; };
    context.requestPair = async () => { state.samCalls++; throw Error("Unexpected SAM request"); };
    const initialCheck = context.refreshService();
    const run = context.run();
    await Promise.resolve();
    assert.equal(context.submit.disabled, true);
    assert.equal(state.samCalls, 0);
    assert.equal(state.judgeCalls, 0);
    assert.equal(state.urls.length, 1);
    assert.ok(!state.urls[0].includes("example-"));
    release({configured: false, authenticated: true});
    await Promise.all([initialCheck, run]);
    noApprox(state);
    assert.equal(state.judgeCalls, 1);
    assert.equal(context.submit.disabled, false);
  },
  async "unauthenticated capture reports login rather than loading an example body"() {
    const {context, state} = fixture();
    context.tryon = null;
    context.readJson = async url => { state.urls.push(url); return {configured: true, authenticated: false}; };
    context.requestPair = async () => { state.samCalls++; throw Error("Unexpected SAM request"); };
    await context.run();
    assert.equal(state.samCalls, 0);
    assert.equal(state.judgeCalls, 1);
    assert.equal(state.urls.length, 1);
    noApprox(state);
    assert.ok(state.notes.at(-1).includes("로그인"));
  },
  async "catalog mismatch does not substitute an example body"() {
    const {context, state} = fixture();
    context.tryon = null;
    context.readJson = async url => {
      state.urls.push(url);
      return url.endsWith("/status") ? {configured: true, authenticated: true} : {items: [{item_code: "other", garment_id: 7}]};
    };
    context.requestPair = async () => { state.samCalls++; throw Error("Unexpected SAM request"); };
    await context.run();
    assert.equal(state.samCalls, 0);
    assert.equal(state.judgeCalls, 1);
    assert.ok(state.urls.every(url => !url.includes("example-")));
    noApprox(state);
    assert.ok(state.notes.at(-1).includes("3D 카탈로그"));
  },
  async "catalog connection failure retains its cause and never fetches an example"() {
    const {context, state} = fixture();
    context.tryon = null;
    context.readJson = async url => {
      state.urls.push(url);
      if (url.endsWith("/status")) return {configured: true, authenticated: true};
      throw Error("카탈로그 데이터베이스 준비 중");
    };
    context.requestPair = async () => { state.samCalls++; throw Error("Unexpected SAM request"); };
    await context.run();
    assert.equal(state.samCalls, 0);
    assert.equal(state.judgeCalls, 1);
    assert.ok(state.urls.every(url => !url.includes("example-")));
    noApprox(state);
    assert.ok(state.notes.at(-1).includes("카탈로그 데이터베이스 준비 중"));
  },
  async "explicit loading preview alone may load the example and approximation"() {
    const {context, state} = fixture();
    context.preview = true;
    context.tryon = {preview: true};
    context.requestPair = async () => { state.samCalls++; throw Error("Unexpected SAM request"); };
    await context.run();
    assert.equal(state.samCalls, 0);
    assert.ok(state.urls.includes("/static/models/example-body.glb"));
    assert.ok(state.specs.some(Boolean));
  },
  async "successful readiness proceeds to the actual SAM pair exactly once"() {
    const {context, state} = fixture();
    context.tryon = null;
    context.readJson = async url => {
      state.urls.push(url);
      if (url.endsWith("/status")) return {configured: true, authenticated: true};
      if (url.endsWith("/sizes")) return {items: [{size_id: 3, region: "KR", size_label: "M"}]};
      return {items: [{item_code: "E422992", garment_id: 6}]};
    };
    context.requestPair = async () => {
      state.samCalls++;
      return {body: {status: "ready", model_id: "a".repeat(64)}, garment: {status: "ready"}};
    };
    await context.run();
    assert.equal(state.samCalls, 1);
    assert.equal(state.judgeCalls, 1);
    assert.ok(state.urls.every(url => !url.includes("example-")));
    assert.equal(state.mountedCloth.length, 1);
    assert.equal(state.model, true);
    noApprox(state);
    assert.deepEqual(state.steps.at(-1), ["tryon", "done"]);
  },
  async "body rejection preserves the server photo-quality message without substitute models"() {
    const {context, state, size, signal} = fixture();
    context.requestPair = async () => ({body: {status: "error", message: "전신 사진에서 양발을 확인할 수 없어요."}});
    await context.dress(size, {height_cm: 170, weight_kg: 65}, signal);
    assert.ok(state.notes.at(-1).includes("전신 사진에서 양발을 확인할 수 없어요."));
    assert.ok(state.urls.every(url => !url.includes("example-")));
    assert.equal(state.mountedCloth.length, 0);
    noApprox(state);
    assert.deepEqual(state.steps.at(-1), ["tryon", "error"]);
  },
};

(async () => {
  for (const [name, run] of Object.entries(tests)) { await run(); console.log("PASS", name); }
  console.log(`${Object.keys(tests).length} SAM garment display failure checks passed`);
})().catch(error => { console.error(error); process.exitCode = 1; });
