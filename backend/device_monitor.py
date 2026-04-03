import subprocess
import psutil
import time

class DeviceMonitor:
    def __init__(self):
        self.community = 'public'
        self.previous_net_io = None

    def _raw_snmp_get(self, ip, oid):
        """Versión mejorada para capturar tanto números como texto (STRING)"""
        try:
            res = subprocess.run(
                ['snmpget', '-v', '2c', '-c', self.community, ip, oid],
                capture_output=True, text=True, timeout=1.5
            )
            if res.returncode == 0:
                if "INTEGER:" in res.stdout:
                    return res.stdout.split("INTEGER:")[1].strip()
                if "STRING:" in res.stdout:
                    # Limpia las comillas del texto
                    return res.stdout.split("STRING:")[1].strip().replace('"', '')
        except: pass
        return None

    def get_remote_metrics(self, ip):
        metrics = {'cpu_usage': 0, 'ram_usage': 0, 'disk_usage': 0, 'network_usage': 0}
        
        # CPU Usage
        cpu = self._raw_snmp_get(ip, '1.3.6.1.2.1.25.3.3.1.2.1')
        if cpu: metrics['cpu_usage'] = float(cpu)
        
        # RAM (Índice .3)
        t_ram = self._raw_snmp_get(ip, '1.3.6.1.2.1.25.2.3.1.5.3')
        s_ram = self._raw_snmp_get(ip, '1.3.6.1.2.1.25.2.3.1.6.3')
        if t_ram and s_ram:
            metrics['ram_usage'] = round((float(s_ram) / float(t_ram)) * 100, 2)

        # DISCO (Índice .1)
        t_disk = self._raw_snmp_get(ip, '1.3.6.1.2.1.25.2.3.1.5.1')
        s_disk = self._raw_snmp_get(ip, '1.3.6.1.2.1.25.2.3.1.6.1')
        if t_disk and s_disk:
            metrics['disk_usage'] = round((float(s_disk) / float(t_disk)) * 100, 2)

        return metrics

    def get_process_details(self, ip):
        """Nueva función para el botón de Procesos"""
        total_ram_units = self._raw_snmp_get(ip, '1.3.6.1.2.1.25.2.3.1.5.3') or "0"
        
        details = {
            'hostname': self._raw_snmp_get(ip, '1.3.6.1.2.1.1.5.0') or "Desconocido",
            'cpu_model': self._raw_snmp_get(ip, '1.3.6.1.2.1.25.3.2.1.3.1') or "Intel/AMD Genérico",
            'total_ram': f"{round(float(total_ram_units) * 65536 / (1024**3), 2)} GB",
            'processes': []
        }
        
        # snmpwalk para obtener los nombres de procesos corriendo
        try:
            res = subprocess.run(
                ['snmpwalk', '-v', '2c', '-c', self.community, ip, '1.3.6.1.2.1.25.4.2.1.2'],
                capture_output=True, text=True, timeout=2
            )
            if res.returncode == 0:
                lines = res.stdout.strip().split('\n')[:10] # Top 10
                details['processes'] = [l.split('STRING: ')[1].replace('"', '') for l in lines if 'STRING:' in l]
        except: pass
        return details