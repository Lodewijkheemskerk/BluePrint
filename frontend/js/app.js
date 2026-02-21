/**
 * BluePrint — Main application controller.
 */
import * as api from './api.js';
import {
    formatPrice, formatPercent, formatDate, timeAgo,
    directionBadge, statusBadge, regimeBadge, tradingViewUrl,
    showToast, openModal, closeModal
} from './utils.js';

let currentView = 'setups';
let chartInstance = null;
let volumeSeriesRef = null;
let selectedSetupForJournal = null;

// ─── Live Log State ──────────────────────────────────────────────────────────
let logSocket = null;
let logEntries = [];           // all received entries
let logPaused = false;
let logLevelFilter = 'all';
let logSearchTerm = '';
let logAutoScroll = true;
const LOG_MAX = 5000;          // max entries to keep in memory

// ─── Navigation ─────────────────────────────────────────────────────────────

function navigate(view) {
    currentView = view;
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    document.querySelectorAll('.nav-links a').forEach(a => a.classList.remove('active'));

    const viewEl = document.getElementById(`view-${view}`);
    const navEl = document.querySelector(`.nav-links a[data-view="${view}"]`);
    if (viewEl) viewEl.classList.add('active');
    if (navEl) navEl.classList.add('active');

    const loaders = {
        setups: loadSetups,
        strategies: loadStrategies,
        universe: loadUniverse,
        regime: loadRegime,
        scans: loadScans,
        journal: loadJournal,
        backtester: loadBacktester,
        logs: loadLogs,
    };
    if (loaders[view]) loaders[view]();
}

// ─── Dashboard / Setups View ─────────────────────────────────────────────────

async function loadSetups() {
    try {
        const [stats, setups] = await Promise.all([
            api.getDashboardStats(),
            api.getSetups(),
        ]);

        // Stats row
        document.getElementById('stat-active-setups').textContent = stats.active_setups;
        document.getElementById('stat-active-strategies').textContent = stats.active_strategies;
        document.getElementById('stat-universe-size').textContent = stats.assets_in_universe;
        document.getElementById('stat-setups-today').textContent = stats.setups_today;

        const regimeEl = document.getElementById('stat-regime');
        if (stats.market_regime) {
            regimeEl.innerHTML = regimeBadge(stats.market_regime.regime);
        } else {
            regimeEl.innerHTML = '<span class="text-muted">No data</span>';
        }

        const lastScanEl = document.getElementById('stat-last-scan');
        if (stats.last_scan) {
            lastScanEl.textContent = timeAgo(stats.last_scan.started_at);
        } else {
            lastScanEl.textContent = 'Never';
        }

        // Setups table
        renderSetupsTable(setups);
        // Ensure event delegation is set up after rendering
        setupSetupsTableEventDelegation();
    } catch (e) {
        showToast('Failed to load dashboard: ' + e.message, 'error');
    }
}

function renderSetupsTable(setups) {
    const tbody = document.getElementById('setups-tbody');
    if (!setups.length) {
        tbody.innerHTML = `<tr><td colspan="10" class="empty-state"><h3>No active setups</h3><p>Run a scan or wait for the next scheduled scan to detect setups.</p></td></tr>`;
        return;
    }
    // Use data attribute instead of inline onclick for better event handling
    tbody.innerHTML = setups.map(s => `
        <tr data-setup-id="${s.id}" style="cursor:pointer">
            <td><strong>${s.asset.symbol}</strong></td>
            <td>${s.strategy_name}</td>
            <td>${directionBadge(s.direction)}</td>
            <td>${statusBadge(s.status)}</td>
            <td>${formatPrice(s.entry_price)}</td>
            <td class="red">${formatPrice(s.stop_loss)}</td>
            <td class="green">${formatTakeProfits(s)}</td>
            <td><strong>${s.risk_reward_ratio ? s.risk_reward_ratio.toFixed(1) + ':1' : '—'}</strong></td>
            <td>${s.funding_rate != null ? (s.funding_rate * 100).toFixed(4) + '%' : '—'}</td>
            <td>${timeAgo(s.detected_at)}</td>
        </tr>
    `).join('');
}

// Setup event delegation for setup table rows (runs once on page load)
function setupSetupsTableEventDelegation() {
    const tbody = document.getElementById('setups-tbody');
    if (tbody && !tbody.hasAttribute('data-delegation-setup')) {
        tbody.setAttribute('data-delegation-setup', 'true');
        tbody.addEventListener('click', (e) => {
            const row = e.target.closest('tr[data-setup-id]');
            if (row && row.dataset.setupId) {
                const setupId = parseInt(row.dataset.setupId);
                if (setupId && window.app && window.app.showSetupDetail) {
                    window.app.showSetupDetail(setupId);
                } else {
                    console.error('Cannot open setup detail: setupId or showSetupDetail not available', { setupId, hasApp: !!window.app });
                }
            }
        });
    }
}

function formatTakeProfits(setup) {
    const levels = [
        { label: 'TP1', price: setup.take_profit_1 },
        { label: 'TP2', price: setup.take_profit_2 },
        { label: 'TP3', price: setup.take_profit_3 },
    ].filter(level => level.price != null);

    if (!levels.length) return '—';
    return levels.map(level => `${level.label} ${formatPrice(level.price)}`).join(' · ');
}

async function showSetupDetail(setupId) {
    try {
        if (!setupId || isNaN(setupId)) {
            console.error('Invalid setupId:', setupId);
            showToast('Invalid setup ID', 'error');
            return;
        }
        const setup = await api.getSetup(setupId);
        selectedSetupForJournal = setup;
        const content = document.getElementById('setup-detail-content');

        content.innerHTML = `
            <div style="display:flex;align-items:center;gap:12px;margin-bottom:16px">
                <span style="font-size:20px;font-weight:700">${setup.asset.symbol}</span>
                ${directionBadge(setup.direction)}
                ${statusBadge(setup.status)}
            </div>
            <div class="grid-2" style="margin-bottom:16px">
                <div class="level-item"><span class="level-label">Strategy</span><span class="level-value">${setup.strategy_name}</span></div>
                <div class="level-item"><span class="level-label">Detected</span><span class="level-value">${formatDate(setup.detected_at)}</span></div>
                <div class="level-item"><span class="level-label">Entry</span><span class="level-value">${formatPrice(setup.entry_price)}</span></div>
                <div class="level-item"><span class="level-label">Stop Loss</span><span class="level-value red">${formatPrice(setup.stop_loss)}</span></div>
                <div class="level-item"><span class="level-label">TP1</span><span class="level-value green">${formatPrice(setup.take_profit_1)}</span></div>
                <div class="level-item"><span class="level-label">TP2</span><span class="level-value green">${formatPrice(setup.take_profit_2)}</span></div>
                <div class="level-item"><span class="level-label">TP3</span><span class="level-value green">${formatPrice(setup.take_profit_3)}</span></div>
                <div class="level-item"><span class="level-label">R:R</span><span class="level-value">${setup.risk_reward_ratio ? setup.risk_reward_ratio.toFixed(1) + ':1' : '—'}</span></div>
                <div class="level-item"><span class="level-label">Funding Rate</span><span class="level-value">${setup.funding_rate != null ? (setup.funding_rate * 100).toFixed(4) + '%' : '—'}</span></div>
                <div class="level-item"><span class="level-label">Regime</span><span>${regimeBadge(setup.market_regime)}</span></div>
            </div>
            <div style="margin-bottom:12px">
                <span class="level-label">Performance: </span>
                ${setup.tp1_hit ? '<span class="badge badge-long">TP1 Hit</span>' : ''}
                ${setup.tp2_hit ? '<span class="badge badge-long">TP2 Hit</span>' : ''}
                ${setup.tp3_hit ? '<span class="badge badge-long">TP3 Hit</span>' : ''}
                ${setup.sl_hit ? '<span class="badge badge-short">SL Hit</span>' : ''}
                ${!setup.tp1_hit && !setup.sl_hit ? '<span style="color:var(--text-secondary)">Pending</span>' : ''}
            </div>
            <div style="display:flex;gap:8px;margin-bottom:16px">
                <a href="${setup.tradingview_url}" target="_blank" class="btn btn-secondary btn-sm">Open in TradingView</a>
                <button class="btn btn-primary btn-sm" onclick="window.app.logTradeFromSetup(${setup.id})">Log Trade</button>
            </div>
            <div id="setup-chart" class="chart-container"></div>
        `;

        openModal('setup-detail-modal');

        // Load chart
        setTimeout(() => loadChart('setup-chart', setup.asset.symbol, '4h', setup), 100);
    } catch (e) {
        showToast('Failed to load setup: ' + e.message, 'error');
    }
}

// ─── Chart Loading (TradingView Lightweight Charts) ──────────────────────────

async function loadChart(containerId, symbol, timeframe = '1d', setup = null) {
    const container = document.getElementById(containerId);
    if (!container) return;
    container.innerHTML = '';

    if (typeof LightweightCharts === 'undefined') {
        container.innerHTML = '<div class="empty-state"><p>Chart library loading...</p></div>';
        return;
    }

    const chart = LightweightCharts.createChart(container, {
        width: container.clientWidth,
        height: container.clientHeight || 400,
        layout: {
            background: { type: 'solid', color: '#131722' },
            textColor: '#d1d4dc',
            fontSize: 12,
            fontFamily: 'Inter, sans-serif',
        },
        grid: {
            vertLines: { color: '#1e222d' },
            horzLines: { color: '#1e222d' },
        },
        crosshair: { mode: 0 },
        rightPriceScale: { borderColor: '#2a2e39' },
        timeScale: {
            borderColor: '#2a2e39',
            timeVisible: true,
        },
    });

    const candleSeries = chart.addCandlestickSeries({
        upColor: '#089981',
        downColor: '#f23645',
        borderUpColor: '#089981',
        borderDownColor: '#f23645',
        wickUpColor: '#089981',
        wickDownColor: '#f23645',
    });

    const volSeries = chart.addHistogramSeries({
        priceFormat: { type: 'volume' },
        priceScaleId: 'vol',
    });

    chart.priceScale('vol').applyOptions({
        scaleMargins: { top: 0.8, bottom: 0 },
    });

    try {
        const data = await api.getOHLCV(symbol, timeframe);
        if (data.candles.length) {
            candleSeries.setData(data.candles);
            volSeries.setData(data.volumes);
        }

        // Draw setup levels if provided
        if (setup) {
            if (setup.entry_price) {
                candleSeries.createPriceLine({
                    price: setup.entry_price,
                    color: '#2962FF',
                    lineWidth: 1,
                    lineStyle: 2,
                    axisLabelVisible: true,
                    title: 'Entry',
                });
            }
            if (setup.stop_loss) {
                candleSeries.createPriceLine({
                    price: setup.stop_loss,
                    color: '#f23645',
                    lineWidth: 1,
                    lineStyle: 2,
                    axisLabelVisible: true,
                    title: 'SL',
                });
            }
            if (setup.take_profit_1) {
                candleSeries.createPriceLine({
                    price: setup.take_profit_1,
                    color: '#089981',
                    lineWidth: 1,
                    lineStyle: 2,
                    axisLabelVisible: true,
                    title: 'TP1',
                });
            }
            if (setup.take_profit_2) {
                candleSeries.createPriceLine({
                    price: setup.take_profit_2,
                    color: '#089981',
                    lineWidth: 1,
                    lineStyle: 0,
                    axisLabelVisible: true,
                    title: 'TP2',
                });
            }
        }

        chart.timeScale().fitContent();
    } catch (e) {
        container.innerHTML = `<div class="empty-state"><p>Could not load chart data</p></div>`;
    }

    // Resize observer
    const ro = new ResizeObserver(() => {
        chart.applyOptions({ width: container.clientWidth, height: container.clientHeight });
    });
    ro.observe(container);
}

// ─── Strategies View ─────────────────────────────────────────────────────────

async function loadStrategies() {
    try {
        const strategies = await api.getStrategies();
        const container = document.getElementById('strategies-list');

        if (!strategies.length) {
            container.innerHTML = `<div class="empty-state"><h3>No strategies yet</h3><p>Create your first strategy to start scanning.</p></div>`;
            return;
        }

        container.innerHTML = strategies.map(s => `
            <div class="strategy-card">
                <div class="strategy-card-header">
                    <div>
                        <span class="strategy-name">${s.name}</span>
                        ${directionBadge(s.direction)}
                    </div>
                    <div style="display:flex;align-items:center;gap:8px">
                        <label class="toggle">
                            <input type="checkbox" ${s.is_active ? 'checked' : ''} onchange="window.app.toggleStrategy(${s.id})">
                            <span class="toggle-slider"></span>
                        </label>
                        <button class="btn-icon" onclick="window.app.deleteStrategy(${s.id})" title="Delete">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18M8 6V4a2 2 0 012-2h4a2 2 0 012 2v2m3 0v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6h14"/></svg>
                        </button>
                    </div>
                </div>
                ${s.description ? `<p style="font-size:12px;color:var(--text-secondary);margin-bottom:8px">${s.description}</p>` : ''}
                <div class="strategy-meta">
                    <span>Setups: <strong>${s.recent_setups_count}</strong></span>
                    <span>Win Rate: <strong>${s.win_rate != null ? s.win_rate + '%' : '—'}</strong></span>
                    ${s.valid_regimes ? `<span>Regimes: ${s.valid_regimes.map(r => regimeBadge(r)).join(' ')}</span>` : ''}
                </div>
                <div class="strategy-conditions">
                    ${s.conditions.map(c => `<span class="condition-tag">${c.condition_type} (${c.timeframe})</span>`).join('')}
                </div>
            </div>
        `).join('');
    } catch (e) {
        showToast('Failed to load strategies: ' + e.message, 'error');
    }
}

async function createNewStrategy() {
    const name = document.getElementById('new-strat-name').value.trim();
    const direction = document.getElementById('new-strat-direction').value;
    const description = document.getElementById('new-strat-description').value.trim();

    if (!name) { showToast('Strategy name is required', 'error'); return; }

    // Gather conditions from the dynamic form
    const conditionEls = document.querySelectorAll('.condition-row');
    const conditions = [];
    conditionEls.forEach(el => {
        const type = el.querySelector('.cond-type').value;
        const tf = el.querySelector('.cond-tf').value;
        const paramsStr = el.querySelector('.cond-params').value.trim();
        let params = {};
        try { if (paramsStr) params = JSON.parse(paramsStr); } catch (e) {}
        const required = el.querySelector('.cond-required').checked;
        conditions.push({
            condition_type: type,
            timeframe: tf,
            parameters: params,
            is_required: required,
            order: conditions.length,
        });
    });

    try {
        await api.createStrategy({ name, direction, description, is_active: true, conditions });
        closeModal('new-strategy-modal');
        showToast('Strategy created', 'success');
        loadStrategies();
    } catch (e) {
        showToast('Failed to create strategy: ' + e.message, 'error');
    }
}

// ─── Universe View ───────────────────────────────────────────────────────────

async function loadUniverse() {
    try {
        const assets = await api.getAssets(false);
        const tbody = document.getElementById('universe-tbody');

        tbody.innerHTML = assets.map(a => `
            <tr>
                <td><strong>${a.symbol}</strong></td>
                <td>${a.base_currency}</td>
                <td><span class="badge ${a.source === 'dynamic' ? 'badge-active' : 'badge-detected'}">${a.source}</span></td>
                <td>${a.market_cap_rank || '—'}</td>
                <td>${a.is_active ? '<span style="color:var(--green)">Active</span>' : '<span style="color:var(--text-secondary)">Inactive</span>'}</td>
                <td>
                    <a href="${tradingViewUrl(a.symbol)}" target="_blank" class="btn btn-secondary btn-sm">TV</a>
                    ${a.is_active
                        ? `<button class="btn btn-danger btn-sm" onclick="window.app.removeAsset(${a.id})">Remove</button>`
                        : `<button class="btn btn-primary btn-sm" onclick="window.app.activateAsset(${a.id})">Activate</button>`
                    }
                </td>
            </tr>
        `).join('');
    } catch (e) {
        showToast('Failed to load universe: ' + e.message, 'error');
    }
}

async function addNewAsset() {
    const symbol = document.getElementById('new-asset-symbol').value.trim().toUpperCase();
    if (!symbol || !symbol.includes('/')) {
        showToast('Enter a valid symbol like BTC/USDT', 'error');
        return;
    }
    const base = symbol.split('/')[0];
    const quote = symbol.split('/')[1] || 'USDT';
    try {
        await api.addAsset({ symbol, base_currency: base, quote_currency: quote, source: 'watchlist' });
        document.getElementById('new-asset-symbol').value = '';
        showToast(`${symbol} added to watchlist`, 'success');
        loadUniverse();
    } catch (e) {
        showToast('Failed to add asset: ' + e.message, 'error');
    }
}

// ─── Market Regime View ──────────────────────────────────────────────────────

async function loadRegime() {
    try {
        const stats = await api.getDashboardStats();
        const container = document.getElementById('regime-content');

        if (stats.market_regime) {
            const r = stats.market_regime;
            container.innerHTML = `
                <div class="stat-card" style="margin-bottom:20px">
                    <div class="stat-label">Current Market Regime</div>
                    <div style="font-size:28px;margin:12px 0">${regimeBadge(r.regime)}</div>
                    <p style="color:var(--text-secondary)">${r.description}</p>
                </div>
                <div class="grid-2">
                    <div class="stat-card">
                        <div class="stat-label">BTC Trend</div>
                        <div class="stat-value">${r.btc_trend}</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">Confidence</div>
                        <div class="stat-value">${formatPercent(r.confidence * 100)}</div>
                    </div>
                </div>
            `;
        } else {
            container.innerHTML = `<div class="empty-state"><h3>No regime data</h3><p>Run a scan to detect the current market regime.</p></div>`;
        }
    } catch (e) {
        showToast('Failed to load regime: ' + e.message, 'error');
    }
}

// ─── Scan History View ───────────────────────────────────────────────────────

async function loadScans() {
    try {
        const [logs, status] = await Promise.all([
            api.getScanLogs(),
            api.getScanStatus(),
        ]);
        const tbody = document.getElementById('scans-tbody');
        const activeScanId = status.is_running ? status.scan_id : null;

        _scanIsRunning = !!status.is_running;
        if (!_scanIsRunning) {
            _cancellationRequested = false;
        }

        if (!logs.length) {
            tbody.innerHTML = `<tr><td colspan="7" class="empty-state"><h3>No scan history</h3><p>Trigger your first scan.</p></td></tr>`;
            if (_scanIsRunning) {
                if (!_cancellationRequested) {
                    setScanButtonState('running');
                } else {
                    setScanButtonState('cancelling');
                }
                startScanStatusPolling();
            } else {
                setScanButtonState('idle');
            }
            return;
        }

        tbody.innerHTML = logs.map(l => `
            <tr>
                <td>${l.id}</td>
                <td>${formatDate(l.started_at)}</td>
                <td>${l.finished_at
                    ? formatDate(l.finished_at)
                    : (activeScanId === l.id
                        ? '<div class="spinner" style="margin:0;width:16px;height:16px"></div>'
                        : '—'
                    )
                }</td>
                <td>${l.assets_scanned}</td>
                <td><strong>${l.setups_found}</strong></td>
                <td>${regimeBadge(l.market_regime)}</td>
                <td><span class="badge badge-${l.status === 'completed' ? 'active' : l.status === 'running' ? 'detected' : l.status === 'cancelled' ? 'invalidated' : 'invalidated'}">${l.status}</span></td>
            </tr>
        `).join('');

        if (_scanIsRunning) {
            if (!_cancellationRequested) {
                setScanButtonState('running');
            } else {
                setScanButtonState('cancelling');
            }
            startScanStatusPolling();
        } else {
            setScanButtonState('idle');
        }
    } catch (e) {
        showToast('Failed to load scan logs: ' + e.message, 'error');
        // Still try to update button state on error
        updateScanButton();
    }
}

// ─── Journal View ────────────────────────────────────────────────────────────

async function loadJournal() {
    try {
        const [entries, stats] = await Promise.all([
            api.getJournalEntries(),
            api.getJournalStats(30),
        ]);

        // Stats
        document.getElementById('journal-total').textContent = stats.total_trades;
        document.getElementById('journal-winrate').textContent = stats.win_rate != null ? stats.win_rate + '%' : '—';
        document.getElementById('journal-avgr').textContent = stats.avg_r_multiple != null ? stats.avg_r_multiple + 'R' : '—';
        const totalPnl = stats.total_pnl != null ? Number(stats.total_pnl) : null;
        document.getElementById('journal-pnl').textContent = totalPnl != null && Number.isFinite(totalPnl) ? '$' + totalPnl.toFixed(2) : '—';

        // Table
        const tbody = document.getElementById('journal-tbody');
        if (!entries.length) {
            tbody.innerHTML = `<tr><td colspan="9" class="empty-state"><h3>No journal entries</h3><p>Log your first trade from a setup alert.</p></td></tr>`;
            return;
        }

        tbody.innerHTML = entries.map(e => `
            <tr>
                <td>${formatDateShort(e.created_at)}</td>
                <td><strong>${e.asset_symbol}</strong></td>
                <td>${e.strategy_name || '—'}</td>
                <td>${e.direction ? directionBadge(e.direction) : '—'}</td>
                <td><span class="badge badge-${e.action === 'took_trade' ? 'active' : 'expired'}">${e.action}</span></td>
                <td><span class="${e.outcome === 'win' ? 'green' : e.outcome === 'loss' ? 'red' : ''}">${e.outcome || '—'}</span></td>
                <td>${e.planned_rr != null ? '1:' + e.planned_rr : '—'}</td>
                <td>${e.pnl_r_multiple != null ? e.pnl_r_multiple + 'R' : '—'}</td>
                <td>${e.tags && e.tags.length ? e.tags.map(t => `<span class="condition-tag">${t}</span>`).join('') : '—'}</td>
            </tr>
        `).join('');
    } catch (e) {
        showToast('Failed to load journal: ' + e.message, 'error');
    }
}

function formatDateShort(isoStr) {
    if (!isoStr) return '—';
    return new Date(isoStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function resetJournalForm() {
    document.getElementById('journal-setup-id').value = '';
    document.getElementById('journal-symbol').value = '';
    document.getElementById('journal-strategy').value = '';
    document.getElementById('journal-direction').value = '';
    document.getElementById('journal-action').value = 'took_trade';
    document.getElementById('journal-outcome').value = 'open';
    document.getElementById('journal-entry-price').value = '';
    document.getElementById('journal-stop-price').value = '';
    document.getElementById('journal-tp1-price').value = '';
    document.getElementById('journal-tp2-price').value = '';
    document.getElementById('journal-tp3-price').value = '';
    document.getElementById('journal-r-multiple').value = '';
    document.getElementById('journal-planned-rr').value = '';
    document.getElementById('journal-tags').value = '';
    document.getElementById('journal-notes').value = '';
}

function buildJournalTagsFromSetup(setup) {
    const tags = [
        setup.strategy_name,
        setup.direction,
        setup.status,
        setup.market_regime,
    ].filter(Boolean);
    return [...new Set(tags)];
}

function buildJournalNotesFromSetup(setup) {
    const lines = [
        'Prefilled from setup:',
        `- Setup ID: ${setup.id}`,
        `- Detected: ${formatDate(setup.detected_at)}`,
    ];
    if (setup.entry_price != null) lines.push(`- Planned entry: ${setup.entry_price}`);
    if (setup.stop_loss != null) lines.push(`- Planned stop: ${setup.stop_loss}`);
    if (setup.take_profit_1 != null) lines.push(`- Planned TP1: ${setup.take_profit_1}`);
    if (setup.take_profit_2 != null) lines.push(`- Planned TP2: ${setup.take_profit_2}`);
    if (setup.take_profit_3 != null) lines.push(`- Planned TP3: ${setup.take_profit_3}`);
    if (setup.risk_reward_ratio != null) lines.push(`- Setup R:R: ${setup.risk_reward_ratio.toFixed(2)}:1`);
    if (setup.funding_rate != null) lines.push(`- Funding rate: ${(setup.funding_rate * 100).toFixed(4)}%`);
    if (setup.market_regime) lines.push(`- Market regime: ${setup.market_regime}`);
    return lines.join('\n');
}

function prefillJournalFromSetup(setup) {
    resetJournalForm();
    document.getElementById('journal-setup-id').value = setup.id;
    document.getElementById('journal-symbol').value = setup.asset?.symbol || '';
    document.getElementById('journal-strategy').value = setup.strategy_name || '';
    document.getElementById('journal-direction').value = setup.direction || '';
    document.getElementById('journal-entry-price').value = setup.entry_price ?? '';
    document.getElementById('journal-stop-price').value = setup.stop_loss ?? '';
    document.getElementById('journal-tp1-price').value = setup.take_profit_1 ?? '';
    document.getElementById('journal-tp2-price').value = setup.take_profit_2 ?? '';
    document.getElementById('journal-tp3-price').value = setup.take_profit_3 ?? '';
    document.getElementById('journal-planned-rr').value = setup.risk_reward_ratio ?? '';
    document.getElementById('journal-tags').value = buildJournalTagsFromSetup(setup).join(', ');
    document.getElementById('journal-notes').value = buildJournalNotesFromSetup(setup);
}

function openJournalModal() {
    resetJournalForm();
    openModal('new-journal-modal');
}

async function logTradeFromSetup(setupId) {
    closeModal('setup-detail-modal');
    try {
        let setup = selectedSetupForJournal;
        if (!setup || setup.id !== setupId) {
            setup = await api.getSetup(setupId);
        }

        selectedSetupForJournal = setup;
        prefillJournalFromSetup(setup);
        openModal('new-journal-modal');
    } catch (e) {
        showToast('Failed to prefill trade entry: ' + e.message, 'error');
    }
}

async function saveJournalEntry() {
    const parseOptionalNumber = (id) => {
        const raw = document.getElementById(id).value.trim();
        if (!raw) return null;
        const parsed = parseFloat(raw);
        return Number.isNaN(parsed) ? null : parsed;
    };

    const data = {
        setup_id: parseInt(document.getElementById('journal-setup-id').value) || null,
        asset_symbol: document.getElementById('journal-symbol').value,
        strategy_name: document.getElementById('journal-strategy').value,
        direction: document.getElementById('journal-direction').value || null,
        action: document.getElementById('journal-action').value,
        outcome: document.getElementById('journal-outcome').value || null,
        actual_entry: parseOptionalNumber('journal-entry-price'),
        actual_stop: parseOptionalNumber('journal-stop-price'),
        actual_tp1: parseOptionalNumber('journal-tp1-price'),
        actual_tp2: parseOptionalNumber('journal-tp2-price'),
        actual_tp3: parseOptionalNumber('journal-tp3-price'),
        pnl_r_multiple: parseOptionalNumber('journal-r-multiple'),
        planned_rr: parseOptionalNumber('journal-planned-rr'),
        notes: document.getElementById('journal-notes').value || null,
        tags: document.getElementById('journal-tags').value
            ? document.getElementById('journal-tags').value.split(',').map(t => t.trim()).filter(Boolean)
            : null,
    };

    try {
        await api.createJournalEntry(data);
        closeModal('new-journal-modal');
        showToast('Trade logged', 'success');
        if (currentView === 'journal') loadJournal();
    } catch (e) {
        showToast('Failed to log trade: ' + e.message, 'error');
    }
}

// ─── Backtester View ─────────────────────────────────────────────────────────

async function loadBacktester() {
    try {
        const strategies = await api.getStrategies();
        const select = document.getElementById('bt-strategy');
        select.innerHTML = strategies.map(s =>
            `<option value="${s.id}">${s.name}</option>`
        ).join('');
    } catch (e) { /* ignore */ }
}

async function runBacktest() {
    const strategyId = parseInt(document.getElementById('bt-strategy').value);
    const timeframe = document.getElementById('bt-timeframe').value;
    const symbolsInput = document.getElementById('bt-symbols').value.trim();
    const symbols = symbolsInput ? symbolsInput.split(',').map(s => s.trim()) : null;

    const resultEl = document.getElementById('bt-results');
    resultEl.innerHTML = '<div class="spinner"></div>';

    try {
        const result = await api.runBacktest({
            strategy_id: strategyId,
            symbols,
            timeframe,
        });

        resultEl.innerHTML = `
            <div class="stats-row" style="margin-bottom:16px">
                <div class="stat-card"><div class="stat-label">Total Setups</div><div class="stat-value">${result.total_setups}</div></div>
                <div class="stat-card"><div class="stat-label">Win Rate</div><div class="stat-value ${result.win_rate >= 50 ? 'green' : 'red'}">${result.win_rate}%</div></div>
                <div class="stat-card"><div class="stat-label">Avg R:R</div><div class="stat-value">${result.avg_rr}</div></div>
                <div class="stat-card"><div class="stat-label">Max Drawdown</div><div class="stat-value red">${result.max_drawdown}R</div></div>
                <div class="stat-card"><div class="stat-label">Setups/Month</div><div class="stat-value">${result.setups_per_month}</div></div>
                <div class="stat-card"><div class="stat-label">Symbols Tested</div><div class="stat-value">${result.symbols_tested}</div></div>
            </div>
            ${result.setup_details.length ? `
            <div class="table-container" style="max-height:300px;overflow-y:auto">
                <table>
                    <thead><tr><th>Symbol</th><th>Entry Date</th><th>Entry</th><th>SL</th><th>TP1</th><th>Result</th><th>P&L (R)</th></tr></thead>
                    <tbody>
                        ${result.setup_details.map(d => `
                            <tr>
                                <td>${d.symbol}</td>
                                <td>${d.entry_date ? d.entry_date.split('T')[0] : '—'}</td>
                                <td>${formatPrice(d.entry_price)}</td>
                                <td class="red">${formatPrice(d.stop_loss)}</td>
                                <td class="green">${formatPrice(d.take_profit_1)}</td>
                                <td><span class="${d.outcome === 'win' ? 'green' : d.outcome === 'loss' ? 'red' : ''}">${d.outcome}</span></td>
                                <td class="${d.pnl_r >= 0 ? 'green' : 'red'}">${d.pnl_r}R</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>` : ''}
        `;
    } catch (e) {
        resultEl.innerHTML = `<div class="empty-state"><h3>Backtest failed</h3><p>${e.message}</p></div>`;
    }
}

// ─── Helper Actions ──────────────────────────────────────────────────────────

async function handleToggleStrategy(id) {
    try {
        await api.toggleStrategy(id);
        loadStrategies();
    } catch (e) {
        showToast('Failed: ' + e.message, 'error');
    }
}

async function handleDeleteStrategy(id) {
    if (!confirm('Delete this strategy? This cannot be undone.')) return;
    try {
        await api.deleteStrategy(id);
        showToast('Strategy deleted', 'success');
        loadStrategies();
    } catch (e) {
        showToast('Failed: ' + e.message, 'error');
    }
}

async function handleRemoveAsset(id) {
    try {
        await api.removeAsset(id);
        loadUniverse();
    } catch (e) {
        showToast('Failed: ' + e.message, 'error');
    }
}

async function handleActivateAsset(id) {
    try {
        await api.activateAsset(id);
        loadUniverse();
    } catch (e) {
        showToast('Failed: ' + e.message, 'error');
    }
}

async function handleTriggerScan() {
    // Prevent triggering if already running
    if (_scanIsRunning) {
        showToast('A scan is already running', 'warning');
        return;
    }
    try {
        // Reset cancellation flag for new scan
        _cancellationRequested = false;
        // Optimistic: immediately show "scanning" state
        _scanIsRunning = true;
        setScanButtonState('running');
        await api.triggerScan();
        showToast('Scan triggered — running in background', 'info');
        startScanStatusPolling();
    } catch (e) {
        _scanIsRunning = false;
        _cancellationRequested = false;
        setScanButtonState('idle');
        showToast('Failed to trigger scan: ' + e.message, 'error');
    }
}

async function handleStopScan() {
    // Prevent double-clicking stop
    if (_cancellationRequested) {
        return; // Already requested
    }
    _cancellationRequested = true;
    setScanButtonState('cancelling');
    try {
        const result = await api.stopScan();
        showToast(result.message, 'info');
        // Keep in cancelling state until poll detects scan actually stopped
    } catch (e) {
        _cancellationRequested = false; // Reset on error so user can retry
        showToast('Failed to stop scan: ' + e.message, 'error');
        // Restore stop button so user can retry
        setScanButtonState('running');
    }
}

let scanStatusInterval = null;
let _scanIsRunning = false;
let _cancellationRequested = false;

function startScanStatusPolling() {
    // Clear any existing interval
    if (scanStatusInterval) {
        clearInterval(scanStatusInterval);
    }

    // Poll every 2 seconds
    scanStatusInterval = setInterval(async () => {
        try {
            const status = await api.getScanStatus();

            if (status.is_running) {
                _scanIsRunning = true;
                // Only show "running" if we haven't requested cancellation
                // Otherwise keep showing "cancelling" until it actually stops
                if (!_cancellationRequested) {
                    setScanButtonState('running');
                }
                // If cancellation was requested, keep showing "cancelling"
            } else {
                _scanIsRunning = false;
                _cancellationRequested = false; // Reset cancellation flag
                setScanButtonState('idle');
                clearInterval(scanStatusInterval);
                scanStatusInterval = null;
                // Refresh data when scan completes
                if (currentView === 'scans') loadScans();
                if (currentView === 'setups') loadSetups();
                showToast('Scan finished', 'success');
            }
        } catch (e) {
            console.error('Failed to get scan status:', e);
        }
    }, 2000);
}

/**
 * Set all scan buttons to a given visual state.
 * States: 'idle' | 'running' | 'cancelling'
 */
function setScanButtonState(state) {
    const buttons = document.querySelectorAll('[data-scan-btn]');

    buttons.forEach(btn => {
        btn.disabled = state === 'cancelling';

        if (state === 'running') {
            btn.innerHTML = `
                <span class="scan-spinner"></span>
                Cancel Scan
            `;
            btn.onclick = () => window.app.stopScan();
            btn.className = 'btn btn-danger btn-sm scan-btn-running';
        } else if (state === 'cancelling') {
            btn.innerHTML = `
                <span class="scan-spinner"></span>
                Cancelling…
            `;
            btn.onclick = null;
            btn.className = 'btn btn-danger btn-sm scan-btn-running';
        } else {
            btn.innerHTML = `
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 4v6h-6"/><path d="M20.49 15a9 9 0 11-2.12-9.36L23 10"/></svg>
                Scan Now
            `;
            btn.onclick = () => window.app.triggerScan();
            btn.className = 'btn btn-primary btn-sm';
            btn.disabled = false;
        }
    });
}

function updateScanButton() {
    // Check the real backend status and sync UI
    api.getScanStatus().then(status => {
        _scanIsRunning = status.is_running;
        if (!status.is_running) {
            _cancellationRequested = false; // Reset if no scan running
        }
        // Only set state if we haven't requested cancellation
        if (status.is_running && !_cancellationRequested) {
            setScanButtonState('running');
            startScanStatusPolling();
        } else if (!status.is_running) {
            setScanButtonState('idle');
        }
        // If running and cancellation requested, keep "cancelling" state
    }).catch(() => {
        _cancellationRequested = false;
        setScanButtonState('idle');
    });
}

function addConditionRow() {
    const container = document.getElementById('conditions-container');
    const row = document.createElement('div');
    row.className = 'condition-row';
    row.style.cssText = 'display:grid;grid-template-columns:1fr 80px 1fr 60px 30px;gap:6px;margin-bottom:6px;align-items:center';
    row.innerHTML = `
        <select class="form-select cond-type">
            <option value="price_above_ma">Price Above MA</option>
            <option value="price_below_ma">Price Below MA</option>
            <option value="ma_slope_rising">MA Slope Rising</option>
            <option value="ma_slope_falling">MA Slope Falling</option>
            <option value="ema_crossover_bullish">EMA Cross Bullish</option>
            <option value="ema_crossover_bearish">EMA Cross Bearish</option>
            <option value="higher_highs_higher_lows">HH/HL (Uptrend)</option>
            <option value="lower_highs_lower_lows">LH/LL (Downtrend)</option>
            <option value="break_of_structure_bullish">BOS Bullish</option>
            <option value="break_of_structure_bearish">BOS Bearish</option>
            <option value="price_near_support">Near Support</option>
            <option value="price_near_resistance">Near Resistance</option>
            <option value="bb_squeeze">BB Squeeze</option>
            <option value="atr_above_average">ATR Above Avg</option>
            <option value="atr_below_average">ATR Below Avg</option>
            <option value="candle_range_contraction">Range Contraction</option>
            <option value="rsi_in_range">RSI In Range</option>
            <option value="rsi_oversold">RSI Oversold</option>
            <option value="rsi_overbought">RSI Overbought</option>
            <option value="macd_histogram_positive">MACD Hist +</option>
            <option value="macd_histogram_negative">MACD Hist -</option>
            <option value="rsi_bullish_divergence">RSI Bull Div</option>
            <option value="volume_spike">Volume Spike</option>
            <option value="volume_declining">Volume Declining</option>
            <option value="funding_rate_below">Funding Below</option>
            <option value="funding_rate_above">Funding Above</option>
            <option value="open_interest_rising">OI Rising</option>
        </select>
        <select class="form-select cond-tf">
            <option value="1d">1D</option>
            <option value="4h">4H</option>
            <option value="1h">1H</option>
            <option value="15m">15M</option>
        </select>
        <input class="form-input cond-params" placeholder='{"period":50}' value="{}">
        <label class="toggle" style="margin:0 auto"><input type="checkbox" checked class="cond-required"><span class="toggle-slider"></span></label>
        <button class="btn-icon" onclick="this.closest('.condition-row').remove()" title="Remove">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
        </button>
    `;
    container.appendChild(row);
}

// ─── Live Log Viewer ─────────────────────────────────────────────────────────

function loadLogs() {
    connectLogSocket();
    // Bind search input
    const searchInput = document.getElementById('log-search');
    if (searchInput && !searchInput._bound) {
        searchInput._bound = true;
        searchInput.addEventListener('input', (e) => {
            logSearchTerm = e.target.value.toLowerCase();
            rerenderLogLines();
        });
    }
    // Set up scroll detection for auto-scroll
    const output = document.getElementById('log-output');
    if (output && !output._bound) {
        output._bound = true;
        output.addEventListener('scroll', () => {
            const atBottom = output.scrollHeight - output.scrollTop - output.clientHeight < 40;
            logAutoScroll = atBottom;
        });
    }
}

function connectLogSocket() {
    if (logSocket && (logSocket.readyState === WebSocket.OPEN || logSocket.readyState === WebSocket.CONNECTING)) {
        return; // already connected
    }

    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const url = `${protocol}//${location.host}/ws/logs`;

    logSocket = new WebSocket(url);

    logSocket.onopen = () => {
        setLogStatus('connected', 'Connected');
    };

    logSocket.onmessage = (event) => {
        try {
            const entry = JSON.parse(event.data);
            logEntries.push(entry);
            // Trim if over max
            while (logEntries.length > LOG_MAX) {
                logEntries.shift();
            }
            updateLineCount();
            if (!logPaused) {
                appendLogLine(entry);
            }
        } catch (e) { /* ignore bad messages */ }
    };

    logSocket.onclose = () => {
        setLogStatus('disconnected', 'Disconnected');
        // Auto-reconnect after 3 seconds
        setTimeout(() => {
            if (currentView === 'logs') connectLogSocket();
        }, 3000);
    };

    logSocket.onerror = () => {
        setLogStatus('disconnected', 'Error');
    };
}

function setLogStatus(cls, text) {
    const statusEl = document.getElementById('log-status');
    const textEl = document.getElementById('log-status-text');
    if (statusEl) {
        statusEl.className = 'log-status ' + cls;
    }
    if (textEl) textEl.textContent = text;
}

function updateLineCount() {
    const countEl = document.getElementById('log-line-count');
    if (countEl) {
        const visible = logEntries.filter(e => isLogVisible(e)).length;
        countEl.textContent = `${visible} lines`;
    }
}

function isLogVisible(entry) {
    if (logLevelFilter !== 'all' && entry.level !== logLevelFilter) return false;
    if (logSearchTerm && !entry.message.toLowerCase().includes(logSearchTerm) &&
        !entry.logger.toLowerCase().includes(logSearchTerm)) return false;
    return true;
}

function formatLogTime(isoStr) {
    if (!isoStr) return '';
    const d = new Date(isoStr);
    return d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function highlightSearch(text) {
    if (!logSearchTerm) return escapeHtml(text);
    const escaped = escapeHtml(text);
    const regex = new RegExp(`(${logSearchTerm.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
    return escaped.replace(regex, '<span class="log-highlight">$1</span>');
}

function createLogLineHtml(entry) {
    const visible = isLogVisible(entry);
    const hiddenClass = visible ? '' : ' hidden';
    const levelClass = `log-level-${entry.level}`;
    const msg = highlightSearch(entry.message);
    return `<div class="log-line ${levelClass}${hiddenClass}"><span class="log-ts">${formatLogTime(entry.timestamp)}</span><span class="log-level ${levelClass}">${entry.level}</span><span class="log-logger">${escapeHtml(entry.logger)}</span><span class="log-msg">${msg}</span></div>`;
}

function appendLogLine(entry) {
    const output = document.getElementById('log-output');
    if (!output) return;

    const html = createLogLineHtml(entry);
    output.insertAdjacentHTML('beforeend', html);

    // Auto-scroll to bottom
    if (logAutoScroll) {
        output.scrollTop = output.scrollHeight;
    }
}

function rerenderLogLines() {
    const output = document.getElementById('log-output');
    if (!output) return;

    // Rebuild all lines (needed when filter/search changes)
    const html = logEntries.map(e => createLogLineHtml(e)).join('');
    output.innerHTML = html;
    updateLineCount();

    // Scroll to bottom
    if (logAutoScroll) {
        output.scrollTop = output.scrollHeight;
    }
}

function toggleLogPause() {
    logPaused = !logPaused;
    const label = document.getElementById('log-pause-label');
    const icon = document.getElementById('log-pause-icon');

    if (logPaused) {
        if (label) label.textContent = 'Resume';
        if (icon) icon.innerHTML = '<polygon points="5 3 19 12 5 21"/>';
        setLogStatus('paused', 'Paused');
    } else {
        if (label) label.textContent = 'Pause';
        if (icon) icon.innerHTML = '<rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/>';
        setLogStatus('connected', 'Connected');
        // Catch up: re-render all entries that arrived while paused
        rerenderLogLines();
    }
}

function clearLogs() {
    logEntries = [];
    const output = document.getElementById('log-output');
    if (output) output.innerHTML = '';
    updateLineCount();
}

function filterLogLevel(level, btn) {
    logLevelFilter = level;
    document.querySelectorAll('.log-level-pill').forEach(p => p.classList.remove('active'));
    if (btn) btn.classList.add('active');
    rerenderLogLines();
}

function downloadLogs() {
    const lines = logEntries.map(e =>
        `${e.timestamp} [${e.level}] ${e.logger}: ${e.message}`
    ).join('\n');
    const blob = new Blob([lines], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `blueprint-logs-${new Date().toISOString().slice(0,19).replace(/:/g,'-')}.txt`;
    a.click();
    URL.revokeObjectURL(url);
}

// ─── Init ────────────────────────────────────────────────────────────────────

// Expose functions to global scope for onclick handlers
// Initialize scan button state on page load
document.addEventListener('DOMContentLoaded', () => {
    updateScanButton();
});

window.app = {
    navigate,
    showSetupDetail,
    toggleStrategy: handleToggleStrategy,
    deleteStrategy: handleDeleteStrategy,
    removeAsset: handleRemoveAsset,
    activateAsset: handleActivateAsset,
    triggerScan: handleTriggerScan,
    stopScan: handleStopScan,
    addAsset: addNewAsset,
    createStrategy: createNewStrategy,
    addConditionRow,
    saveJournalEntry,
    openJournalModal,
    logTradeFromSetup,
    runBacktest,
    openModal,
    closeModal,
    // Log viewer
    toggleLogPause,
    clearLogs,
    filterLogLevel,
    downloadLogs,
};

// Setup navigation
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.nav-links a').forEach(a => {
        a.addEventListener('click', (e) => {
            e.preventDefault();
            navigate(a.dataset.view);
        });
    });

    // Setup event delegation for setups table
    setupSetupsTableEventDelegation();

    // Load default view
    navigate('setups');
});
