import subprocess
import socket
import psutil
import re

class NetworkScanner:
    def get_local_ip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
        except:
            ip = '127.0.0.1'
        finally:
            s.close()
        return ip

    def scan_network(self):
        devices = {}
        # Despertar dispositivos con fping (ignorar errores si no está instalado)
        try:
            subprocess.run(['fping', '-g', '192.168.1.0/24', '-a', '-q'], capture_output=True, timeout=5)
        except:
            pass
        
        try:
            # Usamos la ruta absoluta de arp-scan
            res = subprocess.run(['sudo', '/usr/sbin/arp-scan', '--localnet', '--ignoredups'], 
                               capture_output=True, text=True, timeout=10)
            
            if res.returncode == 0:
                for line in res.stdout.split('\n'):
                    parts = line.split()
                    if len(parts) >= 2 and re.match(r'^\d+\.\d+\.\d+\.\d+$', parts[0]):
                        ip, mac = parts[0], parts[1]
                        vendor = ' '.join(parts[2:]) if len(parts) > 2 else "Desconocido"
                        
                        devices[ip] = {
                            'ip': ip, 'mac': mac, 'vendor': vendor,
                            'hostname': self._get_hostname(ip),
                            'cpu_usage': 0, 'ram_usage': 0, 'disk_usage': 0,
                            'network_usage': 0, 'is_reachable': True
                        }
        except Exception as e:
            print(f"Error en escaneo ARP: {e}")
            
        # Si no detecta nada, al menos agregamos el local para que la tabla no esté vacía
        local_ip = self.get_local_ip()
        if local_ip not in devices:
            devices[local_ip] = {
                'ip': local_ip, 'mac': 'Local', 'vendor': 'Propio',
                'hostname': socket.gethostname(), 'is_reachable': True,
                'cpu_usage': 0, 'ram_usage': 0, 'disk_usage': 0, 'network_usage': 0
            }
        return devices

    def _get_hostname(self, ip):
        try:
            return socket.gethostbyaddr(ip)[0]
        except:
            return "Desconocido"

    def _get_local_metrics(self):
        try:
            return {
                'cpu_usage': psutil.cpu_percent(interval=0.1),
                'ram_usage': psutil.virtual_memory().percent,
                'disk_usage': psutil.disk_usage('/').percent,
                'network_usage': round((psutil.net_io_counters().bytes_sent + psutil.net_io_counters().bytes_recv) / (1024*1024), 2)
            }
        except:
            return {'cpu_usage': 0, 'ram_usage': 0, 'disk_usage': 0, 'network_usage': 0}