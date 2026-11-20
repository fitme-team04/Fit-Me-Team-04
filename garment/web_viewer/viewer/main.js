// 역할: Three.js 장면·카메라·GLB 로더와 피팅 뷰어를 구성합니다.
import * as THREE from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {createFitMeViewer, fitGarment} from '../src/web.js';

const $ = id => document.getElementById(id);
const cfg = import.meta.env;
const form = $('inputs');
const scene = new THREE.Scene();
const canvas = $('view');
const renderer = new THREE.WebGLRenderer({canvas, antialias:true});
scene.background = new THREE.Color(0xedf3ef);
const camera = new THREE.PerspectiveCamera(36,1,.01,30);
camera.position.set(0,1,3.3);
const controls = new OrbitControls(camera,canvas);
controls.target.set(0,.9,0);
controls.update();
scene.add(new THREE.HemisphereLight(0xffffff,0x71827d,2.4));
const light = new THREE.DirectionalLight(0xffffff,2);
light.position.set(2,4,2);
scene.add(light);
new ResizeObserver(() => {
  renderer.setSize(canvas.clientWidth,canvas.clientHeight,false);
  camera.aspect=canvas.clientWidth/canvas.clientHeight;
  camera.updateProjectionMatrix();
}).observe(canvas);
renderer.setAnimationLoop(()=>renderer.render(scene,camera));

const viewer=createFitMeViewer(new GLTFLoader(),{
  onReady(kind,receipt){
    $(kind).textContent=(kind==='avatars'?'신체':'의류')+' · '+receipt.status+' · '+receipt.model_id;
  }
});
function dispose(root){
  root?.traverse(node=>{node.geometry?.dispose();for(const m of [].concat(node.material||[]))m.dispose()});
  root?.removeFromParent();
}
let current;
form.onsubmit=async event=>{
  event.preventDefault(); const fields=form.elements;
  form.querySelector('button').disabled=true;
  $('avatars').textContent='';$('garments').textContent='';$('status').textContent='생성 중…';
  const params={height_cm:Number(fields.height.value),weight_kg:Number(fields.weight.value),photo:fields.photo.files[0]};
  const product=Number(fields.product.value),size=Number(fields.namedItem('size').value);
  let body,shirt,pants;
  try{
    const lowerProduct=Number(fields.lower_product.value),lowerSize=Number(fields.lower_size.value);
    if (Boolean(lowerProduct)!==Boolean(lowerSize)) throw Error('추가 하의의 상품 ID와 사이즈 ID를 모두 입력하세요.');
    const tasks=[
      viewer.loadFitMeAvatar(params,cfg.VITE_AVATAR_API||'/api/avatars'),
      viewer.loadFitMeGarment(product,size,cfg.VITE_GARMENT_API||'/api/garments')];
    const results=await Promise.allSettled(tasks);
    [body,shirt]=results.map(r=>r.status==='fulfilled'?r.value.scene:null);
    for(const r of results)if(r.status==='rejected')throw r.reason;
    if (lowerProduct) {
      if (shirt.userData.fitme_garment?.kind === 'slacks') throw Error('추가 하의를 사용할 때 첫 상품은 상의여야 합니다.');
      pants=(await viewer.loadFitMeGarment(lowerProduct,lowerSize,cfg.VITE_GARMENT_API||'/api/garments')).scene;
    }
    fitGarment(body,shirt);
    if (pants) {
      if (pants.userData.fitme_garment?.kind !== 'slacks') throw Error('추가 하의에는 슬랙스 상품을 선택하세요.');
      fitGarment(body,pants);
    }
    dispose(current);scene.add(body);current=body;body=shirt=pants=null;
    $('status').textContent='착장 완료';
  }catch(e){dispose(pants);dispose(shirt);dispose(body);$('status').textContent=e.message}
  finally{form.querySelector('button').disabled=false}
};
