/*!
 * fit-stage.js : 내 체형 GLB 위에 옷(상의)을 입히는 3D 스테이지 모듈
 * - 디자인(배경/박스/버튼)은 포함하지 않습니다. 넘겨준 컨테이너 안에 canvas만 채웁니다.
 * - 필요: three r128 (build/three.min.js) + examples/js/controls/OrbitControls.js + examples/js/loaders/GLTFLoader.js
 *   (전역 THREE 사용)
 *
 * const stage = FitStage.mount(document.querySelector("#stage"), {
 *   glb: "/api/body/6.glb",              // URL 또는 ArrayBuffer
 *   measurements: measurementsJson,      // {measurements:{...}} 또는 {...} (키: height_cm, chest_girth_cm ...)
 *   garment: {w:52, sh:45.5, len:68, sl:20.5},  // 사이즈표(cm): 가슴단면, 어깨너비, 총장, 소매길이
 *   color: "#f1efe8",
 *   onFit: r => {...},                   // 핏 계산 결과 (옷/사이즈 바뀔 때마다)
 *   onReady: () => {...}, onError: e => {...}
 * });
 * stage.setGarment(spec) / setColor(hex) / setHeatmap(bool) / setGarmentVisible(bool)
 * stage.setAutoRotate(bool) / resetView() / destroy()
 * stage.setGarmentModel(glb, lowerBody) → Promise
 *   의류 서버가 만든 GLB를 그대로 입힌다(원본 재질·색상 유지). 상의는 양쪽 fit_anchor,
 *   하의는 fit_anchor_waist 를 맞추는 강체 변환이라 크기는 바꾸지 않는다(3D팀 web.js fitGarment 와 같은 규칙).
 *   상의는 입히기 전에 팔(어깨→손목)과 소매(어깨→소매끝) 각도를 비교해, 신체 GLB 의 fitme_pose 허용 오차를
 *   넘으면 reject 한다(3D팀 pose.js compareSleeves 와 같은 규칙).
 *   서버 의류가 있는 동안에는 자체 옷 생성(setGarment)을 쓰지 않는다. clearGarmentModel() 로 되돌린다.
 */
(function (root) {
  "use strict";
  var FALLBACK_MAIN = "지금은 3D 착장을 볼 수 없어요.\n핏 판정 결과를 확인해 주세요.";
  var FALLBACK_NOTE = "3D 피팅 연결을 확인하지 못했어요. 지금은 핏 판정만 확인할 수 있어요.";
  var T23 = Math.tan(23 * Math.PI / 180);
  var lerp = function (a, b, t) { return a + (b - a) * t; };
  var sstep = function (a, b, x) { var t = Math.min(1, Math.max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t); };

  function fitLabel(e) { return e < 0 ? "작음" : e < 4 ? "타이트" : e < 10 ? "보통" : e < 16 ? "넉넉함" : "오버핏"; }

  function mount(el, opts) {
    if (!root.THREE || !THREE.GLTFLoader || !THREE.OrbitControls) throw new Error("FitStage: THREE / GLTFLoader / OrbitControls 필요");
    opts = opts || {};
    var raw = opts.measurements && opts.measurements.measurements ? opts.measurements.measurements : (opts.measurements || {});
    var v = function (k) { var x = raw[k]; return x && typeof x === "object" ? (x.measured != null ? x.measured : x.target) : x; };

    if (getComputedStyle(el).position === "static") el.style.position = "relative";
    var canvas = document.createElement("canvas");
    canvas.style.cssText = "position:absolute;inset:0;width:100%;height:100%;display:block;touch-action:none;background:transparent";
    el.appendChild(canvas);

    var renderer = new THREE.WebGLRenderer({ canvas: canvas, antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(root.devicePixelRatio || 1, 2));
    var scene = new THREE.Scene();
    var cam = new THREE.PerspectiveCamera(30, 1, 0.01, 100);
    scene.add(new THREE.HemisphereLight(0xffffff, 0x8a7f73, 0.95));
    var key = new THREE.DirectionalLight(0xffffff, 0.85); key.position.set(2, 3, 4); scene.add(key);
    var rim = new THREE.DirectionalLight(0xffffff, 0.3); rim.position.set(-3, 2, -3); scene.add(rim);
    var controls = new THREE.OrbitControls(cam, canvas);
    controls.enableDamping = true; controls.autoRotateSpeed = 1.4;

    var state = { garmentSpec: opts.garment || null, color: opts.color || "#f1efe8", heat: false, visible: true };
    var body, src, u, minY, cx, cz, garment = null, home, raf = 0, dead = false, overlay = null;
    var bodyScene = null, model = null, modelTint = null;   // 신체 GLB 원본 장면(기준점 위치용), 서버 의류 GLB

    function resize() {
      var w = el.clientWidth || 1, h = el.clientHeight || 1;
      renderer.setSize(w, h, false); cam.aspect = w / h; cam.updateProjectionMatrix();
    }
    var ro = root.ResizeObserver ? new ResizeObserver(resize) : null;
    if (ro) ro.observe(el); else root.addEventListener("resize", resize);
    resize();

    function fail(err) {
      if (overlay || dead) return;
      overlay = document.createElement("div");
      overlay.style.cssText = "position:absolute;inset:0;display:grid;place-items:center;text-align:center;white-space:pre-line;line-height:1.7;font-size:14px;color:inherit;opacity:.75;pointer-events:none";
      overlay.textContent = FALLBACK_MAIN;
      var note = document.createElement("div");
      note.style.cssText = "position:absolute;left:16px;bottom:12px;font-size:12px;opacity:.8;white-space:normal;text-align:left";
      note.textContent = FALLBACK_NOTE;
      overlay.appendChild(note);
      el.appendChild(overlay);
      canvas.style.display = "none";
      if (opts.onError) opts.onError(err);
    }

    function onGltf(gltf) {
      if (dead) return;
      try {
        gltf.scene.updateMatrixWorld(true);
        bodyScene = gltf.scene;
        var best = null;
        gltf.scene.traverse(function (o) {
          if (o.isMesh && (!best || o.geometry.attributes.position.count > best.geometry.attributes.position.count)) best = o;
        });
        var g = best.geometry.clone(); g.applyMatrix4(best.matrixWorld);
        if (!g.attributes.normal) g.computeVertexNormals();
        if (!g.index) {
          var n = g.attributes.position.count, a = new Uint32Array(n);
          for (var i = 0; i < n; i++) a[i] = i;
          g.setIndex(new THREE.BufferAttribute(a, 1));
        }
        g.computeBoundingBox();
        var bb = g.boundingBox;
        minY = bb.min.y; u = (bb.max.y - bb.min.y) / v("height_cm");
        cx = (bb.max.x + bb.min.x) / 2; cz = (bb.max.z + bb.min.z) / 2;
        src = g;
        body = new THREE.Mesh(g, new THREE.MeshStandardMaterial({ color: 0xd8bda3, roughness: 0.8 }));
        scene.add(body);
        var H = bb.max.y - bb.min.y, ctr = new THREE.Vector3(cx, (bb.max.y + bb.min.y) / 2, cz);
        home = { pos: new THREE.Vector3(cx, ctr.y, cz + H / 2 / Math.tan(cam.fov * Math.PI / 360) * 1.3), tgt: ctr };
        resetView();
        if (state.garmentSpec) dress();
        if (opts.onReady) opts.onReady();
      } catch (e) { fail(e); }
    }

    try {
      if (typeof opts.glb === "string") new THREE.GLTFLoader().load(opts.glb, onGltf, undefined, fail);
      else new THREE.GLTFLoader().parse(opts.glb, "", onGltf, fail);
    } catch (e) { fail(e); }

    function girthAt(y) {
      var hy = v("hip_line_height_cm"), wy = v("waist_line_height_cm"), cy = v("chest_line_height_cm");
      if (y <= hy) return v("hip_girth_cm");
      if (y <= wy) return lerp(v("hip_girth_cm"), v("waist_girth_cm"), (y - hy) / (wy - hy));
      if (y <= cy) return lerp(v("waist_girth_cm"), v("chest_girth_cm"), (y - wy) / (cy - wy));
      return v("chest_girth_cm");
    }

    function dress() {
      if (!src) return;
      if (garment) { scene.remove(garment); garment.geometry.dispose(); garment.material.dispose(); garment = null; }
      if (model) return;   // 서버 의류 GLB 를 입힌 동안에는 자체 옷을 만들지 않는다
      var c = state.garmentSpec;
      if (!c) { return; }
      var P = src.attributes.position, N = src.attributes.normal, n = P.count;
      var hh = v("height_cm"), yNeck = 0.85 * hh, xs = v("shoulder_width_cm") / 2;
      var yAcr = yNeck - (xs - 6) * T23, hem = yNeck - 1 - c.len, G = 2 * c.w;
      var shExtra = Math.max(0, (c.sh - v("shoulder_width_cm")) / 2);
      var out = new Float32Array(n * 3), keep = new Uint8Array(n), easeA = new Float32Array(n);
      for (var i = 0; i < n; i++) {
        var px = P.getX(i), py = P.getY(i), pz = P.getZ(i);
        var x = (px - cx) / u, y = (py - minY) / u, ax = Math.abs(x);
        var yCut = ax <= 6 ? yNeck - 1 : (ax <= xs ? yNeck - 1 - (ax - 6) * T23 : 1e9);
        var inc = false, off = 0, ease = 99;
        if (y <= yCut) {
          if (ax <= xs - 0.5) {
            if (y >= hem) {
              inc = true; ease = G - girthAt(y); off = Math.max(0.3, ease / (2 * Math.PI));
              off += shExtra * sstep(v("chest_line_height_cm"), yAcr, y) * sstep(8, xs - 0.5, ax);
            }
          } else if (Math.hypot(ax - xs, y - yAcr) <= c.sl) { inc = true; off = 1.2; ease = G - v("chest_girth_cm"); }
        }
        keep[i] = inc ? 1 : 0; easeA[i] = ease;
        out[i * 3] = px + N.getX(i) * off * u; out[i * 3 + 1] = py + N.getY(i) * off * u; out[i * 3 + 2] = pz + N.getZ(i) * off * u;
      }
      var idx = src.index.array, tri = [];
      for (var t = 0; t < idx.length; t += 3) {
        var a = idx[t], b = idx[t + 1], d = idx[t + 2];
        if (keep[a] && keep[b] && keep[d]) tri.push(a, b, d);
      }
      var g = new THREE.BufferGeometry();
      g.setAttribute("position", new THREE.BufferAttribute(out, 3));
      g.setIndex(tri); g.computeVertexNormals(); g.userData.ease = easeA;
      garment = new THREE.Mesh(g, new THREE.MeshStandardMaterial({ vertexColors: true, side: THREE.DoubleSide, roughness: 0.92 }));
      garment.visible = state.visible;
      scene.add(garment);
      paint();
      if (opts.onFit) opts.onFit(fitResult());
    }

    function fitResult() {
      var c = state.garmentSpec, G = 2 * c.w;
      var ch = G - v("chest_girth_cm"), wa = G - v("waist_girth_cm"), hi = G - v("hip_girth_cm"), sh = c.sh - v("shoulder_width_cm");
      return {
        chest: { ease_cm: ch, label: fitLabel(ch), body_girth_cm: v("chest_girth_cm"), garment_girth_cm: G },
        waist: { ease_cm: wa, label: fitLabel(wa) },
        hip: { ease_cm: hi, label: fitLabel(hi) },
        shoulder: { diff_cm: sh, label: sh > 2 ? "드롭숄더" : sh < -1 ? "좁음" : "맞음" },
        length_cm: c.len, sleeve_cm: c.sl
      };
    }

    function paint() {
      if (!garment) return;
      var g = garment.geometry, e = g.userData.ease, n = e.length, col = new Float32Array(n * 3);
      var base = new THREE.Color(state.color), red = new THREE.Color("#c8372d"), amb = new THREE.Color("#e0a030"), grn = new THREE.Color("#4f9d6b"), tmp = new THREE.Color();
      for (var i = 0; i < n; i++) {
        if (state.heat) {
          var t = Math.min(1, Math.max(0, e[i] / 12));
          if (t < 0.5) tmp.copy(red).lerp(amb, t * 2); else tmp.copy(amb).lerp(grn, (t - 0.5) * 2);
        } else tmp.copy(base);
        col[i * 3] = tmp.r; col[i * 3 + 1] = tmp.g; col[i * 3 + 2] = tmp.b;
      }
      g.setAttribute("color", new THREE.BufferAttribute(col, 3));
    }

    function disposeModel() {
      if (!model) return;
      scene.remove(model);
      model.traverse(function (o) {
        if (!o.isMesh) return;
        o.geometry.dispose();
        (Array.isArray(o.material) ? o.material : [o.material]).forEach(function (m) {
          for (var k in m) if (m[k] && m[k].isTexture) m[k].dispose();
          m.dispose();
        });
      });
      model = null; modelTint = null;
    }

    // 어깨 → 손목(신체)/소매끝(의류) 방향을 fit_anchor 좌표로 구한다 (3D팀 web.js sleeveDirections 와 같은 규칙).
    function sleeveDirections(sceneRoot, end) {
      var anchor = sceneRoot.getObjectByName("fit_anchor"), out = {};
      ["L", "R"].forEach(function (side) {
        var local = function (tag) {
          var node = sceneRoot.getObjectByName("fit_" + tag + "_" + side);
          if (!anchor || !node) throw new Error("FitStage: 기준점이 없어요 · fit_" + tag + "_" + side);
          return anchor.worldToLocal(node.getWorldPosition(new THREE.Vector3()));
        };
        out[side] = local(end).sub(local("shoulder"));
      });
      return out;
    }

    // 팔과 소매의 A 자세 각도가 허용 오차 안에서 같은지 본다 (3D팀 pose.js compareSleeves 와 같은 규칙).
    // 어긋나면 입히지 않는다. 호출한 쪽(fit-room.js)이 실측표 근사 옷으로 대신 보여 준다.
    function sleevesMatch(bodyRoot, garmentRoot) {
      var pose = bodyRoot.userData && bodyRoot.userData.fitme_pose;
      var want = pose && isFinite(pose.arm_angle_deg) ? pose.arm_angle_deg : 45;
      var tol = pose && isFinite(pose.sleeve_tolerance_deg) ? pose.sleeve_tolerance_deg : 1;
      var b = sleeveDirections(bodyRoot, "wrist"), g = sleeveDirections(garmentRoot, "cuff");
      return ["L", "R"].every(function (side) {
        var bv = b[side].clone(), gv = g[side].clone();
        if (!(bv.length() > 1e-7) || !(gv.length() > 1e-7)) return false;
        bv.normalize(); gv.normalize();
        var sign = side === "L" ? 1 : -1;
        var angle = function (d) { return Math.atan2(sign * d.x, -d.y) * 180 / Math.PI; };
        var diff = Math.acos(Math.min(1, Math.max(-1, bv.dot(gv)))) * 180 / Math.PI;
        return Math.abs(angle(bv) - want) <= tol && Math.abs(angle(gv) - want) <= tol && diff <= tol;
      });
    }

    function setGarmentModel(glb, lowerBody) {
      return new Promise(function (resolve, reject) {
        if (dead || !bodyScene) { reject(new Error("FitStage: 신체 모델이 아직 준비되지 않았어요")); return; }
        new THREE.GLTFLoader().parse(glb, "", function (gltf) {
          if (dead) { resolve(); return; }
          var name = lowerBody ? "fit_anchor_waist" : "fit_anchor";
          var target = bodyScene.getObjectByName(name);
          var source = gltf.scene.getObjectByName(name) || (lowerBody ? gltf.scene.getObjectByName("fit_anchor") : null);
          if (!target || !source) { reject(new Error("FitStage: 기준점이 없어요 · " + name)); return; }
          bodyScene.updateMatrixWorld(true);
          gltf.scene.updateMatrixWorld(true);
          // 의류 서버가 이 신체 위에서 직접 시뮬레이션한 옷은 이미 그 몸의 팔 자세에 맞춰져 있어
          // 45° A 자세 검사를 하지 않는다 (SAM 직접 신체는 사진 속 실제 팔 각도라 45°±1°에서 벗어날 수 있음).
          var fitting = gltf.scene.userData && gltf.scene.userData.fitme_garment;
          var simulated = !!fitting && ["db_cloth_collision", "sam_body_cloth_collision"].includes(fitting.fitting_mode);
          if (!lowerBody && !simulated) {
            var matched;
            try { matched = sleevesMatch(bodyScene, gltf.scene); } catch (e) { reject(e); return; }
            if (!matched) { reject(new Error("FitStage: 팔과 소매의 A 자세 각도가 달라요")); return; }
          }
          // 신체 기준점 × (의류 기준점)⁻¹ : 의류의 기준점을 신체의 기준점 자리에 그대로 옮긴다.
          var holder = new THREE.Group();
          holder.matrixAutoUpdate = false;
          holder.matrix.copy(target.matrixWorld).multiply(new THREE.Matrix4().copy(source.matrixWorld).invert());
          holder.add(gltf.scene);
          disposeModel();
          if (garment) { scene.remove(garment); garment.geometry.dispose(); garment.material.dispose(); garment = null; }
          model = holder;
          model.visible = state.visible;
          scene.add(model);
          resolve();
        }, function (err) { reject(err || new Error("FitStage: 의류 GLB 를 읽지 못했어요")); });
      });
    }

    function tintModel(hex) {
      if (!model) return;
      model.traverse(function (o) {
        if (!o.isMesh) return;
        if (!modelTint) o.material = Array.isArray(o.material) ? o.material.map(function (m) { return m.clone(); }) : o.material.clone();
        (Array.isArray(o.material) ? o.material : [o.material]).forEach(function (m) { if (m.color) m.color.set(hex); });
      });
      modelTint = hex;
    }

    function resetView() { if (!home) return; cam.position.copy(home.pos); controls.target.copy(home.tgt); controls.update(); }

    (function loop() { if (dead) return; raf = requestAnimationFrame(loop); controls.update(); renderer.render(scene, cam); })();

    return {
      setGarment: function (spec) { state.garmentSpec = spec; dress(); },
      setGarmentModel: setGarmentModel,
      clearGarmentModel: function () { disposeModel(); dress(); },
      hasGarmentModel: function () { return !!model; },
      setColor: function (hex) { state.color = hex; if (model) tintModel(hex); else paint(); },
      setHeatmap: function (on) { state.heat = !!on; paint(); },
      setGarmentVisible: function (on) { state.visible = !!on; if (garment) garment.visible = state.visible; if (model) model.visible = state.visible; },
      setAutoRotate: function (on) { controls.autoRotate = !!on; },
      resetView: resetView,
      getFit: function () { return state.garmentSpec && src ? fitResult() : null; },
      destroy: function () {
        dead = true; cancelAnimationFrame(raf);
        if (ro) ro.disconnect(); else root.removeEventListener("resize", resize);
        controls.dispose(); renderer.dispose();
        if (garment) { garment.geometry.dispose(); garment.material.dispose(); }
        disposeModel();
        if (src) src.dispose();
        if (canvas.parentNode) canvas.parentNode.removeChild(canvas);
        if (overlay && overlay.parentNode) overlay.parentNode.removeChild(overlay);
      }
    };
  }
  root.FitStage = { mount: mount, fitLabel: fitLabel };
})(typeof window !== "undefined" ? window : this);
