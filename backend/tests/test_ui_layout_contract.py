from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HTML = (ROOT / "web" / "prototype" / "index.html").read_text(encoding="utf-8")
CSS = (ROOT / "web" / "prototype" / "styles.css").read_text(encoding="utf-8")


def test_shell_uses_single_responsive_layout_system():
    assert '<div class="app-shell">' in HTML
    assert '.app-shell {' in CSS
    assert 'grid-template-columns: var(--sidebar-w) minmax(0, 1fr);' in CSS
    assert 'position: fixed' not in CSS


def test_content_is_centered_and_width_bounded():
    assert '.content-container {' in CSS
    assert 'width: min(100%, var(--content-max));' in CSS
    assert 'margin-inline: auto;' in CSS
    assert 'min-width: 0;' in CSS


def test_search_page_has_only_filter_and_result_columns():
    assert '更好地找到资产' not in HTML
    assert 'search-side-panel' not in HTML
    assert 'search-side-panel' not in CSS
    assert '.search-layout {' in CSS
    assert 'grid-template-columns: 220px minmax(0, 1fr);' in CSS


def test_responsive_breakpoints_cover_desktop_and_narrow_widths():
    for breakpoint in ('1320px', '1080px', '820px', '560px'):
        assert f'@media (max-width: {breakpoint})' in CSS
    assert 'overflow-x: hidden;' in CSS
    assert 'grid-template-columns: 1fr;' in CSS


def test_back_navigation_and_cache_busting_are_present():
    assert 'id="topBack"' in HTML
    assert HTML.count('class="page-back"') >= 3
    assert 'styles.css?v=p1-layout-r4' in HTML
    assert 'app.js?v=p1-layout-r4' in HTML
