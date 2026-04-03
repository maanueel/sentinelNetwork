import subprocess
import psutil

class DeviceMonitor:
    def __init__(self):
        self.community = 'public'
        self.previous_net_io = None

    def _raw_snmp_get(self, ip, oid):
        try:
            res = subprocess.run(
                ['snmpget', '-v', '2c', '-c', self.community, ip, oid],
                capture_output=True, text=True, timeout=1.5
            )
            if res.returncode == 0:
                if "INTEGER:" in res.stdout:
                    return res.stdout.split("INTEGER:")[1].strip()
                if "STRING:" in res.stdout:
                    return res.stdout.split("STRING:")[1].strip().replace('"', '')
        except: pass
        return None

    def get_remote_metrics(self, ip):
        metrics = {'cpu_usage': 0, 'ram_usage': 0, 'disk_usage': 0, 'network_usage': 0}
        
        # CPU: Carga total del sistema
        cpu = self._raw_snmp_get(ip, '1.3.6.1.2.1.25.3.3.1.2.1')
        if cpu: metrics['cpu_usage'] = float(cpu)
        
        # RAM: (Índice .3 según tus capturas)
        t_ram = self._raw_snmp_get(ip, '1.3.6.1.2.1.25.2.3.1.5.3')
        s_ram = self._raw_snmp_get(ip, '1.3.6.1.2.1.25.2.3.1.6.3')
        if t_ram and s_ram:
            metrics['ram_usage'] = round((float(s_ram) / float(t_ram)) * 100, 2)

        # RED: Tráfico de entrada en la interfaz principal (OID ifInOctets.10)
        net = self._raw_snmp_get(ip, '1.3.6.1.2.1.2.2.1.10.10')
        if net:
            metrics['network_usage'] = round(float(net) / (1024 * 1024), 2)

        return metrics

    def get_process_details(self, ip):
        t_ram_units = self._raw_snmp_get(ip, '1.3.6.1.2.1.25.2.3.1.5.3') or "0"
        details = {
            'hostname': self._raw_snmp_get(ip, '1.3.6.1.2.1.1.5.0') or ip,
            'cpu_model': self._raw_snmp_get(ip, '1.3.6.1.2.1.25.3.2.1.3.1') or "Procesador Remoto",
            'total_ram': f"{round(float(t_ram_units) * 65536 / (1024**3), 1)} GB" if t_ram_units != "0" else "N/A",
            'processes': []
        }
        try:
            res = subprocess.run(
                ['snmpwalk', '-v', '2c', '-c', self.community, ip, '1.3.6.1.2.1.25.4.2.1.2'],
                capture_output=True, text=True, timeout=2
            )
            if res.returncode == 0:
                lines = res.stdout.strip().split('\n')[:10]
                details['processes'] = [l.split('STRING: ')[1].replace('"', '') for l in lines if 'STRING:' in l]
        except: pass
        return details

    def get_network_stats(self, devices):
        stats = {'bandwidth_usage': 0, 'total_devices': len(devices)}
        curr_io = psutil.net_io_counters()
        if self.previous_net_io:
            diff = (curr_io.bytes_sent + curr_io.bytes_recv) - (self.previous_net_io.bytes_sent + self.previous_net_io.bytes_recv)
            stats['bandwidth_usage'] = round((diff * 8) / (1024 * 1024), 2)
        self.previous_net_io = curr_io
        return stats