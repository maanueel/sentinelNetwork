import psutil
import time
from pysnmp.hlapi import *

class DeviceMonitor:
    def __init__(self):
        self.community = 'public'
        self.bandwidth_threshold = 80
        self.previous_net_io = None

    def _snmp_get(self, ip, oid):
        try:
            iterator = getCmd(
                SnmpEngine(),
                CommunityData(self.community),
                UdpTransportTarget((ip, 161), timeout=1, retries=0),
                ContextData(),
                ObjectType(ObjectIdentity(oid))
            )
            errorIndication, errorStatus, errorIndex, varBinds = next(iterator)
            if not errorIndication and not errorStatus:
                return varBinds[0][1]
        except:
            pass
        return None

    def get_remote_metrics(self, ip):
        metrics = {'cpu_usage': 0, 'ram_usage': 0, 'disk_usage': 0, 'network_usage': 0}
        
        # 1. CPU (OID estándar de carga de procesador)
        cpu = self._snmp_get(ip, '1.3.6.1.2.1.25.3.3.1.2.1')
        if cpu: metrics['cpu_usage'] = float(cpu)

        # 2. RAM (Física - Según tu captura el índice es el .3)
        # OIDs: Unidades(.4.3), Tamaño Total(.5.3), Usado(.6.3)
        u_ram = self._snmp_get(ip, '1.3.6.1.2.1.25.2.3.1.4.3')
        t_ram = self._snmp_get(ip, '1.3.6.1.2.1.25.2.3.1.5.3')
        s_ram = self._snmp_get(ip, '1.3.6.1.2.1.25.2.3.1.6.3')
        if t_ram and s_ram and float(t_ram) > 0:
            metrics['ram_usage'] = round((float(s_ram) / float(t_ram)) * 100, 2)

        # 3. DISCO C: (Según tu captura el índice es el .1)
        # OIDs: Unidades(.4.1), Tamaño Total(.5.1), Usado(.6.1)
        u_disk = self._snmp_get(ip, '1.3.6.1.2.1.25.2.3.1.4.1')
        t_disk = self._snmp_get(ip, '1.3.6.1.2.1.25.2.3.1.5.1')
        s_disk = self._snmp_get(ip, '1.3.6.1.2.1.25.2.3.1.6.1')
        if t_disk and s_disk and float(t_disk) > 0:
            metrics['disk_usage'] = round((float(s_disk) / float(t_disk)) * 100, 2)

        # 4. RED (Cálculo de Delta - MB consumidos)
        # Usamos la interfaz 10 como prueba inicial (común en Win10/11)
        oid_net = '1.3.6.1.2.1.2.2.1.10.10' 
        n1 = self._snmp_get(ip, oid_net)
        if n1:
            # Esperamos un momento para ver si hay tráfico
            time.sleep(0.5) 
            n2 = self._snmp_get(ip, oid_net)
            if n2:
                diff = float(n2) - float(n1)
                metrics['network_usage'] = round(diff / (1024 * 1024), 2)

        return metrics

    def get_network_stats(self, devices):
        # Esta es la función que te faltaba y causaba el ERROR CRÍTICO
        stats = {
            'bandwidth_usage': 0,
            'is_saturated': False,
            'total_devices': len(devices),
            'active_devices': sum(1 for d in devices.values() if d.get('is_reachable')),
            'top_consumer': "-"
        }
        
        curr_io = psutil.net_io_counters()
        if self.previous_net_io:
            diff = (curr_io.bytes_sent + curr_io.bytes_recv) - \
                   (self.previous_net_io.bytes_sent + self.previous_net_io.bytes_recv)
            mbps = round((diff * 8) / (1024 * 1024), 2)
            stats['bandwidth_usage'] = mbps
            stats['is_saturated'] = mbps > self.bandwidth_threshold
        
        self.previous_net_io = curr_io
        return stats