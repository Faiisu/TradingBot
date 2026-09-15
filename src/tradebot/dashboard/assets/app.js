// Shared helpers for both dashboard pages. Plain script (no build step); exposes window.TB.
(function () {
  const esc = (value) =>
    String(value ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);

  const num = (value, digits = 2) =>
    Number(value).toLocaleString('en-US', { minimumFractionDigits: digits, maximumFractionDigits: digits });

  const pct = (value, digits = 2) => `${value > 0 ? '+' : ''}${num(value, digits)}%`;

  const signClass = (value) => (value > 0 ? 'pos' : value < 0 ? 'neg' : 'muted');

  function relativeTime(iso) {
    if (!iso) return 'never';
    const seconds = Math.round((Date.now() - new Date(iso).getTime()) / 1000);
    if (seconds < 60) return 'just now';
    const minutes = Math.round(seconds / 60);
    if (minutes < 60) return `${minutes} min ago`;
    const hours = Math.round(minutes / 60);
    if (hours < 48) return `${hours} h ago`;
    return `${Math.round(hours / 24)} days ago`;
  }

  function niceTicks(min, max, count = 4) {
    const span = max - min || 1;
    const rough = span / count;
    const magnitude = Math.pow(10, Math.floor(Math.log10(rough)));
    const step = [1, 2, 2.5, 5, 10].map((m) => m * magnitude).find((s) => s >= rough);
    const ticks = [];
    for (let t = Math.floor(min / step) * step; t <= max + step * 1e-9; t += step) ticks.push(Number(t.toFixed(10)));
    return ticks;
  }

  // Line chart with a zero baseline, faint grid, emphasized endpoint and a crosshair tooltip.
  // points: [{ y: number, label: string }]; tooltip(point, index) returns HTML.
  function lineChart(container, points, { formatY = (v) => v, tooltip = () => '' } = {}) {
    container.innerHTML = '';
    if (points.length < 2) {
      container.innerHTML = '<div class="empty">Not enough closed trades to draw a curve yet.</div>';
      return;
    }

    const width = container.clientWidth || 800;
    const height = container.clientHeight || 220;
    const pad = { top: 10, right: 14, bottom: 22, left: 64 };
    const plotW = width - pad.left - pad.right;
    const plotH = height - pad.top - pad.bottom;

    const values = points.map((p) => p.y);
    const ticks = niceTicks(Math.min(0, ...values), Math.max(0, ...values));
    const lo = ticks[0];
    const hi = ticks[ticks.length - 1];
    const x = (i) => pad.left + (i / (points.length - 1)) * plotW;
    const y = (v) => pad.top + ((hi - v) / (hi - lo || 1)) * plotH;

    const path = points.map((p, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(p.y).toFixed(1)}`).join('');
    const baseY = y(Math.max(lo, Math.min(0, hi)));
    const area = `${path}L${x(points.length - 1).toFixed(1)},${baseY.toFixed(1)}L${x(0).toFixed(1)},${baseY.toFixed(1)}Z`;
    const last = points[points.length - 1];

    const svgNS = 'http://www.w3.org/2000/svg';
    const svg = document.createElementNS(svgNS, 'svg');
    svg.setAttribute('viewBox', `0 0 ${width} ${height}`);
    svg.setAttribute('role', 'img');
    svg.setAttribute('aria-label', `Equity curve ending at ${formatY(last.y)}`);
    svg.innerHTML = `
      <defs>
        <linearGradient id="chart-area" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#d4a544" stop-opacity="0.22"/>
          <stop offset="100%" stop-color="#d4a544" stop-opacity="0"/>
        </linearGradient>
      </defs>
      ${ticks.map((t) => `<line class="${t === 0 ? 'zero' : 'grid'}" x1="${pad.left}" x2="${width - pad.right}" y1="${y(t)}" y2="${y(t)}"/>
        <text class="tick" x="${pad.left - 8}" y="${y(t) + 3}" text-anchor="end">${esc(formatY(t))}</text>`).join('')}
      <text class="tick" x="${pad.left}" y="${height - 6}">${esc(points[0].label)}</text>
      <text class="tick" x="${width - pad.right}" y="${height - 6}" text-anchor="end">${esc(last.label)}</text>
      <path class="area" d="${area}"/>
      <path class="line" d="${path}"/>
      <circle cx="${x(points.length - 1)}" cy="${y(last.y)}" r="3.5" fill="${last.y >= 0 ? '#3fb968' : '#e5484d'}"/>
      <line class="cross" x1="0" x2="0" y1="${pad.top}" y2="${pad.top + plotH}" visibility="hidden"/>
      <circle class="cross-dot" r="3.5" fill="#d4a544" stroke="#0a0d12" stroke-width="2" visibility="hidden"/>
      <rect x="${pad.left}" y="${pad.top}" width="${plotW}" height="${plotH}" fill="transparent"/>`;
    container.appendChild(svg);

    const tip = document.createElement('div');
    tip.className = 'chart-tip';
    tip.hidden = true;
    container.appendChild(tip);

    const cross = svg.querySelector('.cross');
    const dot = svg.querySelector('.cross-dot');
    const hit = svg.querySelector('rect');

    hit.addEventListener('mousemove', (event) => {
      const box = svg.getBoundingClientRect();
      const mx = ((event.clientX - box.left) / box.width) * width;
      const i = Math.max(0, Math.min(points.length - 1, Math.round(((mx - pad.left) / plotW) * (points.length - 1))));
      const px = x(i);
      const py = y(points[i].y);
      cross.setAttribute('x1', px);
      cross.setAttribute('x2', px);
      cross.setAttribute('visibility', 'visible');
      dot.setAttribute('cx', px);
      dot.setAttribute('cy', py);
      dot.setAttribute('visibility', 'visible');
      tip.innerHTML = tooltip(points[i], i);
      tip.hidden = false;
      const scale = box.width / width;
      const left = px * scale + 12;
      tip.style.left = `${Math.min(left, box.width - tip.offsetWidth - 4)}px`;
      tip.style.top = `${Math.max(0, py * scale - tip.offsetHeight - 10)}px`;
    });
    hit.addEventListener('mouseleave', () => {
      cross.setAttribute('visibility', 'hidden');
      dot.setAttribute('visibility', 'hidden');
      tip.hidden = true;
    });
  }

  const RULE_SET_LABELS = [
    [/^macd_(\d+)_(\d+)_(\d+)/, (m) => `MACD ${m[1]}/${m[2]}/${m[3]}`],
    [/^bollinger_breakout_(\d+)_([\d.]+)/, (m) => `Bollinger Breakout ${m[1]}/${m[2]}`],
    [/^atr_channel_breakout_(\d+)_(\d+)_([\d.]+)/, (m) => `ATR Channel ${m[1]}/${m[2]}/${m[3]}`],
    [/^ma_crossover_(\d+)_(\d+)/, (m) => `MA Crossover ${m[1]}/${m[2]}`],
    [/^rsi_mean_reversion_(\d+)/, (m) => `RSI Reversion ${m[1]}`],
    [/^donchian_breakout_(\d+)_(\d+)/, (m) => `Donchian Breakout ${m[1]}/${m[2]}`],
    [/^supertrend_(\d+)_([\d.]+)/, (m) => `Supertrend ${m[1]}×${m[2]}`],
    [/^adx_dmi_(\d+)/, (m) => `ADX/DMI ${m[1]}`],
    [/^stochastic_reversion_(\d+)_(\d+)/, (m) => `Stochastic Reversion ${m[1]}/${m[2]}`],
    [/^asian_range_breakout$/, () => `Asian Range Breakout`],
    [/^volume_confirmed_breakout_(\d+)_(\d+)/, (m) => `Volume-Confirmed Breakout ${m[1]}/${m[2]}`],
  ];

  function ruleSetLabel(candidateName) {
    for (const [pattern, format] of RULE_SET_LABELS) {
      const match = candidateName.match(pattern);
      if (match) return format(match);
    }
    return candidateName;
  }

  const FILTER_LABELS = { macd: 'MACD', ma_crossover: 'MA Cross', ema_slope: 'EMA slope', REAL_YIELD: 'Real Yield' };
  const filterLabel = (name, timeframe) => `${timeframe} ${FILTER_LABELS[name] || name} filter`;

  window.TB = { esc, num, pct, signClass, relativeTime, lineChart, ruleSetLabel, filterLabel };
})();
