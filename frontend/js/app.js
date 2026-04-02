const API_URL = window.location.origin.replace(':80', ':5000');

let refreshInterval;

// Inicializar
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
});

async function loadDevices() {
    try {
        const response = await fetch(`${API_URL}/api/devices`);
        const data = await response.json();
        
        displayDevices(data.devices);
        document.getElementById('deviceCount').textContent = data.total;
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
    
    if (devices.length === 0) {
        tbody.innerHTML = '<tr><td colspan="9" class="loading">No se encontraron dispositivos</td></tr>';
        return;
    }
    
    tbody.innerHTML = devices.map(device => `
        <tr>
            <td>${device.ip}</td>
            <td><code>${device.mac}</code></td>
            <td>${device.hostname}</td>
            <td>${device.vendor}</td>
            <td>${formatUsage(device.cpu_usage)}</td>
            <td>${formatUsage(device.ram_usage)}</td>
            <td>${formatUsage(device.disk_usage)}</td>
            <td>${device.network_usage.toFixed(2)} MB</td>
            <td>
                <span class="badge ${device.is_reachable ? 'badge-success' : 'badge-danger'}">
                    ${device.is_reachable ? 'Activo' : 'Inactivo'}
                </span>
            </td>
        </tr>
    `).join('');
}

function displayNetworkStats(stats) {
    // Ancho de banda
    document.getElementById('bandwidth').textContent = `${stats.bandwidth_usage} Mbps`;
    
    // Estado de saturación
    const saturationCard = document.getElementById('saturationCard');
    const saturationStatus = document.getElementById('saturationStatus');
    
    if (stats.is_saturated) {
        saturationStatus.textContent = '⚠️ Saturada';
        saturationCard.classList.add('alert');
    } else {
        saturationStatus.textContent = '✓ Normal';
        saturationCard.classList.remove('alert');
    }
    
    // Mayor consumidor
    if (stats.top_consumer) {
        const top = stats.top_consumer;
        document.getElementById('topConsumer').textContent = 
            `${top.hostname} (${top.ip})`;
    } else {
        document.getElementById('topConsumer').textContent = '-';
    }
}

function formatUsage(value) {
    const percentage = Math.round(value);
    const barClass = percentage > 80 ? 'high' : '';
    
    return `
        ${percentage}%
        <div class="usage-bar">
            <div class="usage-fill ${barClass}" style="width: ${percentage}%"></div>
        </div>
    `;
}

async function scanNow() {
    const btn = document.getElementById('scanBtn');
    btn.disabled = true;
    btn.textContent = '⏳ Escaneando...';
    
    try {
        await fetch(`${API_URL}/api/scan-now`, { method: 'POST' });
        await loadDevices();
        await loadNetworkStats();
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
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
    } catch (error) {
        showError('Error al exportar');
    }
}

function showError(message) {
    alert(message);
}
