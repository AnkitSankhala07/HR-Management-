/* Dayflow HRMS front-end helpers: API client, toast, modal, form builder, data table, charts */
const DF = (() => {
  const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const csrf = () => (document.cookie.match(/csrftoken=([^;]+)/) || [])[1] || "";
  const icons = () => window.lucide && lucide.createIcons();

  function toast(msg, type = "") {
    let box = document.querySelector(".toasts");
    if (!box) { box = document.createElement("div"); box.className = "toasts"; box.setAttribute("role", "status"); document.body.appendChild(box); }
    const t = document.createElement("div"); t.className = "toast " + type; t.textContent = msg; box.appendChild(t);
    setTimeout(() => t.remove(), 4200);
  }

  class ApiError extends Error { constructor(status, body) { super(body.message || "Request failed"); this.status = status; this.body = body; this.errors = body.errors || {}; } }

  async function api(url, { method = "GET", body, silent = false } = {}) {
    const opts = { method, headers: { "X-CSRFToken": csrf(), "X-Requested-With": "XMLHttpRequest" }, credentials: "same-origin" };
    if (body instanceof FormData) opts.body = body;
    else if (body !== undefined) { opts.headers["Content-Type"] = "application/json"; opts.body = JSON.stringify(body); }
    let res;
    try { res = await fetch(url, opts); } catch (e) { if (!silent) toast("Network error - please try again", "err"); throw e; }
    const ct = res.headers.get("content-type") || "";
    if (!ct.includes("json")) { if (res.ok) return res; throw new ApiError(res.status, { message: res.statusText }); }
    const data = await res.json();
    if (res.status === 401 && !location.pathname.startsWith("/login")) { location.href = "/login/?next=" + encodeURIComponent(location.pathname); throw new ApiError(401, data); }
    if (!res.ok || data.success === false) {
      if (!silent) toast(res.status === 403 ? "Unauthorized: " + (data.message || "forbidden") : (data.message || "Something went wrong"), "err");
      throw new ApiError(res.status, data);
    }
    return data;
  }

  const badgeColor = { APPROVED: "green", PRESENT: "green", VERIFIED: "green", COMPLETED: "green", PAID: "green", ACCEPTED: "green", HIRED: "green", OPEN: "green", WFH: "blue",
    PENDING: "amber", IN_PROGRESS: "amber", HALF_DAY: "amber", SENT: "blue", SCREENING: "blue", SHORTLISTED: "blue", INTERVIEW: "amber", OFFER: "green",
    REJECTED: "red", ABSENT: "red", EXPIRED: "red", OVERDUE: "red", ON_HOLD: "red", URGENT: "red", IMPORTANT: "amber", HIGH: "red", LEAVE: "blue", HOLIDAY: "blue" };
  const badge = v => v ? `<span class="badge b-${badgeColor[v] || ""}">${esc(String(v).replace(/_/g, " ").toLowerCase().replace(/^\w/, c => c.toUpperCase()))}</span>` : "";
  const date = v => v ? new Date(v.length === 10 ? v + "T00:00" : v).toLocaleDateString(undefined, { day: "2-digit", month: "short", year: "numeric" }) : "-";
  const dt = v => v ? new Date(v).toLocaleString(undefined, { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" }) : "-";
  const money = v => v == null ? "-" : "₹" + Number(v).toLocaleString("en-IN", { maximumFractionDigits: 2 });
  const bar = p => `<div class="progress" role="progressbar" aria-valuenow="${p}" aria-valuemin="0" aria-valuemax="100"><i style="width:${p}%"></i></div>`;
  const state = (icon, msg, spin) => `<div class="state">${spin ? '<div class="spinner"></div>' : `<i data-lucide="${icon}"></i>`}<div>${msg}</div></div>`;

  function modal(title, bodyHtml) {
    const ov = document.createElement("div"); ov.className = "overlay";
    ov.innerHTML = `<div class="modal" role="dialog" aria-modal="true" aria-label="${esc(title)}"><div class="modal-head"><h2>${esc(title)}</h2><button class="icon-btn" aria-label="Close" data-x><i data-lucide="x"></i></button></div><div class="mbody">${bodyHtml}</div></div>`;
    const close = () => ov.remove();
    ov.addEventListener("click", e => { if (e.target === ov || e.target.closest("[data-x]")) close(); });
    document.addEventListener("keydown", function h(e) { if (e.key === "Escape") { close(); document.removeEventListener("keydown", h); } });
    document.body.appendChild(ov); icons();
    const first = ov.querySelector("input,select,textarea"); if (first) first.focus();
    return { el: ov.querySelector(".mbody"), close };
  }

  function confirmBox(msg, label = "Confirm", danger = true) {
    return new Promise(res => {
      const m = modal("Please confirm", `<p>${esc(msg)}</p><div class="row auto" style="justify-content:flex-end;margin-top:18px"><button class="btn secondary" data-no>Cancel</button><button class="btn ${danger ? "danger" : ""}" data-yes>${esc(label)}</button></div>`);
      m.el.querySelector("[data-no]").onclick = () => { m.close(); res(false); };
      m.el.querySelector("[data-yes]").onclick = () => { m.close(); res(true); };
    });
  }

  async function loadOptions(f) {
    if (f.options) return f.options;
    if (f.optionsUrl) {
      const d = await api(f.optionsUrl + (f.optionsUrl.includes("?") ? "&" : "?") + "page_size=100", { silent: true }).catch(() => ({}));
      const list = d.results || d.data || d || [];
      return (Array.isArray(list) ? list : []).map(o => [o.id, o[f.optionLabel || "name"] ?? o.title ?? o.full_name]);
    }
    return [];
  }

  function fieldHtml(f, opts, v) {
    const val = v ?? f.value ?? "", req = f.required ? "required" : "", id = "f_" + f.name;
    let input;
    if (f.type === "select" || f.type === "multiselect") {
      const sel = Array.isArray(val) ? val.map(String) : [String(val)];
      input = `<select id="${id}" name="${f.name}" ${req} ${f.type === "multiselect" ? "multiple size=4" : ""}>${f.type === "select" ? '<option value="">' + (f.placeholder || "Select...") + "</option>" : ""}${opts.map(([k, l]) => `<option value="${esc(k)}" ${sel.includes(String(k)) ? "selected" : ""}>${esc(l)}</option>`).join("")}</select>`;
    } else if (f.type === "textarea") input = `<textarea id="${id}" name="${f.name}" ${req} maxlength="${f.max || 1000}">${esc(val)}</textarea>`;
    else if (f.type === "checkbox") input = `<input type="checkbox" id="${id}" name="${f.name}" ${val ? "checked" : ""}>`;
    else if (f.type === "file") input = `<input type="file" id="${id}" name="${f.name}" accept="${f.accept || ""}" ${req}>`;
    else input = `<input id="${id}" type="${f.type || "text"}" name="${f.name}" value="${esc(val)}" ${req} ${f.min != null ? `min="${f.min}"` : ""} ${f.max != null && f.type === "number" ? `max="${f.max}"` : ""} ${f.step ? `step="${f.step}"` : ""} autocomplete="${f.autocomplete || "off"}">`;
    return `<div class="field"><label for="${id}">${esc(f.label)}${f.required ? " *" : ""}</label>${input}<div class="err" data-err="${f.name}" role="alert"></div></div>`;
  }

  async function form({ title, fields, initial = {}, submit = "Save", onSubmit }) {
    const optSets = await Promise.all(fields.map(loadOptions));
    const m = modal(title, `<form novalidate>${fields.map((f, i) => fieldHtml(f, optSets[i], initial[f.name])).join("")}<div class="row auto" style="justify-content:flex-end"><button type="button" class="btn secondary" data-x>Cancel</button><button class="btn" type="submit">${esc(submit)}</button></div></form>`);
    const fm = m.el.querySelector("form");
    fm.addEventListener("submit", async e => {
      e.preventDefault();
      fm.querySelectorAll("[data-err]").forEach(x => x.textContent = "");
      const btn = fm.querySelector("[type=submit]"); btn.disabled = true;
      let body;
      if (fields.some(f => f.type === "file")) {
        body = new FormData();
        fields.forEach(f => {
          const el = fm.elements[f.name];
          if (f.type === "file") { if (el.files[0]) body.append(f.name, el.files[0]); }
          else if (f.type === "multiselect") [...el.selectedOptions].forEach(o => body.append(f.name, o.value));
          else if (f.type === "checkbox") { if (el.checked) body.append(f.name, "true"); }
          else if (el.value !== "") body.append(f.name, el.value);
        });
      } else {
        body = {};
        fields.forEach(f => {
          const el = fm.elements[f.name];
          if (f.type === "checkbox") body[f.name] = el.checked;
          else if (f.type === "multiselect") body[f.name] = [...el.selectedOptions].map(o => o.value);
          else if (el.value !== "") body[f.name] = el.value;
          else if (f.nullable) body[f.name] = null;
        });
      }
      try { await onSubmit(body); m.close(); }
      catch (err) {
        if (err.errors) Object.entries(err.errors).forEach(([k, v]) => { const t = fm.querySelector(`[data-err="${k}"]`); if (t) t.textContent = [].concat(v).join(" "); });
        btn.disabled = false;
      }
    });
    return m;
  }

  function table(el, cfg) {
    const st = { page: 1, search: "", ordering: cfg.ordering || "", filters: {} };
    el.innerHTML = `<div class="toolbar">${cfg.search === false ? "" : '<input type="search" placeholder="Search..." aria-label="Search" data-s>'}${(cfg.filters || []).map(f => `<select aria-label="${esc(f.label)}" data-f="${f.name}"><option value="">${esc(f.label)}: All</option>${(f.options || []).map(o => `<option value="${esc(o[0])}">${esc(o[1])}</option>`).join("")}</select>`).join("")}${cfg.toolbar || ""}</div><div class="table-wrap" data-body></div><div class="pager" data-pager></div>`;
    const body = el.querySelector("[data-body]"), pager = el.querySelector("[data-pager]");
    (cfg.filters || []).filter(f => f.optionsUrl).forEach(async f => { const o = await loadOptions(f); el.querySelector(`[data-f="${f.name}"]`).insertAdjacentHTML("beforeend", o.map(([k, l]) => `<option value="${esc(k)}">${esc(l)}</option>`).join("")); });
    async function load() {
      body.innerHTML = state("", "Loading...", true);
      const p = new URLSearchParams({ page: st.page, page_size: cfg.pageSize || 10, ...cfg.params });
      if (st.search) p.set("search", st.search);
      if (st.ordering) p.set("ordering", st.ordering);
      Object.entries(st.filters).forEach(([k, v]) => v && p.set(k, v));
      try {
        const d = await api(cfg.url + (cfg.url.includes("?") ? "&" : "?") + p, { silent: true });
        const rows = d.results || d.data || [];
        if (!rows.length) { body.innerHTML = state("inbox", cfg.empty || "Nothing here yet."); pager.innerHTML = ""; icons(); return; }
        body.innerHTML = `<table><thead><tr>${cfg.columns.map(c => `<th ${c.sort ? `class="sortable" data-sort="${c.sort}"` : ""}>${esc(c.label)}${st.ordering.replace("-", "") === c.sort ? (st.ordering[0] === "-" ? " ↓" : " ↑") : ""}</th>`).join("")}${cfg.actions ? "<th></th>" : ""}</tr></thead><tbody>${rows.map((r, i) => `<tr>${cfg.columns.map(c => `<td>${c.render ? c.render(r) : esc(r[c.key] ?? "-")}</td>`).join("")}${cfg.actions ? `<td class="right" data-row="${i}">${cfg.actions(r)}</td>` : ""}</tr>`).join("")}</tbody></table>`;
        body.querySelectorAll("th[data-sort]").forEach(th => th.onclick = () => { const k = th.dataset.sort; st.ordering = st.ordering === k ? "-" + k : k; load(); });
        body.querySelectorAll("[data-row]").forEach(td => { td._row = rows[td.dataset.row]; });
        pager.innerHTML = d.pages ? `<span>${d.count} total</span><span class="row auto"><button class="btn secondary sm" data-p="-1" ${st.page <= 1 ? "disabled" : ""}>Previous</button><span>Page ${d.page} / ${d.pages}</span><button class="btn secondary sm" data-p="1" ${st.page >= d.pages ? "disabled" : ""}>Next</button></span>` : "";
        pager.querySelectorAll("[data-p]").forEach(b => b.onclick = () => { st.page += +b.dataset.p; load(); });
        icons(); cfg.onLoaded && cfg.onLoaded(rows, body);
      } catch (e) { body.innerHTML = state("triangle-alert", e.status === 403 ? "Unauthorized - you do not have access to this data." : esc(e.message || "Could not load data.")); icons(); }
    }
    let t; const s = el.querySelector("[data-s]");
    if (s) s.oninput = () => { clearTimeout(t); t = setTimeout(() => { st.search = s.value; st.page = 1; load(); }, 300); };
    el.querySelectorAll("[data-f]").forEach(f => f.onchange = () => { st.filters[f.dataset.f] = f.value; st.page = 1; load(); });
    body.addEventListener("click", e => { const b = e.target.closest("[data-act]"); if (b && cfg.onAction) cfg.onAction(b.dataset.act, b.closest("[data-row]")._row, load); });
    load(); return { reload: load };
  }

  const charts = {};
  const PALETTE = ["#5A724A", "#BCE2A3", "#8aab74", "#222222", "#818181", "#d6e9c6", "#3f5233"];
  function chart(id, type, labels, datasets, opts = {}) {
    const c = document.getElementById(id); if (!c || !window.Chart) return;
    if (charts[id]) charts[id].destroy();
    const pie = ["doughnut", "pie"].includes(type);
    charts[id] = new Chart(c, { type, data: { labels, datasets: datasets.map((d, i) => ({ ...d, backgroundColor: d.backgroundColor || (pie ? PALETTE : PALETTE[i]), borderColor: d.borderColor || PALETTE[0], borderWidth: pie ? 0 : 2, borderRadius: type === "bar" ? 8 : 0, tension: .35 })) },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: pie || datasets.length > 1, position: "bottom" } }, scales: pie ? {} : { y: { beginAtZero: true, grid: { color: "#f0f0f0" } }, x: { grid: { display: false } } }, ...opts } });
  }

  let svc;
  async function fastapi(path, opts = {}) {
    if (!svc || svc.exp < Date.now()) { const d = await api("/api/auth/service-token/", { silent: true }); svc = { ...d.data, exp: Date.now() + (d.data.expires_in - 30) * 1000 }; }
    let res;
    try { res = await fetch(svc.fastapi_url + path, { ...opts, headers: { Authorization: "Bearer " + svc.token, "Content-Type": "application/json", ...(opts.headers || {}) } }); }
    catch (e) { throw new ApiError(0, { message: "Analytics/AI service is unreachable. Is FastAPI running?" }); }
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new ApiError(res.status, { message: data.detail || data.message || "Service error" });
    return data;
  }

  document.addEventListener("DOMContentLoaded", () => {
    icons();
    const sb = document.querySelector(".sidebar"), tg = document.querySelector(".menu-toggle");
    if (tg) tg.onclick = () => sb.classList.toggle("open");
    const lo = document.getElementById("logout");
    if (lo) lo.onclick = async e => { e.preventDefault(); await api("/api/auth/logout/", { method: "POST" }); location.href = "/login/"; };
  });
  return { esc, api, toast, modal, confirm: confirmBox, form, table, chart, fastapi, badge, date, dt, money, bar, state, icons, ApiError };
})();
