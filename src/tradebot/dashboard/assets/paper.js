(function () {
  const { esc, num, pct, signClass, relativeTime, lineChart, ruleSetLabel } = window.TB;
  const POLL_MS = 4000;
  const FAST_POLL_MS = 1000;
  const $ = (id) => document.getElementById(id);

  let lastUpdatedAt;
  let lastState;
  let lastStatus;
  let busy = false;
  let pollTimer;

  // ---------- polling ----------

  async function poll() {
    clearTimeout(pollTimer);
    try {
      const [stateResponse, statusResponse] = await Promise.all([
        fetch('/api/state', { cache: 'no-store' }),
        fetch('/api/paper/status', { cache: 'no-store' }),
      ]);
      if (!stateResponse.ok || !statusResponse.ok) throw new Error(`HTTP ${stateResponse.status}/${statusResponse.status}`);
      const [data, status] = await Promise.all([stateResponse.json(), statusResponse.json()]);

      lastStatus = status;
      renderSession(status);
      renderUpdated(data);
      if (data.updated_at !== lastUpdatedAt) {
        lastUpdatedAt = data.updated_at;
        lastState = data;
        render(data);
      }
    } catch (error) {
      $('status-pill').className = 'pill bad';
      $('status-pill').textContent = 'Offline';
      $('session-detail').textContent = `Can't reach the dashboard server (${error.message}).`;
      $('start-btn').hidden = true;
      $('stop-btn').hidden = true;
    }
    const transitioning = lastStatus && (lastStatus.state === 'stopping' || busy);
    pollTimer = setTimeout(poll, transitioning ? FAST_POLL_MS : POLL_MS);
  }

  // ---------- session control ----------

  const SESSION_VIEW = {
    running: { pill: 'good', label: 'Running' },
    stopping: { pill: 'busy', label: 'Stopping…' },
    stopped: { pill: 'idle', label: 'Stopped' },
    crashed: { pill: 'bad', label: 'Crashed' },
    running_external: { pill: 'good', label: 'Running outside the dashboard' },
  };

  function renderSession(status) {
    const view = SESSION_VIEW[status.state] || { pill: 'idle', label: status.state };
    $('status-pill').className = `pill ${view.pill}`;
    $('status-pill').textContent = view.label;

    const started = status.started_at ? `${new Date(status.started_at).toLocaleString()} (${relativeTime(status.started_at)})` : null;
    const detail = {
      running: started ? `since ${started}` : '',
      stopping: 'waiting for the loop to close its MT5 connection',
      stopped: started ? `last session started ${started}` : 'no session has been started from the dashboard',
      crashed: `the process exited unexpectedly${status.exit_code !== null ? ` (exit code ${status.exit_code})` : ''} — see the log below`,
      running_external: 'started from a terminal; stop it there (Ctrl+C)',
    }[status.state];
    $('session-detail').textContent = detail || '';

    const ensemble = status.ensemble;
    const saved = ensemble.saved_at ? ` · Ensemble saved ${relativeTime(ensemble.saved_at)}` : '';
    $('ensemble-detail').textContent = ensemble.members
      ? `${status.state === 'running' ? 'Trading' : 'Start will trade'} ${ensemble.members} Ensemble members on the Exness demo account${saved}`
      : 'No Ensemble yet — run scripts/run_backtest.py before starting.';

    const canStart = status.state === 'stopped' || status.state === 'crashed';
    $('start-btn').hidden = !canStart;
    $('start-btn').disabled = busy || !ensemble.members;
    $('stop-btn').hidden = status.state !== 'running';
    $('stop-btn').disabled = busy;

    const log = status.log_tail || [];
    $('log-panel').hidden = log.length === 0;
    $('log-tail').textContent = log.join('\n');
    if (status.state === 'crashed') $('log-panel').open = true;
  }

  async function control(action) {
    if (busy) return;
    if (action === 'stop' && !confirm('Stop paper trading? Open simulated positions are discarded — the next Start is a fresh session.')) return;

    busy = true;
    $('action-error').hidden = true;
    $('start-btn').disabled = true;
    $('stop-btn').disabled = true;
    if (action === 'start') {
      $('status-pill').className = 'pill busy';
      $('status-pill').textContent = 'Starting…';
    }
    try {
      const response = await fetch(`/api/paper/${action}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: '{}',
      });
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.detail || `HTTP ${response.status}`);
      }
    } catch (error) {
      $('action-error').textContent = `Couldn't ${action} paper trading: ${error.message}`;
      $('action-error').hidden = false;
    } finally {
      busy = false;
      poll();
    }
  }

  $('start-btn').addEventListener('click', () => control('start'));
  $('stop-btn').addEventListener('click', () => control('stop'));

  // ---------- session data ----------

  function renderUpdated(data) {
    if (!data.updated_at) {
      $('updated').textContent = 'No paper trading state yet';
      $('updated').removeAttribute('title');
      return;
    }
    $('updated').textContent = `Last update ${relativeTime(data.updated_at)}`;
    $('updated').title = new Date(data.updated_at).toLocaleString();
  }

  function render(data) {
    const hasState = Boolean(data.updated_at);
    $('no-state').hidden = hasState;
    $('content').hidden = !hasState;
    if (!hasState) return;

    const members = data.members;
    const open = members.filter((m) => m.position);
    const openLong = open.filter((m) => m.position.direction === 1).length;
    const closedTrades = members.reduce((sum, m) => sum + m.trade_count, 0);
    const timeframes = new Set(members.map((m) => m.timeframe));

    $('stats').innerHTML = [
      ['Total equity', `$${num(data.total_equity)}`, `started at $${num(data.total_initial_equity)}`],
      ['Return', `<span class="${signClass(data.total_return_pct)}">${pct(data.total_return_pct)}</span>`, 'closed trades only'],
      ['Members', num(members.length, 0), `${timeframes.size} timeframe${timeframes.size === 1 ? '' : 's'}`],
      ['Open positions', num(open.length, 0), `${openLong} long · ${open.length - openLong} short`],
      ['Closed trades', num(closedTrades, 0), `${num(data.equity_history.length, 0)} state snapshots`],
    ]
      .map(([label, value, sub]) => `<div class="stat"><div class="stat-label">${label}</div><div class="stat-value">${value}</div><div class="stat-sub">${sub}</div></div>`)
      .join('');

    renderChart(data);

    $('members').innerHTML = members
      .map((m) => {
        const p = m.position;
        const call = !p ? '<span class="call flat">FLAT</span>' : `<span class="call ${p.direction === 1 ? 'long' : 'short'}">${p.direction === 1 ? 'LONG' : 'SHORT'}</span>`;
        const unrealized = p && p.unrealized_pct !== null ? `<span class="${signClass(p.unrealized_pct)}">${pct(p.unrealized_pct, 3)}</span>` : '<span class="muted">—</span>';
        return `<tr>
          <td><div>${esc(ruleSetLabel(m.candidate_name))}</div><div class="muted num" style="font-size:11px">${esc(m.candidate_name)}</div></td>
          <td><span class="chip">${esc(m.timeframe)}</span></td>
          <td class="num r">$${num(m.equity)}</td>
          <td class="num r ${signClass(m.return_pct)}">${pct(m.return_pct)}</td>
          <td>${call}</td>
          <td class="num r">${p ? num(p.entry_price) : '<span class="muted">—</span>'}</td>
          <td class="num r">${p ? num(p.stop_price) : '<span class="muted">—</span>'}</td>
          <td class="num r">${unrealized}</td>
          <td class="num r">${num(m.trade_count, 0)}</td>
        </tr>`;
      })
      .join('');

    const trades = data.recent_trades.slice().reverse();
    $('trades-empty').hidden = trades.length > 0;
    $('trades-note').textContent = trades.length ? `Newest first · last ${trades.length}` : '';
    $('trades').innerHTML = trades
      .map((t) => {
        const long = t.direction === 1;
        return `<tr>
          <td>${esc(ruleSetLabel(t.candidate_name))} <span class="chip">${esc(t.timeframe)}</span></td>
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
  }

  function renderChart(data) {
    const initial = data.total_initial_equity || 1;
    const points = data.equity_history.map((h) => ({
      y: (h.equity / initial - 1) * 100,
      equity: h.equity,
      label: new Date(h.time).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }),
    }));
    lineChart($('chart'), points, {
      formatY: (v) => `${num(v, 2)}%`,
      tooltip: (p) => `<div>${esc(p.label)}</div><div>$${num(p.equity)}</div><div class="${signClass(p.y)}">${pct(p.y)}</div>`,
    });
  }

  let resizeTimer;
  window.addEventListener('resize', () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => { if (lastState && lastState.updated_at) renderChart(lastState); }, 120);
  });

  poll();
})();
