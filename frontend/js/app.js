const API_URL = `http://${window.location.hostname}:5000`;

document.addEventListener('DOMContentLoaded', () => {
    loadDevices();
    
    // Auto-refresh cada 15 segundos para datos de red más precisos
    setInterval(loadDevices, 15000);
    
    document.getElementById('scanBtn').addEventListener('click', scanNow);
    document.getElementById('exportBtn').addEventListener('click', exportExcel);
});

async function loadDevices() {
    try {
        const response = await fetch(`${API_URL}/api/devices`);
        const data = await response.json();
        
        displayDevices(data.devices);
        updateDashboardStats(data.devices); // <--- Llenar tarjetas superiores
        
    } catch (error) {
        console.error('Error cargando dispositivos:', error);
    }
}

function updateDashboardStats(devices) {
    let totalBandwidth = 0;
    let topConsumer = { name: '---', usage: 0 };

    devices.forEach(device => {
        const usage = parseFloat(device.network_usage) || 0;
        totalBandwidth += usage;

        if (usage > topConsumer.usage) {
            topConsumer = { name: device.hostname || device.ip, usage: usage };
        }
    });

    // Actualizar elementos en el HTML (asegúrate que los IDs coincidan)
    if (document.getElementById('deviceCount')) 
        document.getElementById('deviceCount').textContent = devices.length;
    
    if (document.getElementById('bandwidth')) 
        document.getElementById('bandwidth').textContent = `${totalBandwidth.toFixed(2)} Mbps`;
    
    if (document.getElementById('topConsumer')) 
        document.getElementById('topConsumer').textContent = topConsumer.usage > 0 
            ? `${topConsumer.name} (${topConsumer.usage.toFixed(2)} Mbps)` 
            : '---';
}

function displayDevices(devices) {
    const tbody = document.getElementById('devicesBody');
    if (!tbody || !devices) return;
    
    tbody.innerHTML = devices.map(device => `
        <tr>
            <td>${device.ip}</td>
            <td><code>${device.mac}</code></td>
            <td>${device.hostname || '---'}</td>
            <td>${device.vendor || '---'}</td>
            <td>${formatUsage(device.cpu_usage)}</td>
            <td>${formatUsage(device.ram_usage)}</td>
            <td>${formatUsage(device.disk_usage)}</td>
            <td style="color: #10b981; font-weight: bold;">${(device.network_usage || 0).toFixed(2)} Mbps</td>
            <td>
                <span class="badge ${device.is_reachable ? 'badge-success' : 'badge-danger'}">
                    ${device.is_reachable ? 'Activo' : 'Inactivo'}
                </span>
            </td>
            <td>
                <button onclick="verProcesos('${device.ip}')" class="btn-mini" title="Ver Detalles">⚙️</button>
            </td>
        </tr>
    `).join('');
}

function formatUsage(value) {
    const percentage = Math.round(value || 0);
    const barColor = percentage > 85 ? '#ef4444' : percentage > 60 ? '#f59e0b' : '#3b82f6';
    return `
        <div class="usage-container" style="display:flex; align-items:center; gap:8px;">
            <span style="min-width:32px; font-size: 0.85rem;">${percentage}%</span>
            <div class="usage-bar" style="width:50px; background:#334155; height:6px; border-radius:3px; overflow:hidden;">
                <div class="usage-fill" style="width:${percentage}%; height:100%; background:${barColor}; transition: width 0.5s ease;"></div>
            </div>
        </div>
    `;
}

function verProcesos(ip) {
    window.location.href = `/procesos?ip=${ip}`;
}

async function scanNow() {
    const btn = document.getElementById('scanBtn');
    btn.disabled = true;
    btn.textContent = '⏳ Escaneando...';
    try {
        await fetch(`${API_URL}/api/scan-now`, { method: 'POST' });
        await loadDevices();
    } finally {
        btn.disabled = false;
        btn.textContent = '🔄 Escanear Ahora';
    }
}

async function exportExcel() {
    try {
        const response = await fetch(`${API_URL}/api/export-excel`);
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `Reporte_Red_Sentinel_${new Date().toLocaleDateString()}.xlsx`;
        a.click();
    } catch (error) { alert('Error al exportar'); }
}