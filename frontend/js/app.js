const API_URL = `http://${window.location.hostname}:5000`;

document.addEventListener('DOMContentLoaded', () => {
    loadDevices();
    loadNetworkStats();
    
    // Auto-refresh cada 30 segundos
    setInterval(() => {
        loadDevices();
        loadNetworkStats();
    }, 30000);
    
    document.getElementById('scanBtn').addEventListener('click', scanNow);
    document.getElementById('exportBtn').addEventListener('click', exportExcel);
});

async function loadDevices() {
    try {
        const response = await fetch(`${API_URL}/api/devices`);
        const data = await response.json();
        displayDevices(data.devices);
        document.getElementById('deviceCount').textContent = data.devices.length;
    } catch (error) {
        console.error('Error cargando dispositivos:', error);
    }
}

function displayDevices(devices) {
    const tbody = document.getElementById('devicesBody');
    if (!devices) return;
    
    tbody.innerHTML = devices.map(device => `
        <tr>
            <td>${device.ip}</td>
            <td><code>${device.mac}</code></td>
            <td>${device.hostname || '---'}</td>
            <td>${device.vendor || '---'}</td>
            <td>${formatUsage(device.cpu_usage)}</td>
            <td>${formatUsage(device.ram_usage)}</td>
            <td>${formatUsage(device.disk_usage)}</td>
            <td>${(device.network_usage || 0).toFixed(2)} MB</td>
            <td>
                <span class="badge ${device.is_reachable ? 'badge-success' : 'badge-danger'}">
                    ${device.is_reachable ? 'Activo' : 'Inactivo'}
                </span>
            </td>
            <td>
                <button onclick="verProcesos('${device.ip}')" class="btn-mini">⚙️</button>
            </td>
        </tr>
    `).join('');
}

function formatUsage(value) {
    const percentage = Math.round(value || 0);
    const barClass = percentage > 85 ? 'high' : percentage > 60 ? 'medium' : '';
    return `
        <div class="usage-container" style="display:flex; align-items:center; gap:5px;">
            <span style="min-width:30px">${percentage}%</span>
            <div class="usage-bar" style="width:50px; background:#334155; height:6px; border-radius:3px; overflow:hidden;">
                <div class="usage-fill ${barClass}" style="width:${percentage}%; height:100%; background:${percentage > 85 ? '#ef4444' : '#3b82f6'}"></div>
            </div>
        </div>
    `;
}

function verProcesos(ip) {
    window.location.href = `/procesos?ip=${ip}`;
}

async function loadNetworkStats() {
    try {
        const response = await fetch(`${API_URL}/api/network-stats`);
        const stats = await response.json();
        document.getElementById('bandwidth').textContent = `${stats.bandwidth_usage || 0} Mbps`;
    } catch (error) {
        console.error('Error stats:', error);
    }
}

async function scanNow() {
    const btn = document.getElementById('scanBtn');
    btn.disabled = true;
    btn.textContent = '⏳...';
    await fetch(`${API_URL}/api/scan-now`, { method: 'POST' });
    loadDevices();
    btn.disabled = false;
    btn.textContent = '🔄 Escanear Ahora';
}

async function exportExcel() {
    const response = await fetch(`${API_URL}/api/export-excel`);
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `Reporte_Red.xlsx`;
    a.click();
}