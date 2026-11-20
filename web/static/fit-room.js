/* 구매자 피팅룸: 옷 고르기 → 신체 정보 입력 → 내 몸에 입힌 3D 착장 → 핏 판정.
   3D는 웹앱이 Redis 워커를 거쳐 신체·의류 VM에 요청하고, 핏 판정은 웹앱의 MySQL 데이터로 계산한다. */
import { $, view, esc, flow, report, loadingMark } from "./resale-ui.js?v=20261112";
import { readBuyerPhoto, verifiedModel, readMeasurements } from "./pair-files.js?v=20261117b";

const categories = {"상의": "상의·아우터", "상의·아우터": "상의·아우터", "하의": "하의", "원피스": "원피스"};
const colors = [["#f1efe8", "화이트"], ["#23262b", "블랙"], ["#22335c", "네이비"], ["#8b9096", "그레이"], ["#6e2a2e", "버건디"]];

// 3D 착장은 three r128 + vendor/fit-stage.js(전역 FitStage)로 그린다. 처음 필요할 때 한 번만 불러온다.
const threeScripts = [
  "https://cdn.jsdelivr.net/npm/three@0.128.0/build/three.min.js",
  "https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js",
  "https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/loaders/GLTFLoader.js",
  "/static/vendor/fit-stage.js?v=20261117d",
];
let threeReady = null;
function loadThree() {
  threeReady ??= threeScripts.reduce((previous, src) => previous.then(() => new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = src;
    script.onload = resolve;
    script.onerror = () => { threeReady = null; reject(Error("3D 화면 파일을 불러오지 못했어요. 인터넷 연결을 확인해 주세요.")); };
    document.head.append(script);
  })), Promise.resolve());
  return threeReady;
}

// GLB 안에 들어 있는 치수(scene.extras.fitme_measurements). measurements.json이 없을 때 쓴다.
function measuresFromGlb(buffer) {
  try {
    const view = new DataView(buffer);
    const json = JSON.parse(new TextDecoder().decode(new Uint8Array(buffer, 20, view.getUint32(12, true))));
    return json.scenes?.[json.scene ?? 0]?.extras?.fitme_measurements ?? null;
  } catch { return null; }
}
// 팀원이 바로 체험할 수 있게 입력 칸에 넣어 두는 샘플 상품 (팀 DB에 실측표가 있는 옷)
const sampleLink = "https://www.uniqlo.com/kr/ko/products/E422992-000";

// 상품 링크에서는 주소 경로의 품번으로 찾는다. 링크가 아니면 입력한 그대로 찾는다.
function searchTerms(text) {
  try {
    const url = new URL(text);
    if (["http:", "https:"].includes(url.protocol)) return decodeURIComponent(url.pathname).split("/").filter(Boolean).join(" ");
  } catch { /* 상품명이나 품번 */ }
  return text;
}

async function readJson(url, options) {
  const response = await fetch(url, options);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw Error(typeof data.detail === "string" ? data.detail : "잠시 후 다시 시도해 주세요.");
  return data;
}

function remember(garment) {
  try { sessionStorage.setItem("fit.garment." + garment.garment_id, JSON.stringify(garment)); } catch { /* 이번 화면에서만 사용 */ }
}
function recall(id) {
  try { return JSON.parse(sessionStorage.getItem("fit.garment." + id)); } catch { return null; }
}

// ---------------------------------------------------------------- 옷 고르기
function home(signal) {
  view.innerHTML = `<div class="v2-home"><section class="campaign" aria-labelledby="home-heading">
    <img class="campaign-photo" src="/static/photos/editorial-home.webp" width="1536" height="1024" fetchpriority="high" alt="">
    <div class="campaign-ink wrap">
      <div class="campaign-title">
        <span class="campaign-category">내 몸으로 입어 보는 3D 피팅룸</span>
        <h1 id="home-heading" lang="en">Fitting<br><em>Room.</em></h1>
      </div>
      <div class="campaign-actions">
        <p>사고 싶은 옷을 고르면<br>내 몸에 입혀서 보여드려요.</p>
        <nav class="role-choices"><a href="#pick" class="role-card main" id="go-pick">입어볼 옷 고르기 <span aria-hidden="true">↓</span></a></nav>
      </div>
    </div>
  </section>
  <section id="pick" class="pick wrap" aria-labelledby="pick-title">
    <h2 id="pick-title" tabindex="-1">어떤 옷을 입어볼까요?</h2>
    <form class="pick-form" role="search">
      <label for="pick-query">의류 사이트 상품 링크</label>
      <div><input id="pick-query" type="text" inputmode="url" maxlength="400" autocomplete="off" autocapitalize="none" spellcheck="false"
        value="${esc(sampleLink)}" placeholder="상품 링크 붙여넣기">
      <button type="submit" class="fit-primary">이 옷 입어보기<span class="fit-arrow" aria-hidden="true"></span></button></div>
      <p class="hint">체험용 샘플 링크가 들어 있어요. 다른 상품 링크나 상품명·품번으로 바꿔도 돼요.</p>
    </form>
    <p class="status" role="status"></p>
    <ul class="pick-list"></ul>
  </section></div>`;
  const form = $(".pick-form"), status = $(".pick .status"), list = $(".pick-list");
  let revision = 0;

  $("#go-pick").onclick = event => {
    event.preventDefault();
    $("#pick").scrollIntoView({behavior: "smooth"});
    $("#pick-query").focus({preventScroll: true});
  };

  function show(items, emptyText) {
    list.replaceChildren();
    for (const garment of items) {
      const item = document.createElement("li");
      const link = document.createElement("a");
      link.href = "#fit/" + garment.garment_id;
      link.innerHTML = `<small>${esc(garment.brand_name || "")}</small><strong>${esc(garment.garment_name)}</strong>
        <span>${esc([garment.category, garment.item_code].filter(Boolean).join(" · "))}</span><i class="fit-arrow" aria-hidden="true"></i>`;
      link.onclick = () => remember(garment);
      item.append(link);
      list.append(item);
    }
    report(status, items.length ? "" : emptyText);
  }

  async function search(text, emptyText) {
    const current = ++revision;
    const query = searchTerms(text);
    report(status, "옷을 찾고 있어요.", true);
    try {
      const {items = []} = await readJson("/api/resale/search?q=" + encodeURIComponent(query), {signal});
      if (signal.aborted || current !== revision) return;
      // 링크의 품번과 일치하는 옷이 하나면 바로 피팅 화면으로 간다.
      const codes = query.toLowerCase().split(/\s+/);
      const exact = items.filter(item => codes.includes(String(item.item_code).toLowerCase()));
      if (exact.length === 1) { remember(exact[0]); location.hash = "#fit/" + exact[0].garment_id; return; }
      if (items.length) show(items, "");
      else report(status, emptyText);
    } catch (error) {
      if (!signal.aborted && current === revision) { report(status, error instanceof TypeError ? "서버에 연결하지 못했어요." : error.message); }
    }
  }

  form.onsubmit = event => {
    event.preventDefault();
    const query = $("#pick-query").value.trim();
    if (query) search(query, "이 링크의 옷은 아직 실측표가 없어요. 아래 옷으로 입어 보세요.");
  };

  // 처음에는 실측표가 등록된 옷을 바로 고를 수 있게 보여 준다.
  (async () => {
    const current = ++revision;
    report(status, "입어볼 수 있는 옷을 불러오고 있어요.", true);
    try {
      const {items = []} = await readJson("/api/products", {signal});
      const measured = items.filter(item => item.measured_sizes > 0).slice(0, 6);
      const found = await Promise.all(measured.map(item =>
        readJson("/api/resale/search?q=" + encodeURIComponent(item.item_code), {signal})
          .then(result => (result.items || []).find(garment => garment.item_code === item.item_code))));
      if (!signal.aborted && current === revision) show(found.filter(Boolean), "상품명이나 품번으로 옷을 찾아 주세요.");
    } catch {
      if (!signal.aborted && current === revision) report(status, "상품명이나 품번으로 옷을 찾아 주세요.");
    }
  })();
}

// ---------------------------------------------------------------- 3D 착장
function requestKey() {
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  bytes[6] = (bytes[6] & 15) | 64; bytes[8] = (bytes[8] & 63) | 128;
  const hex = Array.from(bytes, b => b.toString(16).padStart(2, "0")).join("");
  return [hex.slice(0, 8), hex.slice(8, 12), hex.slice(12, 16), hex.slice(16, 20), hex.slice(20)].join("-");
}

function wait(ms, signal) {
  return new Promise((resolve, reject) => {
    signal.throwIfAborted();
    const timer = setTimeout(() => { signal.removeEventListener("abort", cancel); resolve(); }, ms);
    function cancel() { clearTimeout(timer); reject(signal.reason); }
    signal.addEventListener("abort", cancel, {once: true});
  });
}

// 웹앱 → Redis 워커 → 신체·의류 VM. 준비되면 두 모델의 Blob 읽기 링크를 돌려받는다.
// bodyModelId: 몸을 다시 만들지 않고 옷만 받을 때(사이즈 변경), 이미 만든 몸에 맞춰 옷을 시뮬레이션하게 한다.
async function requestPair(body, garment, signal, onWaiting, fit, bodyModelId) {
  const request = {body, garment, fit};
  if (!body && bodyModelId) request.body_model_id = bodyModelId;
  let response = await fetch("/api/v2/model-pair", {method: "POST", signal,
    headers: {"Content-Type": "application/json", "Idempotency-Key": requestKey()}, body: JSON.stringify(request)});
  let jobUrl = null, delay = 1000;
  while (response.status === 202) {
    if (!jobUrl) {
      const job = await response.json();
      const expected = "/api/v2/model-pair/jobs/" + job?.job_id;
      if (!/^[a-f0-9]{32}$/.test(job?.job_id) || job.status_url !== expected) throw Error("모델 요청 번호를 확인할 수 없어요.");
      jobUrl = expected;
    }
    onWaiting();
    const retryAfter = Number(response.headers.get("Retry-After")) * 1000;
    await wait(Math.min(4000, Math.max(delay, Number.isFinite(retryAfter) ? retryAfter : 0)), signal);
    response = await fetch(jobUrl, {signal, cache: "no-store"});
    delay = Math.min(delay * 2, 4000);
  }
  const result = await response.json().catch(() => ({}));
  if (!response.ok) throw Error(typeof result.detail === "string" ? result.detail : "3D 모델을 요청하지 못했어요.");
  return result;
}

// ---------------------------------------------------------------- 피팅 화면
async function room(id, signal) {
  const garment = recall(id);
  if (!garment) { location.hash = "#home"; return; }
  const category = categories[garment.category];
  flow(garment.garment_name, "이 옷의 실측표를 불러오고 있어요.", loadingMark);
  let sizes;
  try {
    const chart = await readJson("/api/resale/garments/" + id, {signal});
    sizes = (chart.sizes || []).filter(size => Object.keys(size.measures || {}).length);
  } catch (error) {
    if (signal.aborted) return;
    flow("옷을 열 수 없어요", error instanceof TypeError ? "서버에 연결하지 못했어요." : error.message, '<a class="btn" href="#home">다른 옷 고르기</a>');
    return;
  }
  if (signal.aborted) return;
  if (!sizes.length || !category) {
    flow(garment.garment_name, "이 옷은 아직 실측표가 없어 입어볼 수 없어요.", '<a class="btn" href="#home">다른 옷 고르기</a>');
    return;
  }
  const sizeName = size => [size.region, size.label].filter(Boolean).join(" · ");
  const field = (name, label, unit, min, max, sample) => `<label class="field fit-field" for="${name}">${label}
    <span class="fit-input"><input id="${name}" type="number" inputmode="decimal" min="${min}" max="${max}" step="any" required
      aria-label="${label} (${unit})" placeholder="${sample}"><span aria-hidden="true">${unit}</span></span></label>`;

  view.innerHTML = `<article class="buyer-flow room" aria-labelledby="room-name">
    <header class="fit-sheet-head">
      <div class="fit-sheet-nav"><a class="fit-back" href="#home">← 다른 옷 고르기</a>
        <span>${esc([garment.brand_name, garment.category, garment.item_code].filter(Boolean).join(" · "))}</span></div>
      <h1 id="room-name">${esc(garment.garment_name)}</h1>
    </header>
    <ol class="room-steps" aria-label="진행 단계">
      <li data-step="body" data-state="now"><b>1</b>신체 정보</li>
      <li data-step="tryon"><b>2</b>3D 착장</li>
      <li data-step="verdict"><b>3</b>핏 판정</li>
    </ol>
    <div class="room-grid">
      <figure class="room-stage">
        <div class="room-view"></div>
        <figcaption role="status"></figcaption>
      </figure>
      <div class="room-panel">
        <form id="buyer-fit" novalidate>
          <h2>내 몸에 입혀 볼까요<span>?</span></h2>
          <label class="field fit-field room-size" for="room-size">사이즈
            <select id="room-size">${sizes.map((size, i) => `<option value="${i}">${esc(sizeName(size))}</option>`).join("")}</select></label>
          <div class="fit-body-fields">${field("fit-height", "키", "cm", 120, 230, 170)}${field("fit-weight", "몸무게", "kg", 30, 250, 65)}</div>
          <div class="room-photo" hidden>
            <label class="pair-consent"><input id="room-consent" type="checkbox">
              내 사진·키·몸무게를 팀 클라우드로 보내 3D 몸을 만들고 저장하는 데 동의해요.</label>
          </div>
          <button id="request-fit" class="fit-primary" type="submit">입어보기<span class="fit-arrow" aria-hidden="true"></span></button>
          <p class="status" id="fit-status" role="status"></p>
        </form>
        <section class="dress-panel" hidden aria-label="옷 바꿔 보기">
          <h2>내 몸에 입혀 볼까요<span>?</span></h2>
          <p class="dress-label">사이즈</p>
          <div class="dress-chips" role="group" aria-label="사이즈"></div>
          <div class="dress-swatches" role="group" aria-label="옷 색상">${colors.map(([hex, name], i) =>
            `<button type="button" data-color="${hex}" aria-pressed="${i === 0}" aria-label="${name}" title="${name}" style="--swatch:${hex}"></button>`).join("")}</div>
          <div class="dress-toggles">
            <button type="button" data-toggle="heat" aria-pressed="false">핏 히트맵</button>
            <button type="button" data-toggle="undress" aria-pressed="false">옷 벗기</button>
            <button type="button" data-toggle="rotate" aria-pressed="false">자동 회전</button>
          </div>
          <button type="button" class="dress-edit">신체 정보 다시 입력</button>
        </section>
        <section id="verdict-card" class="verdict-card" hidden aria-live="polite"></section>

      </div>
    </div></article>`;
  document.title = garment.garment_name + " · 입어봄";

  const form = $("#buyer-fit"), height = $("#fit-height"), weight = $("#fit-weight"), sizePick = $("#room-size");
  const consent = $("#room-consent"), photoBox = $(".room-photo");
  const submit = $("#request-fit"), status = $("#fit-status");
  const stage = $(".room-view"), caption = $(".room-stage figcaption");
  let job = null, modelUrl = "", tryon = null;   // tryon: 3D 서비스가 연결됐을 때 {garment_id}
  let serviceCheckTask = null, serviceError = "";
  // 주소에 ?loading=preview 를 붙이면 3D 서비스가 없어도 촬영 → 로딩 → 결과 자리까지 미리 볼 수 있다.
  const preview = new URLSearchParams(location.search).get("loading") === "preview";
  let shot = null, shotUrl = "", camera = null;      // 촬영하거나 고른 전신 사진과 카메라 스트림

  function step(name, state) { $(`.room-steps [data-step=${name}]`).dataset.state = state; }
  function stageNote(html, busy = false) {
    stage.innerHTML = `<p class="room-note"${busy ? " data-busy" : ""}>${html}</p>`;
  }
  // 3D를 기다리는 동안 보여 주는 로딩 장면. 같은 요소를 두고 문구만 바꿔 애니메이션이 끊기지 않게 한다.
  function stageLoading(text) {
    let box = stage.querySelector(".room-loading");
    if (!box) {
      stage.innerHTML = `<div class="room-loading" role="status">
        <div class="room-loading-art"><video src="/static/photos/loading.mp4" autoplay muted loop playsinline
          preload="auto" aria-hidden="true"></video></div>
        <p></p></div>`;
      box = stage.querySelector(".room-loading");
    }
    box.querySelector("p").textContent = text;
  }
  function release() {
    if (modelUrl) { URL.revokeObjectURL(modelUrl); modelUrl = ""; }
  }
  function stopCamera() {
    camera?.getTracks().forEach(track => track.stop());
    camera = null;
  }
  signal.addEventListener("abort", () => { job?.abort(); release(); stopCamera(); if (shotUrl) URL.revokeObjectURL(shotUrl); }, {once: true});

  // ---- 3D 촬영: 카메라 + 실루엣 가이드. 카메라를 못 쓰면 사진 고르기로 대신한다.
  function setShot(blob) {
    if (shotUrl) URL.revokeObjectURL(shotUrl);
    shot = blob;
    shotUrl = blob ? URL.createObjectURL(blob) : "";
    stopCamera();
    showCapture();
  }
  function showCapture() {
    stage.innerHTML = `<div class="shot">
      <div class="shot-frame" data-state="${shot ? "taken" : "live"}">
        <video playsinline muted autoplay aria-label="카메라 화면"></video>
        <img class="shot-photo" alt="촬영한 전신 사진" ${shot ? `src="${shotUrl}"` : "hidden"}>
        <svg class="shot-guide" viewBox="0 0 200 300" aria-hidden="true" ${shot ? "hidden" : ""}>
          <g fill="none" stroke="currentColor" stroke-width="2.2" stroke-dasharray="7 6" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="100" cy="38" r="18"/><path d="M82 64h36M82 64L22 92M118 64l60 28M82 64v78h36V64M86 142l-10 130M114 142l10 130"/></g></svg>
        <p class="shot-msg" role="status">${shot ? "머리부터 양발까지 모두 보이는지 확인해 주세요." : "전신이 보이게 양팔을 벌리고 서 주세요."}</p>
      </div>
      <div class="shot-actions">
        ${shot ? '<button type="button" class="btn" data-act="retake">다시 찍기</button>'
          : '<button type="button" class="btn primary" data-act="snap" disabled>촬영하기</button>'}
        <label class="btn">사진 고르기<input type="file" accept="image/*" hidden></label>
      </div></div>`;
    const frame = $(".shot-frame", stage), video = $("video", stage), msg = $(".shot-msg", stage), snap = $("[data-act=snap]", stage);
    $("input[type=file]", stage).onchange = event => {
      const file = event.currentTarget.files[0];
      event.currentTarget.value = "";
      if (!file) return;
      if (!file.type.startsWith("image/")) { msg.textContent = "사진 파일을 골라 주세요."; return; }
      setShot(file);
    };
    $("[data-act=retake]", stage)?.addEventListener("click", () => setShot(null));
    if (shot) return;
    if (!navigator.mediaDevices?.getUserMedia) { msg.textContent = "이 브라우저에서는 카메라를 쓸 수 없어요. 사진을 골라 주세요."; return; }
    navigator.mediaDevices.getUserMedia({video: {facingMode: "user", width: {ideal: 1920}}, audio: false}).then(stream => {
      if (signal.aborted || shot || !frame.isConnected) { stream.getTracks().forEach(track => track.stop()); return; }
      stopCamera();
      camera = stream;
      video.srcObject = stream;
      snap.disabled = false;
    }).catch(() => { if (frame.isConnected) msg.textContent = "카메라를 켜지 못했어요. 사진을 골라 주세요."; });
    snap.onclick = () => {
      if (!video.videoWidth) return;
      const scale = Math.min(1, 1920 / Math.max(video.videoWidth, video.videoHeight));
      const canvas = document.createElement("canvas");
      canvas.width = Math.round(video.videoWidth * scale);
      canvas.height = Math.round(video.videoHeight * scale);
      canvas.getContext("2d").drawImage(video, 0, 0, canvas.width, canvas.height);
      canvas.toBlob(blob => blob ? setShot(blob) : (msg.textContent = "사진을 만들지 못했어요. 다시 시도해 주세요."), "image/jpeg", .9);
    };
  }
  showCapture();

  // 3D 서비스 연결과 이 옷의 카탈로그 등록 여부를 먼저 확인한다.
  // 3D 연결 확인. DB가 깨어나는 중이거나 VM이 켜지는 중이면 실패할 수 있어 5초 뒤 한 번 더 확인한다.
  async function checkService(retry = true) {
    if (preview) {
      tryon = {preview: true};
      photoBox.hidden = false;
      consent.required = true;
      report(caption, "미리보기 · 실제 3D 모델은 만들지 않고, 촬영과 로딩 화면의 흐름만 보여드려요.");
      return;
    }
    report(caption, "3D 피팅 연결을 확인하고 있어요.", true);
    try {
      const service = await readJson("/api/v2/model-pair/status", {signal});
      if (!service.configured || !service.authenticated) {
        serviceError = service.configured ? "사진으로 입어보려면 로그인해 주세요. 키·몸무게 판정은 확인할 수 있어요."
          : "3D 모델 서버가 아직 연결되지 않았어요. 잠시 후 다시 입어보기를 눌러 주세요.";
        report(caption, serviceError);
        return;
      }
      const {items = []} = await readJson("/api/v2/garment-catalog", {signal});
      const match = items.filter(item => item.item_code === garment.item_code);
      if (match.length !== 1) {
        serviceError = "이 옷은 3D 카탈로그에 없어 사진 착장을 만들 수 없어요. 핏 판정만 확인할 수 있어요.";
        report(caption, serviceError);
        return;
      }
      tryon = {garment_id: match[0].garment_id};
      serviceError = "";
      photoBox.hidden = false;
      consent.required = true;
      report(caption, "");
    } catch (error) {
      if (signal.aborted) return;
      if (retry) {
        report(caption, "3D 피팅 연결을 다시 확인하고 있어요.", true);
        try { await wait(5000, signal); } catch { return; }
        return checkService(false);
      }
      serviceError = (error instanceof TypeError ? "3D 피팅 서버에 연결하지 못했어요." : error.message)
        + " 잠시 후 다시 입어보기를 눌러 주세요. 핏 판정은 확인할 수 있어요.";
      report(caption, serviceError);
    }
  }
  function refreshService() {
    if (!serviceCheckTask) {
      serviceError = "";
      serviceCheckTask = checkService().finally(() => { serviceCheckTask = null; });
    }
    return serviceCheckTask;
  }
  refreshService();

  // ---- 사이즈 판정: ease_check 결과(verdict, message_ko, status, recommended_size)만 그대로 보여 준다.
  // 판정 기준 숫자는 프론트에 두지 않는다.
  //   shotFit     : 촬영한 몸으로 의류 서버 /fit 이 판정한 결과 (3D 서비스가 연결됐을 때)
  //   estimateFit : 키·몸무게로 추정한 가슴둘레로 웹앱이 판정한 결과 (/api/resale/ease)
  const verdictCard = $("#verdict-card");
  const verdictWords = {FIT: "입을 수 있어요", NO_FIT: "맞지 않아요", UNDETERMINED: "판정할 수 없어요"};
  const statusWords = {TOO_TIGHT: "작음", TOO_LOOSE: "너무 큼"};
  let shotFit = null, shotIndex = -1, estimateFit = null, estimateIndex = -1, judgeTask = null;
  function renderVerdict() {
    const size = sizes[currentSize];
    const [judged, basis] = shotFit && shotIndex === currentSize ? [shotFit, "촬영한 몸"]
      : estimateFit && estimateIndex === currentSize ? [estimateFit, "키·몸무게로 추정한 몸"] : [null, ""];
    if (!judged) return;
    const selected = judged.selected ?? {};
    const verdict = Object.hasOwn(verdictWords, selected.verdict) ? selected.verdict : "UNDETERMINED";
    const part = (selected.parts || []).find(item => statusWords[item.status]);
    const recommend = verdict === "NO_FIT" && judged.recommended_size
      ? `<p class="verdict-recommend">이 사이즈를 추천해요 <b>${esc(judged.recommended_size)}</b></p>` : "";
    verdictCard.hidden = false;
    verdictCard.dataset.verdict = verdict;
    verdictCard.innerHTML = `<p class="verdict-tag">${esc(sizeName(size).replace(" · ", "·"))} · ${verdictWords[verdict]}${part ? " · " + statusWords[part.status] : ""}</p>
      <h2>${esc(selected.message_ko || "판정할 수 없습니다.")}</h2>${recommend}
      <p class="hint">${esc(basis)} 기준${judged.rules_version ? " · " + esc(judged.rules_version) : ""}</p>
      <p class="verdict-note">사이즈 판정은 상품 실측과 신체 치수를 비교한 결과예요.</p>`;
  }

  async function judge(size, body) {
    judgeTask?.abort();
    const task = judgeTask = new AbortController();
    signal.addEventListener("abort", () => task.abort(), {once: true});
    step("verdict", "busy");
    if (!(shotFit && shotIndex === sizes.indexOf(size))) {
      verdictCard.hidden = false;
      verdictCard.dataset.verdict = "";
      verdictCard.innerHTML = '<div class="fit-skeleton" aria-hidden="true"><i></i><i></i><i></i></div>';
    }
    try {
      const answer = await readJson("/api/resale/ease", {method: "POST", signal: task.signal,
        headers: {"Content-Type": "application/json"}, body: JSON.stringify({garment_id: id, category: garment.category,
          region: size.region || "KR", size_label: size.label, height_cm: body.height_cm, weight_kg: body.weight_kg})});
      if (task.signal.aborted) return;
      estimateFit = answer;
      estimateIndex = sizes.indexOf(size);
      renderVerdict();
      step("verdict", "done");
    } catch (error) {
      if (task.signal.aborted) return;
      step("verdict", "error");
      if (shotFit && shotIndex === sizes.indexOf(size)) return;
      verdictCard.hidden = false;
      verdictCard.dataset.verdict = "UNDETERMINED";
      verdictCard.innerHTML = `<p class="status">${esc(error instanceof TypeError ? "판정 서버에 연결하지 못했어요." : error.message)}</p>`;
    }
  }

  // ---- 3D 착장: 신체 GLB 위에 의류 서버가 만든 의류 GLB 를 기준점으로 맞춰 입힌다(원본 재질·색상 유지).
  //      실측표 근사 옷은 예시 체형에만 쓴다. SAM 의류가 없으면 신체만 표시한다.
  const panel = $(".dress-panel");
  let fitStage = null, currentSize = 0, lastBody = null, color = colors[0][0], colorChosen = false;
  let catalogSizes = [], garmentSwap = null, bodyModelId = null;
  signal.addEventListener("abort", () => { garmentSwap?.abort(); fitStage?.destroy(); fitStage = null; }, {once: true});
  const viewHint = "드래그: 회전 · 휠/핀치: 확대";
  const approxNote = "실측표로 만든 근사 옷을 보여드려요.";
  const bodyOnlyNote = "옷 모델을 표시하지 못해 신체만 보여드려요. 신체 정보 다시 입력을 눌러 재시도해 주세요.";
  const missingGarmentNote = () => preview && !bodyModelId ? approxNote : bodyOnlyNote;
  // 의류 서버의 착장 시뮬레이션 결과 안내 (anchors.json 의 garment 정보).
  const failLabels = {stretch_exceeded: "늘어남 허용 오차 초과", unsettled: "움직임이 안정되지 않음", body_penetration: "신체 관통",
    initial_intersection: "시작 위치에서 신체와 겹침", simulation_timeout: "계산 시간 초과",
    simulation_diverged: "변형이 크게 발산함", non_finite_simulation: "계산 불안정",
    simulation_interrupted: "계산 중단", simulation_incomplete: "마지막 저장 프레임",
    frame_timeout: "프레임 계산 시간 초과", pushout_rejected: "국소 보정이 치수 한계를 초과함",
    collision_region_exited: "옷이 충돌 계산 영역을 벗어남",
    compression_exceeded: "옷의 과도한 수축", invalid_rest_mesh: "의류 기준 메시 손상",
    invalid_cloth_mesh: "옷 메시의 겹침 또는 퇴화", validation_incomplete: "메시 검사 제한시간 초과",
    self_collision_setup_failed: "자기 충돌 계산 준비 실패", sam_sizing_failed: "SAM 신체 크기 맞춤 실패"};
  function clothNote(anchors) {
    const info = anchors?.garment;
    const samLabel = info?.fitting_mode === "sam_body_cloth_collision" ? "SAM 신체 맞춤 3D · " : "";
    if (info?.simulation_status === "failed") {
      const reasons = (info.failure_reasons || []).map(code => failLabels[code] || code).join(" · ");
      return samLabel + "착장 시뮬레이션 실패 · " + reasons + ". 실패한 옷의 마지막 모습을 그대로 보여드려요. ";
    }
    if (samLabel) return samLabel + "옷 크기를 신체에 맞춘 시뮬레이션이에요. ";
    if (info?.fitting_mode === "db_cloth_collision") return "상품 실측으로 만든 옷을 내 몸에 입혀 본 시뮬레이션이에요. 소재 특성은 실제와 다를 수 있어요. ";
    return "";
  }
  function catalogSize(size) {
    const sized = catalogSizes.filter(item => item.size_label === size.label && (!item.region || !size.region || item.region === size.region));
    return sized.length === 1 ? sized[0] : null;
  }
  // 서버 의류를 입힌 동안: 처음엔 원본 색(색상 버튼 선택 없음), 히트맵은 근사 옷에만 있어 끈다.
  function syncPanel() {
    const original = fitStage?.hasGarmentModel?.() ?? false;
    const heat = $("[data-toggle=heat]", panel);
    heat.disabled = original;
    heat.title = original ? "의류 서버 모델에는 핏 히트맵이 없어요" : "";
    if (original) heat.setAttribute("aria-pressed", "false");
    if (original && !colorChosen) for (const b of panel.querySelectorAll("[data-color]")) b.setAttribute("aria-pressed", "false");
  }
  function showMissingGarment(size) {
    // clearGarmentModel은 이전 garmentSpec을 다시 그리므로 먼저 비운다.
    // 새 사이즈 요청이 실패했을 때 이전 옷이 남아 있는 일도 막는다.
    fitStage.setGarment(null);
    fitStage.clearGarmentModel();
    if (bodyModelId || !preview) return null;
    const spec = garmentSpec(size);
    if (spec) fitStage.setGarment(spec);
    return spec;
  }
  // 사이즈를 바꾸면 그 사이즈의 의류 GLB 를 서버에서 받아 교체한다 (신체는 다시 만들지 않는다).
  async function swapGarment(size) {
    garmentSwap?.abort();
    const task = garmentSwap = new AbortController();
    const expectedBodyModelId = bodyModelId;
    const found = catalogSize(size);
    if (!found) {
      showMissingGarment(size);
      if (bodyModelId) step("tryon", "error");
      report(caption, "이 사이즈는 3D 카탈로그에 없어요. " + missingGarmentNote() + " " + viewHint);
      syncPanel();
      return;
    }
    report(caption, "이 사이즈의 옷 모델을 불러오고 있어요.", true);
    try {
      const pair = await requestPair(null, {garment_id: tryon.garment_id, size_id: found.size_id}, task.signal,
        () => report(caption, "이 사이즈의 옷 모델을 만들고 있어요.", true), undefined, expectedBodyModelId);
      if (pair.garment?.status !== "ready" && pair.garment?.preview_available !== true)
        throw Error(pair.garment?.message || "옷 모델을 받지 못했어요.");
      const {buffer, anchors} = await verifiedModel(pair.garment, "garment", task.signal, expectedBodyModelId);
      if (task.signal.aborted || !fitStage || expectedBodyModelId !== bodyModelId) return;
      await fitStage.setGarmentModel(buffer, category === "하의");
      if (task.signal.aborted || expectedBodyModelId !== bodyModelId) return;
      if (colorChosen) fitStage.setColor(color);
      step("tryon", anchors.garment?.simulation_status === "failed" ? "error" : "done");
      report(caption, clothNote(anchors) + viewHint);
    } catch (error) {
      if (task.signal.aborted || !fitStage) return;
      showMissingGarment(size);
      if (bodyModelId) step("tryon", "error");
      report(caption, (error instanceof TypeError ? "옷 모델 서버에 연결하지 못했어요." : error.message) + " " + missingGarmentNote() + " " + viewHint);
    }
    syncPanel();
  }

  function garmentSpec(size) {
    const m = size.measures;
    const spec = {w: m["가슴단면"], sh: m["어깨너비"], len: m["총장"], sl: m["소매길이"]};
    return category === "상의·아우터" && Object.values(spec).every(Number.isFinite) ? spec : null;
  }
  async function mountStage(glb, measurements, size, note, taskSignal, cloth = null) {
    await loadThree();
    if (taskSignal.aborted) return;
    fitStage?.destroy();
    fitStage = null;
    const holder = document.createElement("div");
    holder.className = "room-3d";
    holder.style.visibility = "hidden";
    stage.append(holder);
    let spec = !cloth && preview && !bodyModelId ? garmentSpec(size) : null;
    await new Promise((resolve, reject) => {
      taskSignal.addEventListener("abort", () => reject(taskSignal.reason), {once: true});
      fitStage = window.FitStage.mount(holder, {glb, measurements, garment: spec, color,
        onReady: resolve, onError: () => reject(Error("3D 몸 모델을 열지 못했어요."))});
    });
    if (cloth) {
      try { await fitStage.setGarmentModel(cloth, category === "하의"); }
      catch (error) {
        spec = showMissingGarment(size);
        note = (error.message || "의류 모델을 몸에 맞추지 못했어요.") + " " + missingGarmentNote() + " ";
      }
    }
    for (const child of [...stage.children]) if (child !== holder) child.remove();
    holder.style.visibility = "";
    const dressed = cloth && fitStage.hasGarmentModel();
    report(caption, note + (dressed || spec || bodyModelId ? "" : "이 옷은 아직 3D로 입힐 수 없어 몸만 보여드려요. ") + viewHint);
  }

  function showPanel() {
    form.hidden = true;
    panel.hidden = false;
    $(".dress-chips", panel).innerHTML = sizes.map((size, i) =>
      `<button type="button" data-size="${i}" aria-pressed="${i === currentSize}">${esc(sizeName(size).replace(" · ", "·"))}</button>`).join("");
    syncPanel();
  }
  panel.addEventListener("click", event => {
    const button = event.target.closest("button");
    if (!button) return;
    if (button.classList.contains("dress-edit")) { panel.hidden = true; form.hidden = false; height.focus(); return; }
    if (!fitStage) return;
    const press = (group, pressed) => { for (const b of panel.querySelectorAll(group)) b.setAttribute("aria-pressed", String(b === pressed)); };
    if (button.dataset.size) {
      currentSize = Number(button.dataset.size);
      sizePick.value = String(currentSize);
      press("[data-size]", button);
      if (tryon && !tryon.preview && catalogSizes.length) swapGarment(sizes[currentSize]);
      else if (preview) {
        const spec = garmentSpec(sizes[currentSize]);
        if (spec) fitStage.setGarment(spec);
      }
      renderVerdict();
      if (lastBody && !(shotFit && shotIndex === currentSize)) judge(sizes[currentSize], lastBody);
    } else if (button.dataset.color) {
      color = button.dataset.color;
      colorChosen = true;
      press("[data-color]", button);
      fitStage.setColor(color);
    } else if (button.dataset.toggle) {
      const on = button.getAttribute("aria-pressed") !== "true";
      button.setAttribute("aria-pressed", String(on));
      if (button.dataset.toggle === "heat") fitStage.setHeatmap(on);
      if (button.dataset.toggle === "undress") fitStage.setGarmentVisible(!on);
      if (button.dataset.toggle === "rotate") fitStage.setAutoRotate(on);
    }
  });

  async function dress(size, body, taskSignal) {
    garmentSwap?.abort();
    bodyModelId = null;
    step("tryon", "busy");
    currentSize = sizes.indexOf(size);
    lastBody = body;
    const started = performance.now();
    const elapsed = () => Math.round((performance.now() - started) / 1000);
    try {
      let glb, measurements, cloth = null, note = "", garmentFailed = false;
      if (!tryon && !preview) {
        throw Error(serviceError || "3D 피팅 연결을 확인하지 못했어요. 잠시 후 다시 입어보기를 눌러 주세요.");
      }
      if (tryon && !tryon.preview) {
        // 웹앱 → Redis → 신체·의류 VM. 신체 GLB와 치수를 받아 이 화면에서 옷을 입힌다.
        stageLoading("사진을 보내고 있어요.");
        const {items = []} = await readJson("/api/v2/garment-catalog/" + tryon.garment_id + "/sizes", {signal: taskSignal});
        const sized = items.filter(item => item.size_label === size.label && (!item.region || !size.region || item.region === size.region));
        if (sized.length !== 1) throw Error("이 사이즈는 3D 카탈로그에 없어요. 다른 사이즈로 입어 보세요.");
        catalogSizes = items;
        const picture = await readBuyerPhoto(shot, taskSignal);
        const pair = await requestPair({...body, ...picture}, {garment_id: tryon.garment_id, size_id: sized[0].size_id}, taskSignal,
          () => stageLoading(`내 몸과 옷의 3D 모델을 만들고 있어요 · ${elapsed()}초`), {item_code: garment.item_code, size_label: size.label});
        // 신체가 실패하면 워커가 "판정할 수 없습니다"를, /fit 이 실패하면 null 을 준다 (3D 는 그대로, 판정만 빠짐).
        shotFit = pair.fit ?? null;
        shotIndex = currentSize;
        renderVerdict();
        if (pair.body?.status !== "ready") throw Error(pair.body?.message || "3D 몸을 만들지 못했어요.");
        stageLoading("3D 몸을 받아 옷을 입히고 있어요.");
        glb = (await verifiedModel(pair.body, "body", taskSignal)).buffer;
        measurements = await readMeasurements(pair.body, taskSignal).catch(() => null) ?? measuresFromGlb(glb);
        taskSignal.throwIfAborted();
        bodyModelId = pair.body.model_id;
        // 의류 서버가 이 몸에 맞춰 시뮬레이션한 의류 GLB. 시뮬레이션이 실패해도 마지막 모습(preview)은 보여 준다.
        // 없거나 검증에 실패하면 실제 오류를 알리고 신체만 보여 준다.
        let fitted = null, garmentError = "";
        if (pair.garment?.status === "ready" || pair.garment?.preview_available === true) {
          try { fitted = await verifiedModel(pair.garment, "garment", taskSignal, bodyModelId); }
          catch (error) {
            taskSignal.throwIfAborted();
            garmentError = error.message || "옷 모델을 확인하지 못했어요.";
          }
        }
        cloth = fitted?.buffer ?? null;
        garmentFailed = pair.garment?.status !== "ready";
        if (!cloth) note = (garmentError || pair.garment?.message || "옷 모델을 받지 못했어요.") + " " + bodyOnlyNote + " ";
        else note = clothNote(fitted.anchors);
      } else {
        shotFit = null;
        if (tryon?.preview) {
          for (const text of ["사진을 보내고 있어요.", "내 몸 3D 모델을 만들고 있어요", "3D 몸을 받아 옷을 입히고 있어요."]) {
            stageLoading(text);
            await wait(2200, taskSignal).catch(() => {});
            if (taskSignal.aborted) return;
          }
        } else stageLoading("예시 체형에 옷을 입히고 있어요.");
        const model = await fetch("/static/models/example-body.glb", {signal: taskSignal});
        if (!model.ok) throw Error("예시 체형을 불러오지 못했어요.");
        [glb, measurements] = await Promise.all([model.arrayBuffer(), readJson("/static/data/example-measurements.json", {signal: taskSignal})]);
        note = "예시 체형(키 175cm)이에요. 3D 서비스가 연결되면 촬영한 내 몸으로 바뀌어요. ";
      }
      if (!measurements) throw Error("몸 치수 정보를 찾지 못했어요.");
      stopCamera();
      await mountStage(glb, measurements, size, note, taskSignal, cloth);
      if (taskSignal.aborted) return;
      step("tryon", bodyModelId && (garmentFailed || !fitStage?.hasGarmentModel()) ? "error" : "done");
      showPanel();
      renderVerdict();
    } catch (error) {
      if (taskSignal.aborted) return;
      fitStage?.destroy();
      fitStage = null;
      step("tryon", "error");
      stageNote(esc(error instanceof TypeError ? "3D 모델 서버에 연결하지 못했어요." : error.message));
    }
  }

  async function run() {
    job?.abort();
    for (const [input, text] of [[height, "키는 120~230 cm 사이로 입력해 주세요."], [weight, "몸무게는 30~250 kg 사이로 입력해 주세요."]]) {
      if (!input.validity.valid) { report(status, text); input.focus(); return; }
    }
    const task = job = new AbortController();
    const size = sizes[Number(sizePick.value)];
    const body = {height_cm: height.valueAsNumber, weight_kg: weight.valueAsNumber};
    submit.disabled = true;
    submit.setAttribute("aria-busy", "true");
    try {
      if (!tryon && !preview) {
        report(status, "3D 피팅 연결을 확인하고 있어요.", true);
        await refreshService();
        if (task.signal.aborted || job !== task) return;
        if (!tryon) {
          step("tryon", "error");
          await judge(size, body);
          if (!task.signal.aborted && job === task) report(status, serviceError || "3D 피팅을 준비하지 못했어요. 잠시 후 다시 입어보기를 눌러 주세요.");
          return;
        }
      }
      if (tryon && !shot) { report(status, "왼쪽에서 전신 사진을 촬영하거나 골라 주세요."); $("[data-act=snap]", stage)?.focus(); return; }
      if (tryon && !consent.checked) { report(status, "사진 전송에 동의해 주세요."); consent.focus(); return; }
      report(status, "3D 착장과 핏 판정을 준비하고 있어요.", true);
      step("body", "done");
      await Promise.all([dress(size, body, task.signal), judge(size, body)]);
      if (!task.signal.aborted && job === task) report(status, "");
    } finally {
      if (job === task) {
        submit.disabled = false;
        submit.removeAttribute("aria-busy");
        submit.firstChild.textContent = "다시 입어보기";
      }
    }
  }
  form.onsubmit = event => { event.preventDefault(); run(); };
  form.addEventListener("input", () => report(status, ""));
}

// ---------------------------------------------------------------- 화면 전환
let controller;
function render() {
  controller?.abort();
  controller = new AbortController();
  const route = location.hash.slice(1);
  const fit = /^fit\/(\d{1,9})$/.exec(route);
  view.classList.toggle("wide-home", !fit);
  document.title = "입어봄 · 3D 피팅룸";
  if (fit) room(Number(fit[1]), controller.signal);
  else home(controller.signal);
  window.scrollTo(0, 0);
  view.focus({preventScroll: true});
}
window.addEventListener("hashchange", render);
render();
