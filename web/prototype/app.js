const $ = (s) => document.querySelector(s);
const $$ = (s) => document.querySelectorAll(s);

function show(page) {
  $('#home').classList.toggle('hidden', page !== 'home');
  $('#detail').classList.toggle('hidden', page !== 'detail');
  window.scrollTo(0, 0);
}

async function api(path) {
  const response = await fetch(path);
  if (!response.ok) throw new Error(await response.text());
  return (await response.json()).data;
}

async function loadHome() {
  try {
    const rows = await api('/api/v1/tables?limit=8');
    $('#recent').innerHTML = rows.slice(0, 5).map((x) => `<button onclick="openDetail('${x.assetId}')"><b>${x.bizName}</b><span>${x.tableName}</span></button>`).join('');
  } catch (_) {
    $('#recent').innerHTML = '<span>请先运行测试数据生成脚本</span>';
  }
}

async function doSearch() {
  const q = $('#q').value || '贷款余额';
  try {
    const rows = await api('/api/v1/search?q=' + encodeURIComponent(q));
    $('#resultMeta').textContent = `${rows.length} 条预览结果`;
    $('#results').className = 'results';
    $('#results').innerHTML = rows.slice(0, 10).map((x) => `<div class="result" onclick="openDetail('${x.asset_id}')"><span class="type">${x.asset_type}</span><h3>${x.title_hl || x.title}</h3><code>${x.technical_name}</code></div>`).join('') || '无结果';
  } catch (_) {
    $('#results').textContent = '检索索引尚未生成：运行 samples/generate_demo_data.py';
  }
}

async function openDetail(id) {
  if (!id.startsWith('DS')) return;
  const x = await api('/api/v1/tables/' + id);
  $('#dName').textContent = x.bizName;
  $('#dTech').textContent = x.tableName;
  $('#dOwner').textContent = x.techOwner || '—';
  $('#dTime').textContent = (x.dataUpdatedAt || '—').replace('T', ' ').slice(0, 16);
  $('#dFreq').textContent = x.updateFreq || '—';
  $('#dId').textContent = x.assetId;
  $('#dDefinition').textContent = x.bizDefinition || '—';
  $('#dCaliber').textContent = x.statCaliber || '—';
  $('#dGrain').textContent = x.grain || '—';
  $('#dSource').textContent = x.dataSourceDesc || '—';
  $('#dSchedule').textContent = (x.scheduleDesc || '未登记') + (x.scheduleNode ? ' · ' + x.scheduleNode : '');
  $('#dNotes').textContent = x.usageNotes || '—';
  $('#cols').innerHTML = x.columns.slice(0, 10).map((c) => `<tr><td>${c.columnName}</td><td>${c.cnName || '—'}</td><td>${c.dataType}</td><td>${c.bizDefinition || '—'}</td></tr>`).join('');
  show('detail');
}

$$('.chips span').forEach((chip) => chip.onclick = () => { $('#q').value = chip.textContent; doSearch(); });
loadHome();
