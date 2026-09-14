(function () {
  const { esc, num, pct, signClass, relativeTime, lineChart, ruleSetLabel, filterLabel } = window.TB;
  const PAGE_SIZE = 50;
  const $ = (id) => document.getElementById(id);

  const state = {
    candidates: [],
    selectedKey: null,
    tf: 'all',
    kind: 'all',
    dir: 'all',
    reason: 'all',
    date: '',
    page: 0,
    walkForward: null,
  };

  const keyOf = (c) => `${c.candidate_name}__${c.timeframe}`;
  const selected = () => state.candidates.find((c) => keyOf(c) === state.selectedKey);

  function visibleCandidates() {
    return state.candidates.filter(
      (c) =>
        (state.tf === 'all' || c.timeframe === state.tf) &&
        (state.kind === 'all' || (state.kind === 'mtf') === Boolean(c.filter_name)),
    );
  }

  async function load() {
    $('reload').disabled = true;
    try {
      const response = await fetch('/api/backtest', { cache: 'no-store' });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const payload = await response.json();
      state.candidates = payload.candidates
        .slice()
        .sort((a, b) => b.performance_metric - a.performance_metric)
        .map((c, i) => ({ ...c, rank: i + 1 }));
      renderRunMeta(payload);
      state.walkForward = payload.walk_forward || null;
      renderWalkForward();

      const hasResults = state.candidates.length > 0;
      $('md').hidden = !hasResults;
      $('no-results').hidden = hasResults;
      if (!hasResults) return;

      const fromHash = decodeURIComponent(location.hash.slice(1));
      const keep = [fromHash, state.selectedKey].find((k) => k && state.candidates.some((c) => keyOf(c) === k));
      select(keep || keyOf(state.candidates[0]), { resetPage: false });
    } catch (error) {
      $('run-meta').textContent = `Couldn't load results (${error.message}). Is the dashboard server running?`;
    } finally {
      $('reload').disabled = false;
    }
  }

  function renderRunMeta(payload) {
    const meta = $('run-meta');
    if (!payload.generated_at) {
      meta.textContent = 'No backtest run yet';
      meta.removeAttribute('title');
      return;
    }
    const dataSpan = payload.window_start ? ` · data ${payload.window_start.slice(0, 10)} → ${payload.window_end.slice(0, 10)}` : '';
    meta.textContent = `Backtest ran ${relativeTime(payload.generated_at)}${dataSpan}`;
    meta.title = `Run at ${new Date(payload.generated_at).toLocaleString()}`;
  }

  function renderWalkForward() {
    const wfv = state.walkForward;
    $('wfv-panel').hidden = !wfv;
    if (!wfv) return;

    const totalReturnPct = (wfv.equity_curve.length
      ? (wfv.equity_curve[wfv.equity_curve.length - 1].equity / wfv.equity_curve[0].equity - 1) * 100
      : 0);

    $('wfv-stats').innerHTML = [
      ['Status', wfv.passed ? '<span class="pill good">Passed</span>' : '<span class="pill bad">Failed</span>', 'out-of-sample Test Windows only'],
      ['Out-of-sample metric', `<span class="${signClass(wfv.performance_metric)}">${num(wfv.performance_metric)}</span>`, `threshold to pass is > 0`],
      ['Test windows', num(wfv.windows.length, 0), '180d Selection / 60d Test, anchored'],
      ['Out-of-sample return', `<span class="${signClass(totalReturnPct)}">${pct(totalReturnPct)}</span>`, 'compounded across windows'],
    ]
      .map(([label, value, sub]) => `<div class="stat"><div class="stat-label">${label}</div><div class="stat-value">${value}</div><div class="stat-sub">${sub}</div></div>`)
      .join('');

    const points = wfv.equity_curve.map((p) => ({ y: (p.equity - 1) * 100, label: p.date.slice(0, 10), point: p }));
    lineChart($('wfv-chart'), points, {
      formatY: (v) => `${num(v, Math.abs(v) >= 100 ? 0 : 1)}%`,
      tooltip: (p) => `
        <div class="muted">${esc(p.point.date.slice(0, 10))}</div>
        <div>equity <span class="${signClass(p.y)}">${pct(p.y)}</span></div>`,
    });

    $('wfv-rows').innerHTML = wfv.windows
      .map((w) => {
        const members = w.members.map((m) => `${ruleSetLabel(m.candidate_name)} (${m.timeframe})`).join(', ') || '<span class="muted">none qualified</span>';
        return `<tr>
          <td class="num r muted">${w.index + 1}</td>
          <td>${esc(w.test_start.slice(0, 10))} → ${esc(w.test_end.slice(0, 10))}</td>
          <td class="num r ${signClass(w.return_pct)}">${pct(w.return_pct)}</td>
          <td class="num r">${num(w.members.length, 0)}</td>
          <td>${members}</td>
        </tr>`;
      })
      .join('');
  }

  function renderList() {
    const list = visibleCandidates();
    $('cand-count').textContent =
      list.length === state.candidates.length ? `${list.length} ranked` : `${list.length} of ${state.candidates.length}`;

    $('cand-list').innerHTML = list.length
      ? list
          .map((c) => {
            const key = keyOf(c);
            const isSelected = key === state.selectedKey;
            const tags = [`<span class="chip">${esc(c.timeframe)}</span>`];
            if (c.filter_name) tags.push(`<span class="chip mtf">${esc(filterLabel(c.filter_name, c.filter_timeframe))}</span>`);
            return `<li>
              <button type="button" class="cand${c.in_ensemble ? '' : ' excluded'}" role="option"
                aria-selected="${isSelected}" data-key="${esc(key)}" tabindex="${isSelected ? 0 : -1}">
                <span class="cand-rank">${c.rank}</span>
                <span>
                  <span class="cand-name">${esc(ruleSetLabel(c.candidate_name))}</span>
                  <span class="cand-tags">${tags.join('')}</span>
                </span>
                <span class="cand-metric">
                  <span class="m ${signClass(c.performance_metric)}">${num(c.performance_metric, 1)}</span><br>
                  <span class="r ${signClass(c.return_pct)}">${pct(c.return_pct, 0)}</span>
                </span>
              </button>
            </li>`;
          })
          .join('')
      : '<li class="empty"><strong>No candidates match.</strong>Change the timeframe or type filter.</li>';
  }

  function select(key, { resetPage = true } = {}) {
    state.selectedKey = key;
    if (resetPage) state.page = 0;
    history.replaceState(null, '', `#${encodeURIComponent(key)}`);
    renderList();
    renderDetail();
  }

  function renderDetail() {
    const c = selected();
    if (!c) return;

    const winStats = (trades) => {
      const wins = trades.filter((t) => t.pnl_pct > 0).length;
      return { count: trades.length, wins, rate: trades.length ? (wins / trades.length) * 100 : null };
    };
    const all = winStats(c.trades);
    const long = winStats(c.trades.filter((t) => t.direction === 1));
    const short = winStats(c.trades.filter((t) => t.direction === -1));
    const rate = (s) => (s.rate === null ? '<span class="muted">—</span>' : `${num(s.rate, 1)}%`);
    const winsOf = (s) => `${num(s.wins, 0)} of ${num(s.count, 0)} won`;

    $('detail-title').textContent = ruleSetLabel(c.candidate_name);
    $('detail-id').textContent = `${c.candidate_name} · ${c.timeframe}`;

    const tags = [`<span class="chip">${esc(c.timeframe)}</span>`];
    if (c.filter_name) tags.push(`<span class="chip mtf">${esc(filterLabel(c.filter_name, c.filter_timeframe))}</span>`);
    tags.push(c.in_ensemble ? '<span class="pill good">In Ensemble</span>' : '<span class="pill bad">Excluded</span>');
    $('detail-tags').innerHTML = tags.join('');

    $('detail-stats').innerHTML = [
      ['Return', `<span class="${signClass(c.return_pct)}">${pct(c.return_pct)}</span>`, 'compounded'],
      ['Max drawdown', `${num(c.max_drawdown_pct)}%`, 'peak to trough'],
      ['Performance metric', `<span class="${signClass(c.performance_metric)}">${num(c.performance_metric)}</span>`, `rank ${c.rank} of ${state.candidates.length}`],
      ['Trades', num(c.trade_count, 0), `${num(long.count, 0)} long · ${num(short.count, 0)} short`],
      ['Win rate', rate(all), winsOf(all)],
      ['<span class="pos">Long</span> win rate', rate(long), winsOf(long)],
      ['<span class="neg">Short</span> win rate', rate(short), winsOf(short)],
    ]
      .map(([label, value, sub]) => `<div class="stat"><div class="stat-label">${label}</div><div class="stat-value">${value}</div><div class="stat-sub">${sub}</div></div>`)
      .join('');

    renderChart(c);
    renderTrades();
  }

  function renderChart(c) {
    let equity = 1;
    const points = c.trades.map((t) => {
      equity *= 1 + t.pnl_pct / 100;
      return { y: (equity - 1) * 100, label: t.exit_time.slice(0, 10), trade: t };
    });
    lineChart($('chart'), points, {
      formatY: (v) => `${num(v, Math.abs(v) >= 100 ? 0 : 1)}%`,
      tooltip: (p, i) => `
        <div>Trade ${num(i + 1, 0)} · <span class="${p.trade.direction === 1 ? 'pos' : 'neg'}">${p.trade.direction === 1 ? 'LONG' : 'SHORT'}</span></div>
        <div class="muted">closed ${esc(p.trade.exit_time)}</div>
        <div>trade <span class="${signClass(p.trade.pnl_pct)}">${pct(p.trade.pnl_pct, 3)}</span></div>
        <div>total <span class="${signClass(p.y)}">${pct(p.y)}</span></div>`,
    });
  }

  function filteredTrades() {
    const c = selected();
    if (!c) return [];
    return c.trades
      .map((t, i) => ({ ...t, n: i + 1 }))
      .filter(
        (t) =>
          (state.dir === 'all' || String(t.direction) === state.dir) &&
          (state.reason === 'all' || t.exit_reason === state.reason) &&
          (!state.date || t.entry_time.includes(state.date) || t.exit_time.includes(state.date)),
      );
  }

  function renderTrades() {
    const trades = filteredTrades();
    const pages = Math.max(1, Math.ceil(trades.length / PAGE_SIZE));
    state.page = Math.min(state.page, pages - 1);
    const slice = trades.slice(state.page * PAGE_SIZE, (state.page + 1) * PAGE_SIZE);

    $('trades-empty').hidden = slice.length > 0;
    $('trade-rows').innerHTML = slice
      .map((t) => {
        const long = t.direction === 1;
        return `<tr>
          <td class="num r muted">${t.n}</td>
          <td><span class="call ${long ? 'long' : 'short'}">${long ? 'LONG' : 'SHORT'}</span></td>
          <td class="num">${esc(t.entry_time)}</td>
          <td class="num r">${num(t.entry_price)}</td>
          <td class="num">${esc(t.exit_time)}</td>
          <td class="num r">${num(t.exit_price)}</td>
          <td class="num r ${signClass(t.pnl_pct)}">${pct(t.pnl_pct, 3)}</td>
          <td class="muted">${t.exit_reason === 'stop_loss' ? 'Stop loss' : 'Signal change'}</td>
        </tr>`;
      })
      .join('');

    const first = trades.length ? state.page * PAGE_SIZE + 1 : 0;
    const last = state.page * PAGE_SIZE + slice.length;
    $('page-info').textContent = `${num(first, 0)}–${num(last, 0)} of ${num(trades.length, 0)} trades`;
    $('prev-page').disabled = state.page === 0;
    $('next-page').disabled = state.page >= pages - 1;
  }

  // --- events ---

  $('cand-list').addEventListener('click', (event) => {
    const button = event.target.closest('.cand');
    if (button) select(button.dataset.key);
  });

  $('cand-list').addEventListener('keydown', (event) => {
    if (event.key !== 'ArrowDown' && event.key !== 'ArrowUp') return;
    const list = visibleCandidates();
    const index = list.findIndex((c) => keyOf(c) === state.selectedKey);
    const next = list[Math.max(0, Math.min(list.length - 1, index + (event.key === 'ArrowDown' ? 1 : -1)))];
    if (!next) return;
    event.preventDefault();
    select(keyOf(next));
    $('cand-list').querySelector('[aria-selected="true"]')?.focus();
  });

  $('tf-filter').addEventListener('change', (event) => { state.tf = event.target.value; renderList(); });
  $('kind-filter').addEventListener('change', (event) => { state.kind = event.target.value; renderList(); });

  document.querySelectorAll('.segmented [data-dir]').forEach((button) =>
    button.addEventListener('click', () => {
      state.dir = button.dataset.dir;
      state.page = 0;
      document.querySelectorAll('.segmented [data-dir]').forEach((b) => b.setAttribute('aria-pressed', String(b === button)));
      renderTrades();
    }),
  );
  $('reason-filter').addEventListener('change', (event) => { state.reason = event.target.value; state.page = 0; renderTrades(); });
  $('date-search').addEventListener('input', (event) => { state.date = event.target.value.trim(); state.page = 0; renderTrades(); });
  $('prev-page').addEventListener('click', () => { state.page -= 1; renderTrades(); });
  $('next-page').addEventListener('click', () => { state.page += 1; renderTrades(); });
  $('reload').addEventListener('click', load);

  let resizeTimer;
  window.addEventListener('resize', () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => { const c = selected(); if (c) renderChart(c); }, 120);
  });

  load();
})();
