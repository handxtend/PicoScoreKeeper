import { api, API_BASE, setApiBase } from './api.js';

const sel = (q)=> document.querySelector(q);
const out = (el, v)=> (el.textContent = typeof v==='string'? v : JSON.stringify(v,null,2));

let deferPrompt=null;
window.addEventListener('beforeinstallprompt', (e)=>{
  e.preventDefault(); deferPrompt=e; sel('#btn-install').hidden=false;
});
sel('#btn-install').addEventListener('click', async ()=>{
  if(!deferPrompt) return;
  deferPrompt.prompt(); await deferPrompt.userChoice; deferPrompt=null;
  sel('#btn-install').hidden=true;
});

sel('#apiBase').value = API_BASE;
sel('#saveApi').onclick = async ()=> {
  setApiBase(sel('#apiBase').value.trim());
  try{ const h = await api.health(); out(sel('#health'), '✓ ' + JSON.stringify(h)); }catch(e){ out(sel('#health'), '✗ ' + e.message); }
};
sel('#saveApi').click();

sel('#btnCreateUser').onclick = async ()=>{
  const u = { firstName: sel('#uFirst').value, lastName: sel('#uLast').value, email: sel('#uEmail').value, duprId: sel('#uDUPR').value||undefined };
  const r = await api.createUser(u);
  const all = await api.listUsers();
  out(sel('#usersOut'), all);
};

let eventId = localStorage.getItem('psk_event');
let divisionId = localStorage.getItem('psk_div');
function saveIds(){ localStorage.setItem('psk_event', eventId||''); localStorage.setItem('psk_div', divisionId||''); }
function showDiv(){ out(sel('#divOut'), { eventId, divisionId }); }

sel('#btnEvent').onclick = async ()=>{
  const e = { name: sel('#eName').value||'My Event', venue: sel('#eVenue').value||'' };
  const r = await api.createEvent(e);
  eventId = r.id; saveIds(); showDiv();
};

sel('#btnDivision').onclick = async ()=>{
  if(!eventId){ alert('Create event first'); return; }
  const d = { eventId, name: sel('#dName').value||'Division 1', type: sel('#dType').value, fixedPartner: sel('#dType').value==='doubles' };
  const r = await api.createDivision(d);
  divisionId = r.id; saveIds(); showDiv();
};

sel('#btnRegister').onclick = async ()=>{
  if(!divisionId) return alert('Create division first');
  const r = await api.register(divisionId, { userId: sel('#regUserId').value, partnerUserId: sel('#regPartnerId').value||undefined });
  out(sel('#divOut'), r);
};

sel('#btnSchedule').onclick = async ()=>{
  if(!divisionId) return alert('Create division first');
  const r = await api.schedule(divisionId);
  const m = await api.matches(divisionId);
  out(sel('#matchOut'), m);
};

sel('#btnSubmit').onclick = async ()=>{
  const payload = { byTeam: sel('#byTeam').value, side: sel('#side').value, scores:[{a:+sel('#g1a').value||0, b:+sel('#g1b').value||0}] };
  const sub = await api.submit(sel('#mId').value, payload);
  sel('#subId').value = sub.id;
  out(sel('#matchOut'), sub);
};

sel('#btnConfirm').onclick = async ()=>{
  const m = await api.confirm(sel('#mId').value, { submissionId: sel('#subId').value });
  out(sel('#matchOut'), m);
};

sel('#btnStandings').onclick = async ()=>{
  const s = await api.standings(divisionId);
  out(sel('#standOut'), s);
};

if('serviceWorker' in navigator){
  navigator.serviceWorker.register('/sw.js');
}
