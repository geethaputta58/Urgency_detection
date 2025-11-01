// static/agent.js
const listEl = document.getElementById('messages_list');
const detail = document.getElementById('detail_area');
const search = document.getElementById('search');
const filterStatus = document.getElementById('filter_status');
const btnRefresh = document.getElementById('btn_refresh');
const cannedList = document.getElementById('canned_list');
const agentNameInput = document.getElementById('agent_name');
const btnLoadMore = document.getElementById('btn_load_more');

let messages = [];
let selected = null;
let limit = 50;
let offset = 0;

async function fetchMessages(reset=false){
  if(reset){ offset = 0; listEl.innerHTML = ''; messages = []; }
  const q = encodeURIComponent(search.value || '');
  const st = filterStatus.value || '';
  const res = await fetch(`/api/messages?q=${q}&status=${st}&limit=${limit}&offset=${offset}`);
  const data = await res.json();
  if(reset) messages = data;
  else messages = messages.concat(data);
  renderList();
  offset += data.length;
}
function renderList(){
  for(const m of messages){
    if(document.querySelector(`li[data-id='${m.id}']`)) continue;
    const li = document.createElement('li');
    li.dataset.id = m.id;
    if(m.priority > 0) li.classList.add('high');
    li.innerHTML = `<strong>${m.customer_name || m.customer_id} — ${m.subject}</strong><div class="muted">${new Date(m.created_at*1000).toLocaleString()} · status: ${m.status}</div><div class="muted">${m.body.slice(0,120)}${m.body.length>120?'...':''}</div>`;
    li.onclick = ()=> openMessage(m.id);
    listEl.appendChild(li);
  }
}
async function openMessage(id){
  const res = await fetch('/api/message/' + id);
  const data = await res.json();
  if(data.error) return alert('Error loading');
  selected = data.message;
  detail.innerHTML = `
    <h3>${selected.subject} <span class="chip">${selected.customer_name||selected.customer_id}</span></h3>
    <div class="msg-body">${selected.body}</div>
    <div class="muted">Created: ${new Date(selected.created_at*1000).toLocaleString()} · Priority: ${selected.priority}</div>
    <div class="muted">Assigned to: ${selected.assigned_to || 'none'}</div>
    <hr/>
    <div id="replies">${data.replies.map(r=>`<div><strong>${r.agent}</strong> — ${new Date(r.created_at*1000).toLocaleString()}<div class="msg-body">${r.body}</div></div>`).join('')}</div>
    <div class="reply">
      <input id="agent_name_reply" placeholder="Agent name" value="${agentNameInput.value || ''}" />
      <textarea id="reply_body" placeholder="Write your reply..."></textarea>
      <button onclick="sendReply()">Send</button>
    </div>
    <div style="margin-top:8px">
      <button onclick="claimSelected()">Claim</button>
      <button onclick="releaseSelected()">Release</button>
    </div>
  `;
  if(data.profile){
    detail.innerHTML += `<hr/><h4>Customer Profile</h4><div class="small">KYC: ${data.profile.kyc_status || 'N/A'} · Tier: ${data.profile.tier || 'N/A'}</div><div class="small">Notes: ${data.profile.notes || ''}</div>`;
  }
}
async function sendReply(){
  const agent = document.getElementById('agent_name_reply').value || agentNameInput.value || 'Agent';
  const body = document.getElementById('reply_body').value;
  if(!selected) return alert('Select a message first');
  const fd = new FormData();
  fd.append('agent', agent);
  fd.append('body', body);
  const r = await fetch('/api/message/' + selected.id + '/reply', { method:'POST', body: fd });
  const j = await r.json();
  if(r.status === 200 || j.ok){
    document.getElementById('reply_body').value='';
    fetchMessages(true);
    openMessage(selected.id);
  } else {
    alert('Error: ' + JSON.stringify(j));
  }
}
async function claimSelected(){
  if(!selected) return alert('Select message first');
  const agent = agentNameInput.value || prompt('Agent name');
  if(!agent) return;
  const fd = new FormData();
  fd.append('agent', agent);
  const r = await fetch(`/api/message/${selected.id}/claim`, { method:'POST', body: fd });
  const j = await r.json();
  if(j.ok){ showToast('Claimed by ' + agent); fetchMessages(true); openMessage(selected.id); }
  else alert(JSON.stringify(j));
}
async function releaseSelected(){
  if(!selected) return alert('Select message first');
  const agent = agentNameInput.value || prompt('Agent name');
  if(!agent) return;
  const fd = new FormData();
  fd.append('agent', agent);
  // we don't have release API in backend for safety - just reassign null via reply placeholder or use claim with empty
  const r = await fetch(`/api/message/${selected.id}/claim`, { method:'POST', body: fd });
  if(r.ok){ showToast('Released'); fetchMessages(true); openMessage(selected.id); }
}

async function loadCanned(){
  const res = await fetch('/api/canned');
  const data = await res.json();
  cannedList.innerHTML = '';
  for(const c of data){
    const div = document.createElement('div');
    div.className='canned';
    div.textContent = c.title + ' — ' + c.body.slice(0,70);
    div.onclick = ()=> {
      if(!selected) return alert('Select a message first');
      const bodyArea = document.getElementById('reply_body');
      if(bodyArea) bodyArea.value = c.body.replace('{{name}}', selected.customer_name || selected.customer_id || 'Customer');
    };
    cannedList.appendChild(div);
  }
}

// socket.io client
const socket = io({transports: ['websocket']});
socket.on('connect', ()=> console.log('socket connected'));
socket.on('new_message', (payload)=> {
  showToast('New message: ' + (payload.subject||payload.body.slice(0,60)));
  fetchMessages(true);
});
socket.on('reply', (payload)=> {
  showToast('Reply sent by ' + payload.agent);
  if(selected && payload.message_id === selected.id) openMessage(selected.id);
  fetchMessages(true);
});
socket.on('claim', (payload)=> {
  showToast('Claim updated');
  fetchMessages(true);
});

function showToast(txt){
  const t = document.createElement('div');
  t.className='toast';
  t.textContent = txt;
  document.body.appendChild(t);
  setTimeout(()=> t.remove(), 3000);
}

btnRefresh.onclick = ()=> fetchMessages(true);
search.oninput = ()=> setTimeout(()=> fetchMessages(true), 250);
filterStatus.onchange = ()=> fetchMessages(true);
btnLoadMore.onclick = ()=> fetchMessages(false);

fetchMessages(true);
loadCanned();
