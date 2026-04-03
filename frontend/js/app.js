const API_URL = 'http://192.168.1.24:5000';
let refreshInterval;

document.addEventListener('DOMContentLoaded', () => {
    loadDevices();
    loadNetworkStats();
    
    // Auto-refresh cada 30 segundos
    refreshInterval = setInterval(() => {
        loadDevices();
        loadNetworkStats();
    }, 30000);
    
    // Event listeners
    document.getElementById('scanBtn').addEventListener('click', scanNow);
    document.getElementById('exportBtn').addEventListener('click', exportExcel);
    
    // El botón de la cabecera por defecto abre el servidor local o el equipo principal
    const procBtn = document.getElementById('processBtn');
    if(procBtn) {
        procBtn.addEventListener('click', () => verProcesos('192.168.1.24'));
    }
});

async function loadDevices() {
    try {
        const response = await fetch(`${API_URL}/api/devices`);
        const data = await response.json();
        
        displayDevices(data.devices);
        document.getElementById('deviceCount').textContent = data.devices.length;
    } catch (error) {
        console.error('Error cargando dispositivos:', error);
        showError('No se pudo conectar con el servidor');
    }
}

async function loadNetworkStats() {
    try {
        const response = await fetch(`${API_URL}/api/network-stats`);
        const stats = await response.json();
        displayNetworkStats(stats);
    } catch (error) {
        console.error('Error cargando estadísticas:', error);
    }
}

function displayDevices(devices) {
    const tbody = document.getElementById('devicesBody');
    
    if (!devices || devices.length === 0) {
        tbody.innerHTML = '<tr><td colspan="10" class="loading">No se encontraron dispositivos</td></tr>';
        return;
    }
    
    tbody.innerHTML = devices.map(device => `
        <tr>
            <td>${device.ip}</td>
            <td><code>${device.mac}</code></td>
            <td>${device.hostname || 'Desconocido'}</td>
            <td>${device.vendor || 'Genérico'}</td>
            <td>${formatUsage(device.cpu_usage || 0)}</td>
            <td>${formatUsage(device.ram_usage || 0)}</td>
            <td>${formatUsage(device.disk_usage || 0)}</td>
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
    const percentage = Math.round(value);
    const barClass = percentage > 80 ? 'high' : '';
    return `
        <div class="usage-container">
            <span>${percentage}%</span>
            <div class="usage-bar">
                <div class="usage-fill ${barClass}" style="width: ${percentage}%"></div>
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
        setTimeout(() => {
            loadDevices();
            loadNetworkStats();
        }, 2000);
    } catch (error) {
        showError('Error al escanear');
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
        a.download = `reporte_red_${new Date().getTime()}.xlsx`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
    } catch (error) {
        showError('Error al exportar');
    }
}

function displayNetworkStats(stats) {
    document.getElementById('bandwidth').textContent = `${stats.bandwidth_usage || 0} Mbps`;
    const saturationCard = document.getElementById('saturationCard');
    const saturationStatus = document.getElementById('saturationStatus');
    
    if (stats.is_saturated) {
        saturationStatus.textContent = '⚠️ Saturada';
        saturationCard.classList.add('alert');
    } else {
        saturationStatus.textContent = '✓ Normal';
        saturationCard.classList.remove('alert');
    }
}

function showError(message) {
    console.error(message);
}