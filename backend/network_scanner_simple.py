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
    
    def get_network_interface(self):
        """Obtener la interfaz de red principal"""
        try:
            result = subprocess.run(
                ['ip', 'route', 'get', '8.8.8.8'],
                capture_output=True,
                text=True
            )
            match = re.search(r'dev (\S+)', result.stdout)
            if match:
                return match.group(1)
        except:
            pass
        return 'eth0'
    
    def scan_network(self):
        """Escanear red usando arp-scan"""
        devices = {}
        network = self.get_local_network()
        interface = self.get_network_interface()
        
        print(f"\n=== Iniciando escaneo de red ===")
        print(f"Red: {network}")
        print(f"Interfaz: {interface}")
        
        try:
            interface = self.get_network_interface()
            result = subprocess.run(
                ['sudo', '/usr/sbin/arp-scan', '--localnet', '--ignoredups'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            print(f"Código de salida arp-scan: {result.returncode}")
            
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                
                for line in lines:
                    # Dividir por espacios/tabs
                    parts = line.split()
                    
                    # Verificar que tenga al menos IP y MAC
                    if len(parts) >= 2:
                        # Verificar si es una IP válida
                        if re.match(r'^\d+\.\d+\.\d+\.\d+$', parts[0]):
                            ip = parts[0]
                            mac = parts[1]
                            vendor = ' '.join(parts[2:]) if len(parts) > 2 else ''
                            
                            # Limpiar vendor
                            if '(Unknown' in vendor or 'locally administered' in vendor:
                                vendor = ''
                            
                            devices[ip] = {
                                'ip': ip,
                                'mac': mac,
                                'hostname': self._get_hostname(ip),
                                'vendor': vendor if vendor else self._get_vendor(mac),
                                'model': 'Desconocido',
                                'cpu_usage': 0,
                                'ram_usage': 0,
                                'disk_usage': 0,
                                'network_usage': 0,
                                'is_reachable': True
                            }
                            
                            print(f"  Encontrado: {ip} - {mac} - {vendor}")
                
                print(f"arp-scan encontró {len(devices)} dispositivos")
            
        except Exception as e:
            print(f"Error en arp-scan: {e}")
        
        # Agregar el servidor local
        local_ip = self.get_local_ip()
        if local_ip not in devices:
            devices[local_ip] = {
                'ip': local_ip,
                'mac': 'Local',
                'hostname': socket.gethostname(),
                'vendor': 'Local',
                'model': 'Server',
                'is_reachable': True
            }
        
        devices[local_ip].update(self._get_local_metrics())
        
        print(f"Total final: {len(devices)} dispositivos\n")
        
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
            hostname = socket.gethostbyaddr(ip)[0]
            return hostname
        except:
            return "Desconocido"
    
    def _get_vendor(self, mac):
        """Mapeo de fabricantes por MAC"""
        if not mac or mac == 'Desconocido':
            return 'Desconocido'
        
        mac_upper = mac.upper().replace(':', '')
        
        vendors = {
            '60109E': 'Huawei',
            'A8944A': 'Chongqing Fugui',
            '5A5ACB': 'Desconocido',
            'FEFD44': 'Desconocido',
            'D8C80C': 'Desconocido',
            '080027': 'VirtualBox',
            '00505': 'VMware',
            '000C29': 'VMware',
            '001AA0': 'Dell',
            'B827EB': 'Raspberry Pi',
            'DCA632': 'Raspberry Pi',
            'E45F01': 'Raspberry Pi',
            '28C63F': 'Apple',
            'F01898': 'Apple',
            '52540': 'QEMU',
            '00155D': 'Microsoft',
        }
        
        for prefix, vendor in vendors.items():
            if mac_upper.startswith(prefix):
                return vendor
        
        return 'Desconocido'
    
    def _get_local_metrics(self):
        try:
            return {
                'cpu_usage': round(psutil.cpu_percent(interval=0.5), 2),
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