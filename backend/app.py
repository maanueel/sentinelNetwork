import threading
import time
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from network_scanner_simple import NetworkScanner
from device_monitor import DeviceMonitor

app = Flask(__name__, static_folder='../frontend', static_url_path='')
CORS(app)

# Globales inicializadas
scanner = NetworkScanner()
monitor = DeviceMonitor()
devices_data = {}
network_stats = {'bandwidth_usage': 0, 'is_saturated': False, 'total_devices': 0, 'active_devices': 0}

def background_monitoring():
    global devices_data, network_stats
    local_ip = scanner.get_local_ip()
    print(f"Iniciando monitoreo. IP Local: {local_ip}")

    while True:
        try:
            # 1. Escaneo ARP
            new_devices = scanner.scan_network()
            
            # 2. SNMP y Métricas locales
            for ip, info in new_devices.items():
                if ip == local_ip:
                    info.update(scanner._get_local_metrics())
                elif info['is_reachable']:
                    # Intentar SNMP
                    remote = monitor.get_remote_metrics(ip)
                    info.update(remote)
            
            # 3. Guardar resultados
            devices_data = new_devices
            network_stats = monitor.get_network_stats(devices_data)
            print(f"Ciclo completado. Dispositivos: {len(devices_data)}")
            
        except Exception as e:
            print(f"Error en bucle: {e}")
        
        time.sleep(30)

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/api/devices')
def get_devices():
    return jsonify({'devices': list(devices_data.values()), 'total': len(devices_data)})

@app.route('/api/network-stats')
def get_stats():
    return jsonify(network_stats)

if __name__ == '__main__':
    # Lanzar el hilo
    t = threading.Thread(target=background_monitoring, daemon=True)
    t.start()
    # Ejecutar Flask
    app.run(host='0.0.0.0', port=5000, debug=False)