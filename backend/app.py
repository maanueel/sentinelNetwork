from flask import Flask, jsonify, send_file, send_from_directory
from flask_cors import CORS
from network_scanner_simple import NetworkScanner
from device_monitor import DeviceMonitor
from excel_export import ExcelExporter
import threading
import time
import os

# Configurar rutas
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(os.path.dirname(BASE_DIR), 'frontend')

app = Flask(__name__, 
            static_folder=FRONTEND_DIR,
            static_url_path='')
CORS(app)

# Instancias globales
scanner = NetworkScanner()
monitor = DeviceMonitor()
devices_data = {}
network_stats = {
    'bandwidth_usage': 0,
    'is_saturated': False,
    'top_consumer': None
}

def background_monitoring():
    """Monitoreo continuo en segundo plano"""
    global devices_data, network_stats
    while True:
        try:
            # Escanear red cada 30 segundos
            devices_data = scanner.scan_network()
            
            # Actualizar estadísticas de red
            network_stats = monitor.get_network_stats(devices_data)
            
            time.sleep(30)
        except Exception as e:
            print(f"Error en monitoreo: {e}")
            time.sleep(30)

# Ruta raíz - servir index.html
@app.route('/')
def index():
    return send_from_directory(FRONTEND_DIR, 'index.html')

# Servir archivos estáticos (CSS, JS)
@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory(FRONTEND_DIR, path)

@app.route('/api/devices', methods=['GET'])
def get_devices():
    """Obtener lista de dispositivos"""
    return jsonify({
        'devices': list(devices_data.values()),
        'total': len(devices_data)
    })

@app.route('/api/network-stats', methods=['GET'])
def get_network_stats():
    """Obtener estadísticas de red"""
    return jsonify(network_stats)

@app.route('/api/export-excel', methods=['GET'])
def export_excel():
    """Exportar datos a Excel"""
    try:
        exporter = ExcelExporter()
        filepath = exporter.create_report(devices_data, network_stats)
        return send_file(filepath, as_attachment=True)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/scan-now', methods=['POST'])
def scan_now():
    """Forzar escaneo inmediato"""
    global devices_data
    devices_data = scanner.scan_network()
    return jsonify({'status': 'success', 'devices': len(devices_data)})

if __name__ == '__main__':
    # Iniciar monitoreo en segundo plano
    monitor_thread = threading.Thread(target=background_monitoring, daemon=True)
    monitor_thread.start()
    
    print(f"Frontend directory: {FRONTEND_DIR}")
    print(f"Servidor iniciando en http://0.0.0.0:5000")
    
    # Iniciar servidor Flask
    app.run(host='0.0.0.0', port=5000, debug=False)