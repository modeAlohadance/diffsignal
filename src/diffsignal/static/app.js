const monitorsNode = document.querySelector('#monitors');
const errorNode = document.querySelector('#form-error');
const dialog = document.querySelector('#changes-dialog');

const escapeHtml = (value) => String(value).replace(/[&<>'"]/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]));

async function request(url, options = {}) {
  const response = await fetch(url, {headers:{'Content-Type':'application/json'}, ...options});
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${response.status})`);
  }
  return response.status === 204 ? null : response.json();
}

async function loadMonitors() {
  const monitors = await request('/api/monitors');
  if (!monitors.length) {
    monitorsNode.innerHTML = '<p class="muted">No monitors yet. Add a public page above.</p>';
    return;
  }
  monitorsNode.innerHTML = monitors.map(m => `
    <article class="card">
      <span class="status ${m.last_status === 'error' ? 'error' : ''}">${escapeHtml(m.last_status)}</span>
      <h3>${escapeHtml(m.name)}</h3>
      <div class="url" title="${escapeHtml(m.url)}">${escapeHtml(m.url)}</div>
      <p class="muted">Every ${m.interval_minutes} min${m.last_error ? `<br>${escapeHtml(m.last_error)}` : ''}</p>
      <div class="actions">
        <button data-check="${m.id}">Check now</button>
        <button class="ghost" data-changes="${m.id}" data-name="${escapeHtml(m.name)}">Changes</button>
      </div>
    </article>`).join('');
}

document.querySelector('#monitor-form').addEventListener('submit', async event => {
  event.preventDefault(); errorNode.textContent = '';
  const data = Object.fromEntries(new FormData(event.currentTarget));
  data.interval_minutes = Number(data.interval_minutes);
  if (!data.ignore_selector) data.ignore_selector = null;
  try {
    await request('/api/monitors', {method:'POST', body:JSON.stringify(data)});
    event.currentTarget.reset(); await loadMonitors();
  } catch (error) { errorNode.textContent = error.message; }
});

monitorsNode.addEventListener('click', async event => {
  const checkId = event.target.dataset.check;
  const changesId = event.target.dataset.changes;
  if (checkId) {
    event.target.disabled = true; event.target.textContent = 'Checking…';
    await request(`/api/monitors/${checkId}/check`, {method:'POST'}).catch(error => alert(error.message));
    await loadMonitors();
  }
  if (changesId) {
    const changes = await request(`/api/monitors/${changesId}/changes`);
    document.querySelector('#changes-title').textContent = `${event.target.dataset.name}: changes`;
    document.querySelector('#changes').innerHTML = changes.length
      ? changes.map(change => `<p class="muted">${new Date(change.created_at).toLocaleString()}</p><pre>${escapeHtml(change.diff)}</pre>`).join('')
      : '<p class="muted">No changes recorded yet.</p>';
    dialog.showModal();
  }
});

document.querySelector('#refresh').addEventListener('click', loadMonitors);
document.querySelector('#close-dialog').addEventListener('click', () => dialog.close());
loadMonitors().catch(error => monitorsNode.innerHTML = `<p class="error">${escapeHtml(error.message)}</p>`);
