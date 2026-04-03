import psutil
from pysnmp.hlapi import *

class DeviceMonitor:
    def __init__(self):
        self.community = 'public'
        self.bandwidth_threshold = 80
        self.previous_net_io = None

    def _snmp_get(self, ip, oid):
        """Consulta un OID específico vía SNMP v2c"""
        try:
            errorIndication, errorStatus, errorIndex, varBinds = next(
                getCmd(SnmpEngine(),
                       CommunityData(self.community),
                       UdpTransportTarget((ip, 161), timeout=1, retries=0),
                       ContextData(),
                       ObjectType(ObjectIdentity(oid)))
            )
            if not errorIndication and not errorStatus:
                return varBinds[0][1]
            return None
        except Exception:
            return None

    def get_remote_metrics(self, ip):
        """Obtiene CPU y RAM de dispositivos remotos"""
        metrics = {'cpu_usage': 0, 'ram_usage': 0}
        
        # OID Carga de CPU (Host Resources)
        cpu = self._snmp_get(ip, '1.3.6.1.2.1.25.3.3.1.2.1')
        if cpu is not None:
            metrics['cpu_usage'] = float(cpu)

        # OIDs para cálculo de RAM (Storage Table)
        units = self._snmp_get(ip, '1.3.6.1.2.1.25.2.3.1.4.1')
        total = self._snmp_get(ip, '1.3.6.1.2.1.25.2.3.1.5.1')
        used = self._snmp_get(ip, '1.3.6.1.2.1.25.2.3.1.6.1')

        if units and total and used:
            # Cálculo de porcentaje: (Usado / Total) * 100
            metrics['ram_usage'] = round((float(used) / float(total)) * 100, 2)
            
        return metrics

    def get_network_stats(self, devices):
        """Calcula estadísticas globales de la red"""
        stats = {
            'bandwidth_usage': 0,
            'is_saturated': False,
            'top_consumer': None,
            'total_devices': len(devices),
            'active_devices': sum(1 for d in devices.values() if d.get('is_reachable'))
        }

        current_net_io = psutil.net_io_counters()
        if self.previous_net_io:
            diff = (current_net_io.bytes_sent + current_net_io.bytes_recv) - \
                   (self.previous_net_io.bytes_sent + self.previous_net_io.bytes_recv)
            bandwidth_mbps = (diff * 8) / (1024 * 1024)
            stats['bandwidth_usage'] = round(bandwidth_mbps, 2)
            stats['is_saturated'] = bandwidth_mbps > self.bandwidth_threshold

        self.previous_net_io = current_net_io
        
        # Encontrar el mayor consumidor (basado en métricas obtenidas)
        max_val = -1
        for ip, d in devices.items():
            total = d.get('cpu_usage', 0) + d.get('ram_usage', 0)
            if total > max_val:
                max_val = total
                stats['top_consumer'] = {'ip': ip, 'hostname': d.get('hostname')}
                
        return stats