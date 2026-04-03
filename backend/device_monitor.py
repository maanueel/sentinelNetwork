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
        
        # CPU
        cpu = self._snmp_get(ip, '1.3.6.1.2.1.25.3.3.1.2.1')
        if cpu: metrics['cpu_usage'] = float(cpu)

        # RAM (Índice .3 según tu snmpwalk)
        t_ram = self._snmp_get(ip, '1.3.6.1.2.1.25.2.3.1.5.3')
        s_ram = self._snmp_get(ip, '1.3.6.1.2.1.25.2.3.1.6.3')
        if t_ram and s_ram and float(t_ram) > 0:
            metrics['ram_usage'] = round((float(s_ram) / float(t_ram)) * 100, 2)

        # DISCO (Índice .1 según tu snmpwalk)
        t_disk = self._snmp_get(ip, '1.3.6.1.2.1.25.2.3.1.5.1')
        s_disk = self._snmp_get(ip, '1.3.6.1.2.1.25.2.3.1.6.1')
        if t_disk and s_disk and float(t_disk) > 0:
            metrics['disk_usage'] = round((float(s_disk) / float(t_disk)) * 100, 2)

        return metrics

    def get_network_stats(self, devices):
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