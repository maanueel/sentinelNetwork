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
    global devices_data
    while True:
        temp_devices = scanner.scan_network() # Escaneo rápido
        
        for ip, info in temp_devices.items():
            if info['is_reachable'] and ip != local_ip:
                # Si esto tarda mucho, la web verá 'temp_devices' vacío si no tenemos cuidado
                extra = monitor.get_remote_metrics(ip)
                info.update(extra)
        
        # SOLO ACTUALIZAMOS LA VARIABLE GLOBAL AL FINAL DEL CICLO
        devices_data = temp_devices 
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