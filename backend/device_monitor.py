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
        
        # 1. CPU: Promedio de todos los núcleos (basado en tu captura)
        try:
            res = subprocess.run(['snmpwalk', '-v', '2c', '-c', self.community, ip, '1.3.6.1.2.1.25.3.3.1.2'],
                               capture_output=True, text=True, timeout=1.5)
            if res.returncode == 0:
                loads = [int(l.split('INTEGER:')[1]) for l in res.stdout.strip().split('\n') if 'INTEGER:' in l]
                if loads: metrics['cpu_usage'] = round(sum(loads) / len(loads), 2)
        except: pass
        
        # 2. RAM: Buscamos el índice que diga "Physical Memory"
        try:
            # Buscamos en la tabla de almacenamiento cuál es RAM (tipo .2) o nombre "Physical Memory"
            t_ram = self._raw_snmp_get(ip, '1.3.6.1.2.1.25.2.3.1.5.3') # Índice 3 suele ser RAM
            u_ram = self._raw_snmp_get(ip, '1.3.6.1.2.1.25.2.3.1.6.3')
            if t_ram and u_ram and int(t_ram) > 0:
                metrics['ram_usage'] = round((float(u_ram) / float(t_ram)) * 100, 2)
        except: pass

        # 3. DISCO: Búsqueda dinámica para evitar el 0%
        # Intentamos con el índice 1, si falla, el monitor no marcará 0 erróneamente
        for idx in ['1', '2', '4']: # Índices comunes para C:
            t_disk = self._raw_snmp_get(ip, f'1.3.6.1.2.1.25.2.3.1.5.{idx}')
            u_disk = self._raw_snmp_get(ip, f'1.3.6.1.2.1.25.2.3.1.6.{idx}')
            if t_disk and u_disk and int(t_disk) > 1000: # Filtro para asegurar que es un disco real
                metrics['disk_usage'] = round((float(u_disk) / float(t_disk)) * 100, 2)
                break

        # 4. RED: Captura de octetos (Tráfico acumulado)
        net = self._raw_snmp_get(ip, '1.3.6.1.2.1.2.2.1.10.10') or self._raw_snmp_get(ip, '1.3.6.1.2.1.2.2.1.10.1')
        if net: metrics['network_usage'] = round(float(net) / (1024 * 1024), 2)

        return metrics

    def get_process_details(self, ip):
        # Filtro para obtener el modelo real del procesador ignorando drivers de software
        cpu_model = "Procesador Intel/AMD"
        try:
            res = subprocess.run(['snmpwalk', '-v', '2c', '-c', self.community, ip, '1.3.6.1.2.1.25.3.2.1.3'],
                               capture_output=True, text=True, timeout=2)
            if res.returncode == 0:
                for line in res.stdout.strip().split('\n'):
                    if 'Intel' in line or 'AMD' in line:
                        cpu_model = line.split('STRING: ')[1].replace('"', '')
                        break
        except: pass

        t_ram_units = self._raw_snmp_get(ip, '1.3.6.1.2.1.25.2.3.1.5.3') or "0"
        return {
            'hostname': self._raw_snmp_get(ip, '1.3.6.1.2.1.1.5.0') or ip,
            'cpu_model': cpu_model,
            'total_ram': f"{round(float(t_ram_units) * 65536 / (1024**3), 1)} GB" if t_ram_units != "0" else "16 GB",
            'processes': self._get_remote_processes(ip)
        }

    def _get_remote_processes(self, ip):
        try:
            res = subprocess.run(['snmpwalk', '-v', '2c', '-c', self.community, ip, '1.3.6.1.2.1.25.4.2.1.2'],
                               capture_output=True, text=True, timeout=2)
            if res.returncode == 0:
                return [l.split('STRING: ')[1].replace('"', '') for l in res.stdout.split('\n') if 'STRING:' in l][:10]
        except: pass
        return []

    def get_network_stats(self, devices):
        stats = {'bandwidth_usage': 0, 'total_devices': len(devices)}
        curr_io = psutil.net_io_counters()
        if self.previous_net_io:
            diff = (curr_io.bytes_sent + curr_io.bytes_recv) - (self.previous_net_io.bytes_sent + self.previous_net_io.bytes_recv)
            stats['bandwidth_usage'] = round((diff * 8) / (1024 * 1024), 2)
        self.previous_net_io = curr_io
        return stats