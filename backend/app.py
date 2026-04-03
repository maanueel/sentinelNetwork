import threading
import time
import os
from flask import Flask, jsonify, send_file, send_from_directory
from flask_cors import CORS
from network_scanner_simple import NetworkScanner
from device_monitor import DeviceMonitor
from excel_export import ExcelExporter

app = Flask(__name__, static_folder='../frontend', static_url_path='')
CORS(app)

scanner = NetworkScanner()
monitor = DeviceMonitor()
devices_data = {}
network_stats = {}

def background_monitoring():
    global devices_data, network_stats
    local_ip = scanner.get_local_ip()
    
    while True:
        try:
            # 1. Escaneo de red (ARP)
            raw_devices = scanner.scan_network()
            
            # 2. Enriquecimiento SNMP para cada dispositivo encontrado
            for ip, info in raw_devices.items():
                if info['is_reachable'] and ip != local_ip:
                    # Intentamos obtener datos reales si SNMP está activo
                    remote_data = monitor.get_remote_metrics(ip)
                    info.update(remote_data)
                elif ip == local_ip:
                    # Datos locales del propio servidor
                    info.update(scanner._get_local_metrics())
            
            devices_data = raw_devices
            network_stats = monitor.get_network_stats(devices_data)
            
            print(f"Monitoreo actualizado: {len(devices_data)} dispositivos.")
            time.sleep(30)
        except Exception as e:
            print(f"Error en hilo de monitoreo: {e}")
            time.sleep(10)

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/api/devices')
def get_devices():
    return jsonify({'devices': list(devices_data.values()), 'total': len(devices_data)})

@app.route('/api/network-stats')
def get_stats():
    return jsonify(network_stats)

@app.route('/api/scan-now', methods=['POST'])
def scan_now():
    # Forzar ejecución inmediata del hilo (simplificado)
    return jsonify({'status': 'scanning_triggered'})

if __name__ == '__main__':
    t = threading.Thread(target=background_monitoring, daemon=True)
    t.start()
    app.run(host='0.0.0.0', port=5000)