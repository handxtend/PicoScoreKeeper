export let API_BASE = localStorage.getItem('psk_api_base') || 'http://localhost:8787';

export function setApiBase(v){
  API_BASE = v;
  localStorage.setItem('psk_api_base', v);
}

async function j(method, path, body){
  const res = await fetch(API_BASE + path, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined
  });
  if(!res.ok){
    const t = await res.text();
    throw new Error(t || res.statusText);
  }
  return await res.json();
}

export const api = {
  health: ()=> j('GET', '/health'),
  createUser: (u)=> j('POST','/users', u),
  listUsers: ()=> j('GET','/users'),
  createEvent: (e)=> j('POST','/events', e),
  createDivision: (d)=> j('POST','/divisions', d),
  register: (id, r)=> j('POST', `/divisions/${id}/register`, r),
  schedule: (id)=> j('POST', `/divisions/${id}/schedule`),
  matches: (id)=> j('GET', `/divisions/${id}/matches`),
  submit: (mId, payload)=> j('POST', `/matches/${mId}/submit`, payload),
  confirm: (mId, payload)=> j('POST', `/matches/${mId}/confirm`, payload),
  standings: (id)=> j('GET', `/divisions/${id}/standings`),
};
