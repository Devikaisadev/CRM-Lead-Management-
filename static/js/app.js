const modal = () => bootstrap.Modal.getOrCreateInstance(document.getElementById("leadModal"));
const fields = ["full_name","email","phone","company_name","lead_source","lead_status"];

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, ch => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[ch]));
}
async function api(url, options={}) {
  const response = await fetch(url, {headers: {"Content-Type":"application/json"}, ...options});
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = data.fields ? Object.values(data.fields).join(" ") : (data.error || "Something went wrong.");
    throw new Error(detail);
  }
  return data;
}
async function loadStats() {
  try {
    const s = await api("/api/dashboard/stats");
    document.getElementById("totalCount").textContent=s.total;
    document.getElementById("newCount").textContent=s.new_leads;
    document.getElementById("contactedCount").textContent=s.contacted_leads;
    document.getElementById("convertedCount").textContent=s.converted_leads;
  } catch(e) { console.error(e); }
}
async function loadLeads() {
  const body=document.getElementById("leadsBody");
  const search=document.getElementById("searchInput").value;
  const status=document.getElementById("statusFilter").value;
  const params=new URLSearchParams(); if(search) params.set("search",search); if(status) params.set("status",status);
  try {
    const leads=await api("/api/leads?"+params.toString());
    if(!leads.length) body.innerHTML='<tr><td colspan="6" class="text-center py-5 muted">No leads found. Add your first lead to get started.</td></tr>';
    else body.innerHTML=leads.map(l=>`<tr>
      <td><div class="contact-name">${escapeHtml(l.full_name)}</div><div class="contact-email">${escapeHtml(l.email)} · ${escapeHtml(l.phone)}</div></td>
      <td><span class="company-name">${escapeHtml(l.company_name)}</span></td>
      <td>${escapeHtml(l.lead_source)}</td>
      <td><span class="status-pill status-${escapeHtml(l.lead_status)}">${escapeHtml(l.lead_status)}</span></td>
      <td>${escapeHtml((l.created_at||"").slice(0,10))}</td>
      <td class="text-end text-nowrap"><button class="action-btn" title="Edit" onclick="editLead(${l.id})">✎</button><button class="action-btn" title="Delete" onclick="deleteLead(${l.id})">⌫</button></td>
    </tr>`).join("");
    document.getElementById("resultCount").textContent=`Showing ${leads.length} lead${leads.length===1?"":"s"}`;
  } catch(e) { body.innerHTML=`<tr><td colspan="6" class="text-center text-danger py-4">${escapeHtml(e.message)}</td></tr>`; }
}
function prepareAdd() {
  document.getElementById("leadForm").reset();
  document.getElementById("leadId").value="";
  document.getElementById("modalTitle").textContent="Add a new lead";
  document.getElementById("saveButton").textContent="Save lead";
  document.getElementById("formError").classList.add("d-none");
}
async function editLead(id) {
  try {
    const lead=await api(`/api/leads/${id}`);
    document.getElementById("leadId").value=id;
    fields.forEach(f=>document.getElementById(f).value=lead[f]);
    document.getElementById("modalTitle").textContent="Edit lead";
    document.getElementById("saveButton").textContent="Save changes";
    document.getElementById("formError").classList.add("d-none");
    modal().show();
  } catch(e) { alert(e.message); }
}
async function deleteLead(id) {
  if(!confirm("Delete this lead? This action cannot be undone.")) return;
  try { await api(`/api/leads/${id}`,{method:"DELETE"}); await refresh(); }
  catch(e) { alert(e.message); }
}
async function refresh(){await Promise.all([loadStats(),loadLeads()]);}
document.getElementById("leadForm").addEventListener("submit",async event=>{
  event.preventDefault();
  const id=document.getElementById("leadId").value;
  const payload={}; fields.forEach(f=>payload[f]=document.getElementById(f).value.trim());
  try {
    await api(id?`/api/leads/${id}`:"/api/leads",{method:id?"PUT":"POST",body:JSON.stringify(payload)});
    modal().hide(); prepareAdd(); await refresh();
  } catch(e) {
    const box=document.getElementById("formError"); box.textContent=e.message; box.classList.remove("d-none");
  }
});
let searchTimer;
document.getElementById("searchInput").addEventListener("input",()=>{clearTimeout(searchTimer);searchTimer=setTimeout(loadLeads,250);});
refresh();
