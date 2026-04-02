import nmap
import socket
import psutil
import netifaces
from scapy.all import ARP, Ether, srp
import subprocess
import re

class NetworkScanner:
    def __init__(self):
        self.nm = nmap.PortScanner()
        
    def get_local_network(self):
        """Obtener rango de red local"""
        try:
            gateways = netifaces.gateways()
            default_gateway = gateways['default'][netifaces.AF_INET]
            interface = default_gateway[1]
            addrs = netifaces.ifaddresses(interface)
            ip_info = addrs[netifaces.AF_INET][0]
            ip = ip_info['addr']
            netmask = ip_info['netmask']
            
            # Calcular red CIDR
            network = self._calculate_network(ip, netmask)
            return network
        except:
            return "192.168.1.0/24"  # Default fallback
    
    def _calculate_network(self, ip, netmask):
        """Calcular red en formato CIDR"""
        ip_parts = [int(x) for x in ip.split('.')]
        mask_parts = [int(x) for x in netmask.split('.')]
        network_parts = [ip_parts[i] & mask_parts[i] for i in range(4)]
        cidr = sum([bin(x).count('1') for x in mask_parts])
        return f"{'.'.join(map(str, network_parts))}/{cidr}"
    
    def scan_network(self):
        """Escanear todos los dispositivos en la red"""
        devices = {}
        network = self.get_local_network()
        
        print(f"Escaneando red: {network}")
        
        try:
            # Escaneo rápido con ARP
            arp_devices = self._arp_scan(network)
            
            # Enriquecer con información adicional
            for ip, mac in arp_devices.items():
                device_info = {
                    'ip': ip,
                    'mac': mac,
                    'hostname': self._get_hostname(ip),
                    'vendor': self._get_vendor(mac),
                    'model': 'Desconocido',
                    'cpu_usage': 0,
                    'ram_usage': 0,
                    'disk_usage': 0,
                    'network_usage': 0,
                    'is_reachable': True
                }
                
                # Si es el host local, obtener métricas reales
                if self._is_local_ip(ip):
                    device_info.update(self._get_local_metrics())
                
                devices[ip] = device_info
        
        except Exception as e:
            print(f"Error en escaneo: {e}")
        
        return devices
    
    def _arp_scan(self, network):
        """Escaneo ARP rápido"""
        devices = {}
        try:
            arp = ARP(pdst=network)
            ether = Ether(dst="ff:ff:ff:ff:ff:ff")
            packet = ether/arp
            result = srp(packet, timeout=3, verbose=0)[0]
            
            for sent, received in result:
                devices[received.psrc] = received.hwsrc
        except Exception as e:
            print(f"Error en ARP scan: {e}")
        
        return devices
    
    def _get_hostname(self, ip):
        """Obtener nombre del host"""
        try:
            return socket.gethostbyaddr(ip)[0]
        except:
            return "Desconocido"
    
    def _get_vendor(self, mac):
        """Obtener fabricante del dispositivo por MAC"""
        # Simplificado - podrías usar una API o base de datos OUI
        mac_prefix = mac[:8].upper().replace(':', '')
        vendors = {
            '00:50:56': 'VMware',
            '00:0C:29': 'VMware',
            '00:1A:A0': 'Dell',
            'B8:27:EB': 'Raspberry Pi',
            '28:C6:3F': 'Apple',
            'DC:A6:32': 'Raspberry Pi',
        }
        
        for prefix, vendor in vendors.items():
            if mac.upper().startswith(prefix.replace(':', '')):
                return vendor
        
        return "Desconocido"
    
    def _is_local_ip(self, ip):
        """Verificar si la IP es del host local"""
        try:
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            return ip == local_ip
        except:
            return False
    
    def _get_local_metrics(self):
        """Obtener métricas del sistema local"""
        return {
            'cpu_usage': psutil.cpu_percent(interval=1),
            'ram_usage': psutil.virtual_memory().percent,
            'disk_usage': psutil.disk_usage('/').percent,
            'network_usage': self._get_network_usage()
        }
    
    def _get_network_usage(self):
        """Obtener uso de red en Mbps"""
        try:
            net_io = psutil.net_io_counters()
            return (net_io.bytes_sent + net_io.bytes_recv) / 1024 / 1024
        except:
            return 0