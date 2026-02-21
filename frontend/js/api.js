/**
 * BluePrint API client — all backend communication goes through here.
 */
const API_BASE = '/api';

async function api(path, options = {}) {
    const url = API_BASE + path;
    const config = {
        headers: { 'Content-Type': 'application/json' },
        ...options,
    };
    if (config.body && typeof config.body === 'object') {
        config.body = JSON.stringify(config.body);
    }
    const resp = await fetch(url, config);
    if (!resp.ok) {
        const err = await resp.json().catch(() => ({ detail: resp.statusText }));
        throw new Error(err.detail || 'API error');
    }
    return resp.json();
}

// ─── Dashboard ───
export const getDashboardStats = () => api('/dashboard/stats');

// ─── Assets ───
export const getAssets = (activeOnly = true) => api(`/assets/?active_only=${activeOnly}`);
export const addAsset = (data) => api('/assets/', { method: 'POST', body: data });
export const removeAsset = (id) => api(`/assets/${id}`, { method: 'DELETE' });
export const activateAsset = (id) => api(`/assets/${id}/activate`, { method: 'POST' });

// ─── Strategies ───
export const getStrategies = (activeOnly = false) => api(`/strategies/?active_only=${activeOnly}`);
export const createStrategy = (data) => api('/strategies/', { method: 'POST', body: data });
export const updateStrategy = (id, data) => api(`/strategies/${id}`, { method: 'PUT', body: data });
export const deleteStrategy = (id) => api(`/strategies/${id}`, { method: 'DELETE' });
export const toggleStrategy = (id) => api(`/strategies/${id}/toggle`, { method: 'POST' });
export const getConditionTypes = () => api('/strategies/condition-types');

// ─── Setups ───
export const getSetups = (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return api(`/setups/?${qs}`);
};
export const getAllSetups = (limit = 100) => api(`/setups/all?limit=${limit}`);
export const getSetup = (id) => api(`/setups/${id}`);
export const getSetupsByAsset = (symbol) => api(`/setups/by-asset/${encodeURIComponent(symbol)}`);
export const getPerformanceSummary = (strategyId) => {
    const qs = strategyId ? `?strategy_id=${strategyId}` : '';
    return api(`/setups/performance/summary${qs}`);
};

// ─── Scans ───
export const triggerScan = () => api('/scans/trigger', { method: 'POST' });
export const getScanLogs = (limit = 20) => api(`/scans/logs?limit=${limit}`);
export const stopScan = () => api('/scans/stop', { method: 'POST' });
export const getScanStatus = () => api('/scans/status');

// ─── Journal ───
export const getJournalEntries = (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return api(`/journal/?${qs}`);
};
export const createJournalEntry = (data) => api('/journal/', { method: 'POST', body: data });
export const updateJournalEntry = (id, data) => api(`/journal/${id}`, { method: 'PUT', body: data });
export const deleteJournalEntry = (id) => api(`/journal/${id}`, { method: 'DELETE' });
export const getJournalStats = (days = 30) => api(`/journal/stats?days=${days}`);
export const getJournalCalendar = (days = 90) => api(`/journal/calendar?days=${days}`);

// ─── Backtester ───
export const runBacktest = (data) => api('/backtest/run', { method: 'POST', body: data });

// ─── Chart Data ───
export const getOHLCV = (symbol, timeframe = '1d', limit = 200) => {
    const safe = symbol.replace('/', '-');
    return api(`/chart/ohlcv/${safe}?timeframe=${timeframe}&limit=${limit}`);
};

// ─── Webhooks ───
export const getWebhookHistory = () => api('/webhooks/tradingview/history');
