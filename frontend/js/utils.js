/**
 * Utility functions.
 */

export function formatPrice(price, decimals = 8) {
    if (price == null) return '—';
    if (price >= 1000) return price.toLocaleString('en-US', { maximumFractionDigits: 2 });
    if (price >= 1) return price.toFixed(4);
    return price.toFixed(decimals);
}

export function formatPercent(val, decimals = 1) {
    if (val == null) return '—';
    return val.toFixed(decimals) + '%';
}

export function formatDate(isoStr) {
    if (!isoStr) return '—';
    const d = new Date(isoStr);
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

export function formatDateShort(isoStr) {
    if (!isoStr) return '—';
    return new Date(isoStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

export function timeAgo(isoStr) {
    if (!isoStr) return '—';
    const seconds = (Date.now() - new Date(isoStr).getTime()) / 1000;
    if (seconds < 60) return 'just now';
    if (seconds < 3600) return Math.floor(seconds / 60) + 'm ago';
    if (seconds < 86400) return Math.floor(seconds / 3600) + 'h ago';
    return Math.floor(seconds / 86400) + 'd ago';
}

export function directionBadge(dir) {
    const cls = dir === 'long' ? 'badge-long' : 'badge-short';
    return `<span class="badge ${cls}">${dir}</span>`;
}

export function statusBadge(status) {
    return `<span class="badge badge-${status}">${status}</span>`;
}

export function regimeBadge(regime) {
    if (!regime) return '';
    const label = regime.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
    return `<span class="regime-badge regime-${regime}">${label}</span>`;
}

export function tradingViewUrl(symbol) {
    const clean = symbol.replace('/', '');
    return `https://www.tradingview.com/chart/?symbol=BINANCE:${clean}`;
}

export function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
}

export function openModal(id) {
    document.getElementById(id).classList.add('open');
}

export function closeModal(id) {
    document.getElementById(id).classList.remove('open');
}
