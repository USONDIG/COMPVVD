'use strict';
let dirty=false,busy=false;
const offset=Number(document.body.dataset.serverTime)*1000-Date.now();
function showError(message,conflict=false){
  const el=document.getElementById('notice');el.textContent=message;el.className='show';
  if(conflict){const b=document.createElement('button');b.textContent='Actualiser sans perdre les champs';b.className='secondary small';b.addEventListener('click',refreshPreservingInputs);el.appendChild(b);}
  clearTimeout(showError.timer);showError.timer=setTimeout(()=>el.className='',15000);
}
document.addEventListener('input',()=>dirty=true);
document.addEventListener('change',e=>{if(e.target.id!=='area-filter')dirty=true;});
function refreshPreservingInputs(){
  const drafts=[...document.querySelectorAll('form.ajax')].map(form=>({
    action:form.getAttribute('action')||location.pathname,kind:form.elements.action?.value||'',
    table:form.elements.table?.value||'',match:form.elements.match?.value||'',
    person:form.elements.person?.value||'',
    fields:[...form.elements].filter(e=>e.name&&!['csrf','revision','password','current'].includes(e.name)).map(e=>({name:e.name,value:e.value,checked:e.checked,type:e.type}))
  }));
  sessionStorage.setItem('draft:'+location.pathname,JSON.stringify(drafts));location.reload();
}
(function(){
  const key='draft:'+location.pathname,raw=sessionStorage.getItem(key);if(!raw)return;sessionStorage.removeItem(key);
  let drafts;try{drafts=JSON.parse(raw);}catch(e){return;}
  for(const form of document.querySelectorAll('form.ajax')){
    const draft=drafts.find(d=>d.action===(form.getAttribute('action')||location.pathname)&&d.kind===(form.elements.action?.value||'')&&d.table===(form.elements.table?.value||'')&&d.match===(form.elements.match?.value||'')&&d.person===(form.elements.person?.value||''));
    if(!draft)continue;const counts={};
    for(const saved of draft.fields){const controls=[...form.elements].filter(x=>x.name===saved.name);const i=counts[saved.name]||0;counts[saved.name]=i+1;const c=controls[i];if(!c)continue;if(c.type==='checkbox'||c.type==='radio')c.checked=saved.checked;else if(c.type!=='hidden')c.value=saved.value;}
  }
  dirty=true;showError('Données actualisées. Vos champs sont conservés : vérifiez le combat avant de valider.');
})();
document.addEventListener('submit',async e=>{
  const form=e.target;if(!form.matches('form.ajax'))return;e.preventDefault();if(busy||!form.reportValidity())return;
  if(form.dataset.confirm&&!confirm(form.dataset.confirm))return;
  const data=new FormData(form),buttons=[...form.querySelectorAll('button')];busy=true;buttons.forEach(b=>b.disabled=true);
  try{const res=await fetch(form.getAttribute('action')||location.href,{method:'POST',body:data,credentials:'same-origin',headers:{'X-Requested-With':'fetch'}});const result=await res.json();if(!res.ok){showError(result.error||'Action impossible.',res.status===409);return;}dirty=false;location.assign(result.redirect||location.pathname);}
  catch(e){showError('Connexion interrompue. Vos champs sont conservés. Réessayez après le retour du réseau.');}
  finally{busy=false;buttons.forEach(b=>b.disabled=false);}
});
document.addEventListener('click',e=>{
  const b=e.target.closest('[data-add]');if(b){const input=b.parentElement.querySelector('input');input.value=Math.min(999,Number(input.value||0)+Number(b.dataset.add));dirty=true;}
  if(e.target.closest('[data-print]'))window.print();
  if(e.target.closest('[data-screen]')){document.body.classList.toggle('screen');sessionStorage.setItem('screen',document.body.classList.contains('screen')?'1':'0');}
});
document.addEventListener('keydown',e=>{if(e.key==='Escape'){document.body.classList.remove('screen');sessionStorage.setItem('screen','0');}});
function fmt(value){const n=Math.max(0,Math.floor(value));return String(Math.floor(n/60)).padStart(2,'0')+':'+String(n%60).padStart(2,'0');}
function tick(){
  const now=(Date.now()+offset)/1000;
  for(const el of document.querySelectorAll('[data-clock]')){const t=JSON.parse(el.dataset.clock);if(!t){el.textContent='Prêt';continue;}const elapsed=t.elapsed+(t.running?Math.max(0,now-t.since):0);el.textContent=fmt(t.duration===null?elapsed:Math.ceil(Math.max(0,t.duration-elapsed)));}
  for(const el of document.querySelectorAll('[data-duration]'))el.textContent=fmt((Number(el.dataset.closed)||now)-Number(el.dataset.duration));
}
for(const el of document.querySelectorAll('[data-date]'))el.textContent=new Date(Number(el.dataset.date)*1000).toLocaleString('fr-FR');
const filter=document.getElementById('area-filter');
function filterAreas(){if(!filter)return;for(const el of document.querySelectorAll('[data-area]'))el.hidden=!!filter.value&&el.dataset.area!==filter.value;}
if(filter){filter.value=sessionStorage.getItem('area')||'';filterAreas();filter.addEventListener('change',()=>{sessionStorage.setItem('area',filter.value);filterAreas();});if(sessionStorage.getItem('screen')==='1')document.body.classList.add('screen');}
tick();setInterval(tick,200);
setInterval(async()=>{if(!document.querySelector('[data-live]')||dirty||busy||document.hidden||['INPUT','SELECT','TEXTAREA'].includes(document.activeElement.tagName))return;try{const r=await fetch('/health',{cache:'no-store'});if(r.ok)location.reload();else showError('Connexion indisponible. Résultats non actualisés.');}catch(e){showError('Connexion interrompue. Affichage du dernier état reçu.');}},5000);
