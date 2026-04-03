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
        return 'eth0'  # Fallback
    
    def scan_network(self):
        """Escanear red usando arp-scan"""
        devices = {}
        network = self.get_local_network()
        interface = self.get_network_interface()
        
        print(f"Escaneando red: {network} en interfaz {interface}")
        
        try:
            # Intentar con arp-scan primero (más rápido y efectivo)
            result = subprocess.run(
                ['sudo', 'arp-scan', '--interface', interface, '--localnet'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                for line in lines:
                    # Formato: IP    MAC    Vendor
                    parts = line.split('\t')
                    if len(parts) >= 2:
                        ip_match = re.match(r'(\d+\.\d+\.\d+\.\d+)', parts[0].strip())
                        if ip_match:
                            ip = ip_match.group(1)
                            mac = parts[1].strip() if len(parts) > 1 else 'Desconocido'
                            vendor = parts[2].strip() if len(parts) > 2 else 'Desconocido'
                            
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
                
                print(f"arp-scan encontró {len(devices)} dispositivos")
            else:
                # Si arp-scan falla, usar nmap como respaldo
                print("arp-scan falló, usando nmap...")
                devices = self._scan_with_nmap(network)
        
        except FileNotFoundError:
            # arp-scan no está instalado, usar nmap
            print("arp-scan no disponible, usando nmap...")
            devices = self._scan_with_nmap(network)
        
        except Exception as e:
            print(f"Error en escaneo: {e}")
            devices = self._scan_with_nmap(network)
        
        # Agregar el servidor local con métricas completas
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
        
        return devices
    
    def _scan_with_nmap(self, network):
        """Escaneo con nmap como respaldo"""
        devices = {}
        
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
            
            print(f"nmap encontró {len(devices)} dispositivos")
        
        except Exception as e:
            print(f"Error en nmap: {e}")
        
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
        """Mapeo básico de fabricantes por MAC"""
        if not mac or mac == 'Desconocido':
            return 'Desconocido'
            
        vendors = {
            '00:50:56': 'VMware',
            '00:0C:29': 'VMware',
            '00:1A:A0': 'Dell',
            '00:14:22': 'Dell',
            'B8:27:EB': 'Raspberry Pi',
            'DC:A6:32': 'Raspberry Pi',
            'E4:5F:01': 'Raspberry Pi',
            '28:C6:3F': 'Apple',
            'F0:18:98': 'Apple',
            '08:00:27': 'VirtualBox',
            '52:54:00': 'QEMU/KVM',
            '00:15:5D': 'Microsoft Hyper-V',
            '00:1B:21': 'Intel',
            '00:1E:68': 'Cisco',
            'D8:BB:C1': 'TP-Link',
            'E8:94:F6': 'TP-Link',
            '50:C7:BF': 'TP-Link',
        }
        
        mac_upper = mac.upper().replace(':', '')
        for prefix, vendor in vendors.items():
            if mac_upper.startswith(prefix.replace(':', '')):
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