import subprocess
import re
import socket
import psutil

class NetworkScanner:
    def __init__(self):
        pass
        
    def get_local_network(self):
        """Obtener rango de red local"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            
            network_base = '.'.join(local_ip.split('.')[:-1])
            return f"{network_base}.0/24"
        except:
            return "192.168.1.0/24"
    
    def scan_network(self):
        """Escanear red usando nmap"""
        devices = {}
        network = self.get_local_network()
        
        print(f"Escaneando red: {network}")
        
        try:
            result = subprocess.run(
                ['sudo', 'nmap', '-sn', network],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            lines = result.stdout.split('\n')
            current_ip = None
            
            for line in lines:
                ip_match = re.search(r'Nmap scan report for .*\((\d+\.\d+\.\d+\.\d+)\)', line)
                if not ip_match:
                    ip_match = re.search(r'Nmap scan report for (\d+\.\d+\.\d+\.\d+)', line)
                
                if ip_match:
                    current_ip = ip_match.group(1)
                    devices[current_ip] = {
                        'ip': current_ip,
                        'mac': 'Desconocido',
                        'hostname': self._get_hostname(current_ip),
                        'vendor': 'Desconocido',
                        'model': 'Desconocido',
                        'cpu_usage': 0,
                        'ram_usage': 0,
                        'disk_usage': 0,
                        'network_usage': 0,
                        'is_reachable': True
                    }
                
                if current_ip:
                    mac_match = re.search(r'MAC Address: ([0-9A-F:]{17})', line, re.IGNORECASE)
                    if mac_match:
                        mac = mac_match.group(1)
                        devices[current_ip]['mac'] = mac
                        devices[current_ip]['vendor'] = self._get_vendor(mac)
            
            local_ip = self.get_local_ip()
            if local_ip in devices:
                devices[local_ip].update(self._get_local_metrics())
            elif local_ip:
                devices[local_ip] = {
                    'ip': local_ip,
                    'mac': 'Local',
                    'hostname': socket.gethostname(),
                    'vendor': 'Local',
                    'model': 'Server',
                    'is_reachable': True
                }
                devices[local_ip].update(self._get_local_metrics())
        
        except Exception as e:
            print(f"Error en escaneo: {e}")
            try:
                local_ip = self.get_local_ip()
                devices[local_ip] = {
                    'ip': local_ip,
                    'mac': 'Local',
                    'hostname': socket.gethostname(),
                    'vendor': 'Local',
                    'model': 'Server',
                    'is_reachable': True
                }
                devices[local_ip].update(self._get_local_metrics())
            except:
                pass
        
        return devices
    
    def get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except:
            return "127.0.0.1"
    
    def _get_hostname(self, ip):
        try:
            return socket.gethostbyaddr(ip)[0]
        except:
            return "Desconocido"
    
    def _get_vendor(self, mac):
        vendors = {
            '00:50:56': 'VMware',
            '00:0C:29': 'VMware',
            '00:1A:A0': 'Dell',
            'B8:27:EB': 'Raspberry Pi',
            '28:C6:3F': 'Apple',
            'DC:A6:32': 'Raspberry Pi',
            '08:00:27': 'VirtualBox',
        }
        
        for prefix, vendor in vendors.items():
            if mac.upper().startswith(prefix.replace(':', '')):
                return vendor
        
        return "Desconocido"
    
    def _get_local_metrics(self):
        try:
            return {
                'cpu_usage': round(psutil.cpu_percent(interval=1), 2),
                'ram_usage': round(psutil.virtual_memory().percent, 2),
                'disk_usage': round(psutil.disk_usage('/').percent, 2),
                'network_usage': round((psutil.net_io_counters().bytes_sent + 
                                       psutil.net_io_counters().bytes_recv) / 1024 / 1024, 2)
            }
        except:
            return {
                'cpu_usage': 0,
                'ram_usage': 0,
                'disk_usage': 0,
                'network_usage': 0
            }