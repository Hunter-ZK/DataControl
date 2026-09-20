const $ = (s) => document.querySelector(s);
const $$ = (s) => document.querySelectorAll(s);
let lastSearchRows = [];

function setActiveNav(button) {
  $$('nav button').forEach((x) => x.classList.remove('active'));
  if (button) button.classList.add('active');
}

function show(page, button) {
  ['home', 'overview', 'searchPage', 'detail'].forEach((id) => {
    const el = document.getElementById(id);
    if (el) el.classList.toggle('hidden', id !== page);
  });
  setActiveNav(button);
  const labels = { home: '首页', overview: '数据概览', searchPage: '资产检索', detail: '数据集详情' };
  $('#crumb').textContent = labels[page] || 'DataControl';
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
    $('#recent').innerHTML = rows.slice(0, 4).map((x) => `<button onclick="openDetail('${x.assetId}')"><b>${x.bizName}</b><span>${x.tableName}</span></button>`).join('');
  } catch (_) {
    $('#recent').innerHTML = '<span>请先运行测试数据生成脚本</span>';
  }
}

function renderPreview(rows) {
  $('#resultMeta').textContent = `${rows.length} 条预览结果`;
  $('#results').innerHTML = rows.slice(0, 6).map((x) => `<button class="result preview-result" onclick="openSearchResult('${x.asset_id}','${x.asset_type}')"><span class="type">${x.asset_type}</span><span class="result-copy"><b>${x.title_hl || x.title}</b><code>${x.technical_name}</code></span><span class="result-arrow">↗</span></button>`).join('') || '<div class="result">没有找到匹配结果</div>';
  $('#viewAllResults').classList.toggle('hidden', rows.length === 0);
}

async function loadSuggestions() {
  const q = $('#q').value.trim();
  if (!q) {
    $('#searchDock').classList.add('hidden-dock');
    return;
  }
  $('#searchDock').classList.remove('hidden-dock');
  $('#resultMeta').textContent = '联想中…';
  try {
    lastSearchRows = await api('/api/v1/search?q=' + encodeURIComponent(q));
    renderPreview(lastSearchRows);
  } catch (_) {
    $('#resultMeta').textContent = '索引未就绪';
    $('#results').innerHTML = '<div class="result">检索索引尚未生成：运行 samples/generate_demo_data.py</div>';
  }
}

async function submitSearch(keyword) {
  const q = (keyword || $('#q').value || $('#searchPageQ').value || '贷款余额').trim();
  $('#q').value = q;
  $('#searchPageQ').value = q;
  show('searchPage', document.querySelector('[data-page=searchPage]'));
  $('#searchSummary').textContent = `正在检索“${q}”…`;
  $('#fullResults').innerHTML = '<div class="search-loading">正在查询资产索引…</div>';
  try {
    const rows = await api('/api/v1/search?q=' + encodeURIComponent(q));
    lastSearchRows = rows;
    renderFullResults(rows, q);
  } catch (_) {
    $('#searchSummary').textContent = '检索索引尚未就绪';
    $('#fullResults').innerHTML = '<div class="search-empty">请先运行测试数据生成脚本。</div>';
  }
}

function renderFullResults(rows, q) {
  $('#searchSummary').textContent = `“${q}” · ${rows.length} 条结果`;
  const counts = rows.reduce((acc, row) => {
    acc[row.asset_type] = (acc[row.asset_type] || 0) + 1;
    return acc;
  }, {});
  $('#facetAll').textContent = rows.length;
  $('#facetTable').textContent = counts.TABLE || 0;
  $('#facetColumn').textContent = counts.COLUMN || 0;
  $('#facetMetric').textContent = counts.METRIC || 0;
  $('#fullResults').innerHTML = rows.map((x) => `
    <article class="search-result-card" onclick="openSearchResult('${x.asset_id}','${x.asset_type}')">
      <div class="search-result-main">
        <div class="search-result-kicker"><span class="type">${x.asset_type}</span><span>命中：名称 / 技术标识</span></div>
        <h3>${x.title_hl || x.title}</h3>
        <code>${x.technical_name}</code>
        <p>${x.body_hl || '来自统一资产索引，点击查看资产详情与关联信息。'}</p>
      </div>
      <div class="search-result-side"><span>相关度</span><b>${Number(x.score || 0).toFixed(2)}</b><i>→</i></div>
    </article>`).join('') || '<div class="search-empty">没有找到匹配资产。试试更短的技术名、业务名称或字段名。</div>';
}

function openSearchResult(id, type) {
  if (type === 'TABLE' && id.startsWith('DS')) {
    openDetail(id);
    return;
  }
  submitSearch($('#searchPageQ').value || $('#q').value);
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
  show('detail', null);
}

let suggestionTimer;
$('#q').addEventListener('input', () => {
  clearTimeout(suggestionTimer);
  suggestionTimer = setTimeout(loadSuggestions, 180);
});
$('#q').addEventListener('keydown', (event) => { if (event.key === 'Enter') submitSearch(); });
$('#searchPageQ').addEventListener('keydown', (event) => { if (event.key === 'Enter') submitSearch($('#searchPageQ').value); });
$$('.hint').forEach((chip) => chip.onclick = () => submitSearch(chip.textContent));
loadHome();
