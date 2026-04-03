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
        # Refrescamos tabla ARP con fping antes del escaneo
        subprocess.run(['fping', '-g', '192.168.1.0/24', '-a', '-q'], capture_output=True)
        
        try:
            # IMPORTANTE: Ruta absoluta /usr/sbin/arp-scan
            res = subprocess.run(['sudo', '/usr/sbin/arp-scan', '--localnet', '--ignoredups'], 
                               capture_output=True, text=True)
            
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
            print(f"Error escaneo: {e}")
            
        return devices

    def _get_hostname(self, ip):
        try:
            return socket.gethostbyaddr(ip)[0]
        except:
            return "Desconocido"

    def _get_local_metrics(self):
        return {
            'cpu_usage': psutil.cpu_percent(),
            'ram_usage': psutil.virtual_memory().percent,
            'disk_usage': psutil.disk_usage('/').percent,
            'is_reachable': True
        }