// 입어봄 화면 동작 — 프레임워크 없이 순수 자바스크립트
// 구조: state(지금 상태) 를 바꾸고 → render() 가 그 상태대로 화면을 다시 그림
// 서버와 대화: api() 함수 하나로 /api/... 를 부름 (main.py 의 주소와 1:1)

const state = {
  step: 1,            // 1 등록 · 2 상품·내 정보 · 3 추천
  product: null,      // /api/product/resolve 결과
  candidates: null,   // 사진 선택 후 상품 후보
  photoUrl: null,     // 고른 사진 미리보기 (서버로 보내지 않음)
  form: { gender: "male", height_cm: "", weight_kg: "", mine: {} },
  result: null,       // /api/recommend 결과
  compareWith: null,  // 표에서 비교할 다른 사이즈
  busy: false,
  error: null,
};

const view = document.getElementById("view");

// ---------- 서버 호출 ----------
async function api(path, body) {
  const options = body === undefined
    ? {}
    : { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) };
  const res = await fetch(path, options);
  if (!res.ok) {
    const detail = await res.text();
    throw new Error("서버 오류 " + res.status + ": " + detail.slice(0, 200));
  }
  return res.json();
}

// ---------- 도우미 ----------
// 글자 안의 < > & 를 안전하게 (DB 에서 온 상품명을 그대로 HTML 에 넣지 않기 위해)
function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
function signed(n) { return (n > 0 ? "+" : "") + n; }
function go(step) { state.step = step; state.error = null; render(); window.scrollTo(0, 0); }
async function run(task) {
  state.busy = true; state.error = null; render();
  try { await task(); } catch (e) { state.error = e.message; }
  state.busy = false; render();
}

// ---------- 상단: 데이터 연결 상태 배지 ----------
async function loadHealth() {
  const badge = document.getElementById("mode-badge");
  try {
    const h = await api("/api/health");
    badge.textContent = (h.db_connected ? "DB 연결" : "데모 데이터") + " · " + (h.ai_configured ? "AI 설명" : "템플릿 설명");
    badge.className = "badge " + (h.db_connected ? "db" : "demo");
    badge.title = h.db_connected ? "팀 MySQL 에서 읽는 중" : "DB 미연결: " + (h.db_error || "");
  } catch (e) {
    badge.textContent = "서버 연결 안 됨";
  }
}

// ---------- 1단계: 링크 / 사진 ----------
function step1() {
  const candidates = state.candidates;
  return `
    <div class="hero">
      <div class="tag">THE EVERYDAY EDIT</div>
      <h1>이 옷, 내 사이즈는?</h1>
      <p>유니클로 상품 링크나 사진으로 시작해요.</p>
    </div>

    <form id="link-form">
      <label class="field"><span>유니클로 상품 링크</span>
        <input type="text" id="link" inputmode="url" placeholder="https://www.uniqlo.com/kr/ko/products/E422992-000" autocomplete="off" value="${esc(state.link || "")}">
      </label>
      <button class="btn red" ${state.busy ? "disabled" : ""}>
        <span>${state.busy ? '<span class="spin"></span> 확인 중' : "이 상품 확인하기"}</span><span>→</span>
      </button>
    </form>
    <button class="btn link" id="sample">예시 링크로 해보기</button>

    <div class="or">또는</div>

    <label class="btn ghost" for="photo"><span>사진으로 상품 찾기</span><span>+</span></label>
    <input type="file" id="photo" accept="image/*" hidden>
    <p class="small">사진은 상품 후보를 찾는 데만 써요. 내 전신 사진은 받지 않아요.</p>

    ${state.photoUrl ? `<h2>찾으시는 상품이 맞나요?</h2><img class="preview" src="${state.photoUrl}" alt="선택한 의류 사진">` : ""}
    ${candidates ? `
      <div class="alert info">사진 검색(Azure AI Search)은 아직 연결 전이라, 등록된 상품 목록에서 골라 주세요.</div>
      ${candidates.items.map((p) => `
        <button class="card pick product" data-code="${esc(p.item_code)}">
          <div class="thumb">👕</div>
          <div><b>${esc(p.garment_name)}</b>
            <div class="meta">${esc(p.brand_name)} · ${esc(p.item_code)} · 실측 ${p.measured_sizes}개 사이즈</div></div>
        </button>`).join("")}
      <button class="btn link" id="retry-photo">찾는 상품이 없어요 → 링크로 입력</button>` : ""}
  `;
}

function bindStep1() {
  const link = document.getElementById("link");
  document.getElementById("link-form").onsubmit = (e) => {
    e.preventDefault();
    resolve(link.value);
  };
  document.getElementById("sample").onclick = () => {
    link.value = "https://www.uniqlo.com/kr/ko/products/E422992-000/00";
    resolve(link.value);
  };
  document.getElementById("photo").onchange = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    state.photoUrl = URL.createObjectURL(file);
    run(async () => { state.candidates = await api("/api/products"); });
  };
  document.querySelectorAll(".pick").forEach((el) => { el.onclick = () => resolve(el.dataset.code); });
  const retry = document.getElementById("retry-photo");
  if (retry) retry.onclick = () => { state.candidates = null; state.photoUrl = null; render(); document.getElementById("link").focus(); };
}

function resolve(link) {
  state.link = link;
  run(async () => {
    const r = await api("/api/product/resolve", { link });
    if (!r.ok) throw new Error(r.error);
    state.product = r.product;
    state.result = null;
    go(2);
  });
}

// ---------- 2단계: 상품 확인 + 내 정보 ----------
function step2() {
  const p = state.product;
  const f = state.form;
  const mine = f.mine;
  return `
    <h1>내 정보로<br>좁혀볼까요?</h1>
    <p class="lead">추천에 필요한 정보만 입력해요.</p>

    <div class="card product">
      <div class="thumb">👕</div>
      <div style="flex:1"><b>${esc(p.garment_name)}</b>
        <div class="meta">${esc(p.brand_name)} · ${esc(p.item_code)} · ${esc(p.region)}</div>
        <div class="meta">실측 있는 사이즈: ${p.measured_sizes.length ? esc(p.measured_sizes.join(", ")) : "없음"}</div>
      </div>
      <button class="btn link" id="change" style="width:auto">상품 변경</button>
    </div>
    ${p.can_recommend ? "" : `<div class="alert err">이 상품은 아직 사이즈별 실측이 없어 추천을 보류해요. 다른 상품을 선택해 주세요.</div>`}

    <h2>성별</h2>
    <div class="chips">
      <button class="chip" data-gender="male" aria-pressed="${f.gender === "male"}">남성</button>
      <button class="chip" data-gender="female" aria-pressed="${f.gender === "female"}">여성</button>
    </div>

    <h2>키 · 몸무게</h2>
    <div class="row">
      <label class="field unit"><input type="number" id="height" min="120" max="230" step="0.1" placeholder="170" value="${esc(f.height_cm)}" aria-label="키"><em>cm</em></label>
      <label class="field unit"><input type="number" id="weight" min="30" max="250" step="0.1" placeholder="65" value="${esc(f.weight_kg)}" aria-label="몸무게"><em>kg</em></label>
    </div>

    <details class="more" ${Object.keys(mine).length ? "open" : ""}>
      <summary>잘 맞는 옷의 실측 추가 (선택)</summary>
      <p class="small">평소 잘 맞는 상의를 평평하게 놓고 재요. 가슴단면 = 겨드랑이 아래 좌우 끝 사이 길이(둘레 아님).</p>
      <div class="row3">
        <label class="field unit"><span>가슴단면</span><input type="number" step="0.5" id="m-chest" value="${esc(mine.chest_width ?? "")}"><em>cm</em></label>
        <label class="field unit"><span>어깨너비</span><input type="number" step="0.5" id="m-shoulder" value="${esc(mine.garment_shoulder_width ?? "")}"><em>cm</em></label>
        <label class="field unit"><span>총장</span><input type="number" step="0.5" id="m-length" value="${esc(mine.body_length ?? "")}"><em>cm</em></label>
      </div>
    </details>

    ${state.error ? `<div class="alert err">${esc(state.error)}</div>` : ""}

    <div style="margin-top:22px">
      <button class="btn red" id="go" ${state.busy || !p.can_recommend ? "disabled" : ""}>
        <span>${state.busy ? '<span class="spin"></span> 분석 중' : "내 사이즈 추천받기"}</span><span>→</span>
      </button>
    </div>
    <p class="small" style="text-align:center">입력한 정보는 이 화면에서만 쓰고 저장하지 않아요.</p>
  `;
}

function readForm() {
  const f = state.form;
  f.height_cm = document.getElementById("height").value;
  f.weight_kg = document.getElementById("weight").value;
  const mine = {};
  const pairs = [["m-chest", "chest_width"], ["m-shoulder", "garment_shoulder_width"], ["m-length", "body_length"]];
  pairs.forEach(([id, code]) => {
    const v = document.getElementById(id).value;
    if (v !== "") mine[code] = Number(v);
  });
  f.mine = mine;
}

function bindStep2() {
  document.getElementById("change").onclick = () => { state.candidates = null; state.photoUrl = null; go(1); };
  document.querySelectorAll("[data-gender]").forEach((el) => { el.onclick = () => { readForm(); state.form.gender = el.dataset.gender; render(); }; });
  document.getElementById("go").onclick = () => {
    readForm();
    const f = state.form;
    if (!f.height_cm || !f.weight_kg) { state.error = "키와 몸무게를 입력해 주세요."; render(); return; }
    run(async () => {
      const r = await api("/api/recommend", {
        item_code: state.product.item_code, region: state.product.region,
        gender: f.gender, height_cm: Number(f.height_cm), weight_kg: Number(f.weight_kg),
        my_garment: Object.keys(f.mine).length ? f.mine : null,
      });
      if (!r.ok) throw new Error(r.errors.join(" / "));
      state.result = r;
      state.compareWith = r.compare_with;
      go(3);
    });
  };
}

// ---------- 3단계: 추천 + 비교 ----------
function step3() {
  const r = state.result;
  const ex = r.explanation;
  const names = r.measure_names;
  const bySize = Object.fromEntries(r.sizes.map((s) => [s.size_label, s]));
  const rec = bySize[r.recommended];
  const other = state.compareWith ? bySize[state.compareWith] : null;
  const mine = r.input.my_garment;
  const codes = ["chest_width", "garment_shoulder_width", "body_length", "sleeve_length"].filter((c) => c in rec.garment);
  const measured = r.sizes.filter((s) => s.status !== "nodata" && s.size_label !== r.recommended);

  const cell = (size, code) => {
    if (!size || !(code in size.garment)) return "<td>-</td>";
    const v = size.garment[code];
    const d = mine[code] !== undefined ? ` <small class="${v - mine[code] >= 0 ? "pos" : "neg"}">(${signed(Math.round((v - mine[code]) * 10) / 10)})</small>` : "";
    return `<td>${v}${d}</td>`;
  };

  return `
    <div class="result">
      <div class="size">${esc(r.recommended)}</div>
      <div>
        <div class="kicker">YOUR SIZE, YOUR WAY</div>
        <div class="summary">${esc(ex.summary)}</div>
        <div class="sub">${esc(r.product.garment_name)} · ${r.basis === "my_garment" ? "내 옷 비교 기준" : "팀 판정 기준(ease_check)"}</div>
      </div>
    </div>

    <h2>이렇게 비교했어요</h2>
    <div class="card">
      <ul class="points">${ex.points.map((p) => `<li>${esc(p)}</li>`).join("")}</ul>
      <span class="src">${ex.source === "azure_openai" ? "AI 설명 · Azure OpenAI (계산된 근거만 사용)" : "기본 설명"}${ex.note ? " · " + esc(ex.note) : ""}</span>
    </div>
    ${ex.ask_more ? `<div class="alert info">💡 ${esc(ex.ask_more)}</div>` : ""}

    <h2>숫자로 보는 차이</h2>
    ${measured.length ? `<div class="toggle chips">${measured.map((s) => `<button class="chip" data-cmp="${esc(s.size_label)}" aria-pressed="${s.size_label === state.compareWith}">vs ${esc(s.size_label)}</button>`).join("")}</div>` : ""}
    <div class="card">
      <table class="cmp">
        <thead><tr><th>부위 (옷 실측, cm)</th>${Object.keys(mine).length ? "<th>내 옷</th>" : ""}<th class="hl">${esc(r.recommended)}</th>${other ? `<th>${esc(other.size_label)}</th>` : ""}</tr></thead>
        <tbody>${codes.map((c) => `<tr><td>${esc(names[c] || c)}</td>${Object.keys(mine).length ? `<td>${mine[c] ?? "-"}</td>` : ""}${cell(rec, c).replace("<td>", '<td class="hl">')}${other ? cell(other, c) : ""}</tr>`).join("")}</tbody>
      </table>
      ${Object.keys(mine).length ? '<p class="small">괄호 안 숫자는 내 옷과의 차이예요.</p>' : ""}
    </div>

    ${r.warnings.map((w) => `<div class="alert info">${esc(w)}</div>`).join("")}

    <details class="more">
      <summary>계산 근거 자세히 (개발·검증용)</summary>
      <p class="small"><b>데이터</b>: ${r.mode === "db" ? "팀 MySQL DB" : "데모 데이터 (DB 미연결)"} · <b>몸 치수</b>: ${esc(r.estimator)}</p>
      <ul class="points">${Object.entries(r.body_used).map(([c, v]) => `<li>${esc(names[c] || c)}: ${v.value_cm}cm <span class="small">(${v.source === "entered" ? "입력" : "추정"})</span></li>`).join("")}</ul>
      <p class="small"><b>규칙</b>: 여유분 = 옷 치수 × factor − 몸 치수. 사이즈 판정은 팀 기준 ${esc(r.rule.rules_version ?? "ease_check")}을 따라요.
        팀 기준선 규칙(_추천.py) 결과: <b>${esc(r.team_baseline ?? "-")}</b></p>
    </details>

    <div style="margin-top:22px">
      <a class="btn red" href="${esc(r.product.product_url)}" target="_blank" rel="noopener"><span>${esc(r.recommended)} 선택하고 원본 상품 보기</span><span>→</span></a>
      <button class="btn ghost" id="restart"><span>다른 상품 비교하기</span><span>↺</span></button>
    </div>
  `;
}

function bindStep3() {
  document.querySelectorAll("[data-cmp]").forEach((el) => { el.onclick = () => { state.compareWith = el.dataset.cmp; render(); }; });
  document.getElementById("restart").onclick = () => { state.product = null; state.result = null; state.candidates = null; state.photoUrl = null; go(1); };
}

// ---------- 그리기 ----------
function render() {
  document.querySelectorAll(".steps li").forEach((li) => {
    const n = Number(li.dataset.step);
    li.className = n === state.step ? "on" : n < state.step ? "done" : "";
  });
  const back = document.getElementById("back");
  back.hidden = state.step === 1;
  back.onclick = () => go(state.step - 1);

  if (state.step === 1) {
    view.innerHTML = step1() + (state.error ? `<div class="alert err">${esc(state.error)}</div>` : "");
    bindStep1();
  } else if (state.step === 2) {
    view.innerHTML = step2();
    bindStep2();
  } else {
    view.innerHTML = step3();
    bindStep3();
  }
}

loadHealth();
render();
