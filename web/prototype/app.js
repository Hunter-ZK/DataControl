const $ = (s) => document.querySelector(s);
const $$ = (s) => document.querySelectorAll(s);

let lastSearchRows = [];
let currentSearchType = 'ALL';
let currentPage = 'home';
let pageStack = [];

function setActiveNav(button) {
  $$('.app-nav button').forEach((x) => x.classList.remove('active'));
  if (button) button.classList.add('active');
}

function show(page, button, push = true) {
  if (push && page !== currentPage) pageStack.push(currentPage);
  ['home', 'overview', 'searchPage', 'detail'].forEach((id) => {
    const el = document.getElementById(id);
    if (el) el.classList.toggle('hidden', id !== page);
  });
  currentPage = page;
  setActiveNav(button);
  const labels = { home: '首页', overview: '数据概览', searchPage: '资产检索', detail: '数据集详情' };
  $('#crumb').textContent = labels[page] || 'DataControl';
  $('#topBack').classList.toggle('hidden', page === 'home');
  window.scrollTo(0, 0);
}

function appBack() {
  const target = pageStack.pop() || 'home';
  const button = document.querySelector(`[data-page="${target}"]`);
  show(target, button, false);
}

function focusGlobalSearch() {
  show('home', document.querySelector('[data-page=home]'));
  setTimeout(() => $('#q')?.focus(), 0);
}

async function api(path, options) {
  const response = await fetch(path, options);
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

async function loadOverview() {
  try {
    const data = await api('/api/v1/home/overview');
    $('#overviewTables').textContent = Number(data.tableCount || 0).toLocaleString();
    $('#overviewColumns').textContent = Number(data.columnCount || 0).toLocaleString();
    $('#overviewMetrics').textContent = Number(data.metricCount || 0).toLocaleString();
    $('#overviewCodes').textContent = Number(data.codeTableCount || 0).toLocaleString();
    $('#overviewCatalogs').innerHTML = (data.topCatalogs || []).slice(0, 6).map((x) => `<div><b>${x.name}</b><span>${x.tableCount} 个数据集</span><p>${x.code}</p></div>`).join('');
    $('#overviewLayers').innerHTML = (data.layers || []).map((x) => `<span><b>${x.tableCount}</b>${x.layerCode}</span>`).join('');
  } catch (_) {
    // Keep static placeholders when P1 enrichment has not been run yet.
  }
}

function renderPreview(rows) {
  $('#resultMeta').textContent = `${rows.length} 条联想`;
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
    $('#results').innerHTML = '<div class="result">检索索引尚未生成，请先运行测试数据脚本。</div>';
  }
}

async function submitSearch(keyword) {
  const q = (keyword || $('#q')?.value || $('#searchPageQ')?.value || '贷款余额').trim();
  if ($('#q')) $('#q').value = q;
  if ($('#searchPageQ')) $('#searchPageQ').value = q;
  show('searchPage', document.querySelector('[data-page=searchPage]'));
  $('#searchSummary').textContent = `正在检索“${q}”…`;
  $('#fullResults').innerHTML = '<div class="search-loading">正在查询资产索引…</div>';
  currentSearchType = 'ALL';
  setFacetActive('ALL');
  try {
    lastSearchRows = await api('/api/v1/search?q=' + encodeURIComponent(q));
    renderFullResults(lastSearchRows, q);
    recordSearchHistory(q);
  } catch (_) {
    $('#searchSummary').textContent = '检索索引尚未就绪';
    $('#fullResults').innerHTML = '<div class="search-empty">请先运行测试数据生成脚本。</div>';
  }
}

function setFacetActive(type) {
  $$('.search-facets [data-type]').forEach((button) => button.classList.toggle('active', button.dataset.type === type));
}

function filterResults(type, button) {
  currentSearchType = type;
  setFacetActive(type);
  applyLocalFilters();
  if (window.innerWidth <= 1050) $('#searchFacets').classList.remove('open');
}

function applyLocalFilters() {
  let rows = [...lastSearchRows];
  if (currentSearchType !== 'ALL') rows = rows.filter((x) => x.asset_type === currentSearchType);
  // Search index currently does not expose lifecycle/common flags for every asset type.
  // P2 will move these to server-side facets. In P1 the controls stay non-destructive.
  const q = $('#searchPageQ')?.value || $('#q')?.value || '';
  renderFullResults(rows, q, true);
}

function renderFullResults(rows, q, preserveCounts = false) {
  $('#searchSummary').textContent = `“${q}” · ${rows.length} 条结果`;
  if (!preserveCounts) {
    const counts = rows.reduce((acc, row) => {
      acc[row.asset_type] = (acc[row.asset_type] || 0) + 1;
      return acc;
    }, {});
    $('#facetAll').textContent = rows.length;
    $('#facetTable').textContent = counts.TABLE || 0;
    $('#facetColumn').textContent = counts.COLUMN || 0;
    $('#facetMetric').textContent = counts.METRIC || 0;
  }
  $('#fullResults').innerHTML = rows.map((x) => `
    <article class="search-result-card" onclick="openSearchResult('${x.asset_id}','${x.asset_type}')">
      <div class="search-result-main">
        <div class="search-result-kicker"><span class="type">${x.asset_type}</span><span>统一资产索引</span></div>
        <h3>${x.title_hl || x.title}</h3>
        <code>${x.technical_name}</code>
        <p>${x.body_hl || '点击进入资产详情，继续查看字段、口径、调度和关系信息。'}</p>
      </div>
      <div class="search-result-side"><span>相关度</span><b>${Number(x.score || 0).toFixed(2)}</b><i>→</i></div>
    </article>`).join('') || '<div class="search-empty">没有找到匹配资产。试试更短的技术名、业务名称或字段名。</div>';
}

function toggleFacets() {
  $('#searchFacets').classList.toggle('open');
}

function openSearchResult(id, type) {
  if (type === 'TABLE' && id.startsWith('DS')) {
    openDetail(id);
    return;
  }
  // P1 only has full dataset detail UI; fields and metrics remain in search result view until P2.
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
  $('#cols').innerHTML = x.columns.slice(0, 20).map((c) => `<tr><td>${c.columnName}</td><td>${c.cnName || '—'}</td><td>${c.dataType}</td><td>${c.bizDefinition || '—'}</td></tr>`).join('');
  show('detail', null);
  recordView(id);
}

async function recordView(assetId) {
  try {
    await fetch(`/api/v1/activity/views`, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({assetType:'TABLE',assetId})});
  } catch (_) {}
}

async function recordSearchHistory(keyword) {
  try {
    await fetch(`/api/v1/activity/search-history`, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({keyword})});
  } catch (_) {}
}

let suggestionTimer;
$('#q').addEventListener('input', () => {
  clearTimeout(suggestionTimer);
  suggestionTimer = setTimeout(loadSuggestions, 180);
});
$('#q').addEventListener('keydown', (event) => { if (event.key === 'Enter') submitSearch(); });
$('#searchPageQ').addEventListener('keydown', (event) => { if (event.key === 'Enter') submitSearch($('#searchPageQ').value); });
$$('.hint').forEach((chip) => chip.onclick = () => submitSearch(chip.textContent));
document.addEventListener('keydown', (event) => {
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
    event.preventDefault();
    focusGlobalSearch();
  }
});

loadHome();
loadOverview();
