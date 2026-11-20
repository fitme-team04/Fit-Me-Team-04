export const view = document.getElementById("view");
export const $ = (selector, root = view) => root.querySelector(selector);

export function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;"})[c]);
}

// 기다리는 동안에는 문구 앞에 회전 표시를 붙인다. 같은 요소에는 항상 이 함수로 쓴다.
export function report(element, text, busy = false) {
  element.textContent = text;
  element.toggleAttribute("data-busy", busy && Boolean(text));
}

export const loadingMark = '<p class="flow-loading" role="status" data-busy>잠시만 기다려 주세요.</p>';

export function flow(title, intro, contents) {
  view.innerHTML = `<div class="flow"><a class="backlink" href="#home">← 처음으로</a>
    <h1>${esc(title)}</h1><p class="intro">${esc(intro)}</p>${contents}</div>`;
}
