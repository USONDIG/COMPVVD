'use strict';
let dirty=false,busy=false,printing=false;
let offset=Number(document.body.dataset.serverTime)*1000-Date.now();
function showError(message,conflict=false){
  const el=document.getElementById('notice');el.textContent=message;el.className='show';
  if(conflict){const b=document.createElement('button');b.textContent='Actualiser sans perdre les champs';b.className='secondary small';b.addEventListener('click',refreshPreservingInputs);el.appendChild(b);}
  clearTimeout(showError.timer);showError.timer=setTimeout(()=>el.className='',15000);
}
document.addEventListener('input',e=>{if(!e.target.closest('[data-spectator-filters]'))dirty=true;});
document.addEventListener('change',e=>{if(!e.target.closest('[data-spectator-filters]'))dirty=true;});
function refreshPreservingInputs(){
  const drafts=[...document.querySelectorAll('form.ajax')].map(form=>({
    action:form.getAttribute('action')||location.pathname,kind:form.elements.action?.value||'',
    table:form.elements.table?.value||'',match:form.elements.match?.value||'',
    person:form.elements.person?.value||'',
    fields:[...form.elements].filter(e=>e.name&&e.type!=='file'&&!['csrf','revision','password','current'].includes(e.name)).map(e=>({name:e.name,value:e.value,checked:e.checked,type:e.type}))
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
  const gated=form.querySelector('[data-score-clock]');if(gated&&gated.disabled){showError('Le round n’est pas terminé.');return;}
  if(form.dataset.confirm&&!confirm(form.dataset.confirm))return;
  const data=new FormData(form),buttons=[...form.querySelectorAll('button')];busy=true;buttons.forEach(b=>b.disabled=true);
  try{const res=await fetch(form.getAttribute('action')||location.href,{method:'POST',body:data,credentials:'same-origin',headers:{'X-Requested-With':'fetch'}});const result=await res.json();if(!res.ok){showError(result.error||'Action impossible.',res.status===409);return;}dirty=false;location.assign(result.redirect||location.pathname);}
  catch(e){showError('Connexion interrompue. Vos champs sont conservés. Réessayez après le retour du réseau.');}
  finally{busy=false;buttons.forEach(b=>b.disabled=false);tick();}
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
  for(const el of document.querySelectorAll('[data-clock]')){const t=JSON.parse(el.dataset.clock);if(!t){el.textContent='Prêt';continue;}const elapsed=t.elapsed+(t.running?Math.max(0,now-t.since):0);el.textContent=fmt(t.duration===null?elapsed:Math.ceil(Math.max(0,t.duration-elapsed)));const ended=el.hasAttribute('data-round-clock')&&t.duration!==null&&elapsed>=t.duration;el.classList.toggle('clock-ended',ended);const message=el.parentElement.querySelector('[data-round-ended]');if(message)message.hidden=!ended;}
  for(const button of document.querySelectorAll('[data-score-clock]')){const t=JSON.parse(button.dataset.scoreClock),elapsed=t.elapsed+(t.running?Math.max(0,now-t.since):0),ready=t.duration!==null&&elapsed>=t.duration;button.disabled=busy||!ready;const note=button.parentElement.querySelector('[data-score-wait]');if(note){const text=ready?'Round terminé : vous pouvez valider les scores.':'Validation disponible à la fin du round.';if(note.textContent!==text)note.textContent=text;}}
  for(const el of document.querySelectorAll('[data-duration]'))el.textContent=fmt((Number(el.dataset.closed)||now)-Number(el.dataset.duration));
}
for(const el of document.querySelectorAll('[data-date]'))el.textContent=new Date(Number(el.dataset.date)*1000).toLocaleString('fr-FR');
const filter=document.getElementById('area-filter'),tableFilter=document.getElementById('table-filter');
const filterRoot=document.querySelector('[data-spectator-filters]'),filterKey='spectator:'+(filterRoot?.dataset.spectatorFilters||'');
function filterAreas(){
 if(!filter||!tableFilter)return;
 for(const option of tableFilter.options){const hide=!!option.value&&!!filter.value&&option.dataset.area!==filter.value;option.hidden=hide;option.disabled=hide;}
 if(tableFilter.selectedOptions[0]?.disabled)tableFilter.value='';
 for(const el of document.querySelectorAll('[data-table]'))el.hidden=(!!filter.value&&el.dataset.area!==filter.value)||(!!tableFilter.value&&el.dataset.table!==tableFilter.value);
 const empty=document.getElementById('no-live-match');if(empty)empty.hidden=[...document.querySelectorAll('.live-board')].some(el=>!el.hidden);
 sessionStorage.setItem(filterKey,JSON.stringify({area:filter.value,table:tableFilter.value}));
}
if(filter&&tableFilter){
 try{const saved=JSON.parse(sessionStorage.getItem(filterKey)||'{}');filter.value=saved.area||'';tableFilter.value=saved.table||'';}catch(e){}
 filterAreas();for(const control of [filter,tableFilter])control.addEventListener('change',()=>{filterAreas();renderTrees();});
 if(sessionStorage.getItem('screen')==='1')document.body.classList.add('screen');
}
tick();setInterval(tick,200);
async function refreshPublic(){
 const current=document.querySelector('[data-public-live]');if(!current)return;
 try{
  const r=await fetch('/public',{cache:'no-store',credentials:'same-origin'});if(!r.ok)throw new Error('http');
  const doc=new DOMParser().parseFromString(await r.text(),'text/html');
  if(!doc.querySelector('[data-public-live]')){location.assign('/public');return;}
  if(printing)return;
  const scrolls=new Map([...current.querySelectorAll('[data-tree]')].map(el=>[el.dataset.tree,{x:el.parentElement.scrollLeft,y:el.parentElement.scrollTop}]));
  const details=new Map([...current.querySelectorAll('details[id]')].map(el=>[el.id,el.open]));
  const position=window.scrollY;
  for(const id of ['live-matches','public-trees']){
   const old=document.getElementById(id),fresh=doc.getElementById(id);if(old&&fresh)old.replaceChildren(...fresh.childNodes);
  }
  // Refresh options without replacing the focused selectors or resetting choices.
  for(const select of [filter,tableFilter])if(select){const value=select.value;select.replaceChildren(...doc.getElementById(select.id).childNodes);select.value=value;}
  offset=Number(doc.body.dataset.serverTime)*1000-Date.now();
  filterAreas();renderTrees();tick();
  for(const el of current.querySelectorAll('[data-tree]')){const saved=scrolls.get(el.dataset.tree);if(saved){el.parentElement.scrollLeft=saved.x;el.parentElement.scrollTop=saved.y;}}
  for(const [id,open] of details){const el=document.getElementById(id);if(el)el.open=open;}
  window.scrollTo(0,position);
  document.getElementById('connection').textContent='À jour à '+new Date().toLocaleTimeString('fr-FR')+' · actualisation toutes les 5 secondes';
 }catch(e){const el=document.getElementById('connection');if(el)el.textContent='Connexion interrompue · dernier état conservé. Nouvelle tentative automatique.';}
}
let refreshing=false;
setInterval(async()=>{
 if(!document.querySelector('[data-live]')||busy||printing||document.hidden||refreshing)return;
 if(document.querySelector('[data-public-live]')){refreshing=true;try{await refreshPublic();}finally{refreshing=false;}return;}
 if(dirty||['INPUT','SELECT','TEXTAREA'].includes(document.activeElement.tagName))return;
 try{const r=await fetch('/health',{cache:'no-store'});if(r.ok)location.reload();else showError('Connexion indisponible. Résultats non actualisés.');}catch(e){showError('Connexion interrompue. Affichage du dernier état reçu.');}
},5000);
let printDetails=[];
window.addEventListener('beforeprint',()=>{printing=true;printDetails=[...document.querySelectorAll('details')].map(el=>[el,el.open]);for(const [el] of printDetails)el.open=true;});
window.addEventListener('afterprint',()=>{printing=false;for(const [el,open] of printDetails)el.open=open;});


function renderTrees(){
 for(const canvas of document.querySelectorAll('[data-tree]')){
  const scroll=canvas.parentElement,key='tree-scroll:'+location.pathname+':'+canvas.dataset.tree;
  if(!scroll.dataset.bound){
   scroll.scrollLeft=Number(sessionStorage.getItem(key)||0);
   scroll.addEventListener('scroll',()=>sessionStorage.setItem(key,String(scroll.scrollLeft)),{passive:true});scroll.dataset.bound='1';
  }
 }
}
renderTrees();
