import subprocess
import psutil
import time

class DeviceMonitor:
    def __init__(self):
        self.community = 'public'
        self.previous_net_io = None

    def _raw_snmp_get(self, ip, oid):
        """Usa el comando del sistema para asegurar la compatibilidad"""
        try:
            # Ejecutamos snmpget directamente
            res = subprocess.run(
                ['snmpget', '-v', '2c', '-c', self.community, ip, oid],
                capture_output=True, text=True, timeout=2
            )
            if res.returncode == 0 and "INTEGER:" in res.stdout:
                # Extraemos solo el número final
                return int(res.stdout.split("INTEGER:")[1].strip())
        except:
            pass
        return None

    def get_remote_metrics(self, ip):
        metrics = {'cpu_usage': 0, 'ram_usage': 0, 'disk_usage': 0, 'network_usage': 0}
        
        # 1. CPU
        cpu = self._raw_snmp_get(ip, '1.3.6.1.2.1.25.3.3.1.2.1')
        if cpu is not None: metrics['cpu_usage'] = float(cpu)

        # 2. RAM (Índice .3 según tus capturas)
        total_ram = self._raw_snmp_get(ip, '1.3.6.1.2.1.25.2.3.1.5.3')
        used_ram = self._raw_snmp_get(ip, '1.3.6.1.2.1.25.2.3.1.6.3')
        if total_ram and used_ram:
            metrics['ram_usage'] = round((used_ram / total_ram) * 100, 2)

        # 3. DISCO C: (Índice .1 según tus capturas)
        total_disk = self._raw_snmp_get(ip, '1.3.6.1.2.1.25.2.3.1.5.1')
        used_disk = self._raw_snmp_get(ip, '1.3.6.1.2.1.25.2.3.1.6.1')
        if total_disk and used_disk:
            metrics['disk_usage'] = round((used_disk / total_disk) * 100, 2)

        return metrics

    def get_network_stats(self, devices):
        # Mantenemos esta función para evitar el error de 'attribute'
        stats = {'bandwidth_usage': 0, 'is_saturated': False, 'total_devices': len(devices)}
        curr_io = psutil.net_io_counters()
        if self.previous_net_io:
            diff = (curr_io.bytes_sent + curr_io.bytes_recv) - \
                   (self.previous_net_io.bytes_sent + self.previous_net_io.bytes_recv)
            stats['bandwidth_usage'] = round((diff * 8) / (1024 * 1024), 2)
        self.previous_net_io = curr_io
        return stats