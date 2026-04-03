import psutil
import time
from pysnmp.hlapi import *

class DeviceMonitor:
    def __init__(self):
        self.community = 'public'
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
        
        # 1. CPU (OID Estándar)
        cpu = self._snmp_get(ip, '1.3.6.1.2.1.25.3.3.1.2.1')
        if cpu: metrics['cpu_usage'] = float(cpu)

        # 2. RAM (Física - Índice 3 según tu snmpwalk)
        u_ram = self._snmp_get(ip, '1.3.6.1.2.1.25.2.3.1.4.3')
        t_ram = self._snmp_get(ip, '1.3.6.1.2.1.25.2.3.1.5.3')
        s_ram = self._snmp_get(ip, '1.3.6.1.2.1.25.2.3.1.6.3')
        if t_ram and s_ram and float(t_ram) > 0:
            metrics['ram_usage'] = round((float(s_ram) / float(t_ram)) * 100, 2)

        # 3. DISCO C: (Índice 1 según tu snmpwalk)
        u_disk = self._snmp_get(ip, '1.3.6.1.2.1.25.2.3.1.4.1')
        t_disk = self._snmp_get(ip, '1.3.6.1.2.1.25.2.3.1.5.1')
        s_disk = self._snmp_get(ip, '1.3.6.1.2.1.25.2.3.1.6.1')
        if t_disk and s_disk and float(t_disk) > 0:
            metrics['disk_usage'] = round((float(s_disk) / float(t_disk)) * 100, 2)

        # 4. RED (Cálculo de velocidad MBps)
        # Probamos con el índice 10 que es común en Ethernet/Wi-Fi de Windows
        oid_net = '1.3.6.1.2.1.2.2.1.10.10' 
        n1 = self._snmp_get(ip, oid_net)
        time.sleep(1) # Pausa para medir el delta
        n2 = self._snmp_get(ip, oid_net)
        
        if n1 and n2:
            diff = float(n2) - float(n1)
            # De bytes a Megabytes: (diff / 1024 / 1024)
            metrics['network_usage'] = round(diff / (1024 * 1024), 2)

        return metrics