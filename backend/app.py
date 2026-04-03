import threading
import time
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from network_scanner_simple import NetworkScanner
from device_monitor import DeviceMonitor

app = Flask(__name__, static_folder='../frontend', static_url_path='')
CORS(app)

scanner = NetworkScanner()
monitor = DeviceMonitor()
devices_data = {}
network_stats = {'bandwidth_usage': 0, 'is_saturated': False, 'total_devices': 0, 'active_devices': 0, 'top_consumer': 'Ninguno'}

def background_monitoring():
    global devices_data, network_stats
    local_ip = scanner.get_local_ip()
    while True:
        try:
            print("--- Iniciando ciclo de monitoreo ---")
            new_devices = scanner.scan_network()
            for ip, info in new_devices.items():
                if ip == local_ip:
                    info.update(scanner._get_local_metrics())
                elif info.get('is_reachable'):
                    info.update(monitor.get_remote_metrics(ip))
            
            devices_data = new_devices
            network_stats = monitor.get_network_stats(devices_data)
            print("--- Ciclo completado con éxito ---")
        except Exception as e:
            print(f"Error en hilo: {e}")
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

@app.route('/api/scan-now', methods=['GET', 'POST'])
def scan_now():
    # En una versión real aquí dispararías el hilo, por ahora solo confirmamos
    return jsonify({'status': 'success', 'message': 'Escaneo solicitado'})

@app.route('/api/processes/<ip>')
def get_device_processes(ip):
    data = monitor.get_process_details(ip)
    return jsonify(data)

if __name__ == '__main__':
    t = threading.Thread(target=background_monitoring, daemon=True)
    t.start()
    app.run(host='0.0.0.0', port=5000)