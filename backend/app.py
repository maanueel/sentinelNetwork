import threading
import time
from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
from network_scanner_simple import NetworkScanner
from device_monitor import DeviceMonitor
import psutil

app = Flask(__name__, static_folder='../frontend', static_url_path='')
CORS(app)

scanner = NetworkScanner()
monitor = DeviceMonitor()
devices_data = {}
network_stats = {'bandwidth_usage': 0, 'total_devices': 0}

def background_monitoring():
    global devices_data, network_stats
    local_ip = scanner.get_local_ip()
    while True:
        try:
            new_devices = scanner.scan_network()
            for ip, info in new_devices.items():
                if ip == local_ip or "server" in info.get('hostname', '').lower():
                    info.update(scanner._get_local_metrics())
                elif info.get('is_reachable'):
                    info.update(monitor.get_remote_metrics(ip))
            devices_data = new_devices
            network_stats = monitor.get_network_stats(devices_data)
        except Exception as e:
            print(f"Error en monitoreo: {e}")
        time.sleep(30)

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/procesos')
def procesos_page():
    return send_from_directory(app.static_folder, 'procesos.html')

@app.route('/api/devices')
def get_devices():
    return jsonify({'devices': list(devices_data.values())})

@app.route('/api/processes/<ip>')
def get_processes(ip):
    local_ip = scanner.get_local_ip()
    # Si la IP es la local, usamos psutil
    if ip == local_ip or ip == '127.0.0.1':
        return jsonify({
            'hostname': 'Servidor Local (server1)',
            'cpu_model': 'Procesador del Sistema',
            'total_ram': f"{round(psutil.virtual_memory().total / (1024**3), 1)} GB",
            'processes': [p.info['name'] for p in psutil.process_iter(['name'])][:10]
        })
    # Si es remota, usamos SNMP
    return jsonify(monitor.get_process_details(ip))

if __name__ == '__main__':
    t = threading.Thread(target=background_monitoring, daemon=True)
    t.start()
    app.run(host='0.0.0.0', port=5000)