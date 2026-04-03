import subprocess
import time

class DeviceMonitor:
    def __init__(self):
        self.community = 'public'
        # Almacenamos (últimos_octetos, timestamp) por IP para calcular Mbps
        self.last_traffic_data = {} 

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
        
        # CPU: Promedio de carga
        try:
            res = subprocess.run(['snmpwalk', '-v', '2c', '-c', self.community, ip, '1.3.6.1.2.1.25.3.3.1.2'],
                               capture_output=True, text=True, timeout=1.5)
            if res.returncode == 0:
                loads = [int(l.split('INTEGER:')[1]) for l in res.stdout.strip().split('\n') if 'INTEGER:' in l]
                if loads: metrics['cpu_usage'] = round(sum(loads) / len(loads), 2)
        except: pass
        
        # RAM: Uso porcentual
        t_ram = self._raw_snmp_get(ip, '1.3.6.1.2.1.25.2.3.1.5.3')
        u_ram = self._raw_snmp_get(ip, '1.3.6.1.2.1.25.2.3.1.6.3')
        if t_ram and u_ram:
            metrics['ram_usage'] = round((float(u_ram) / float(t_ram)) * 100, 2)

        # RED: Cálculo de Mbps (Velocidad real)
        try:
            res = subprocess.run(['snmpwalk', '-v', '2c', '-c', self.community, ip, '1.3.6.1.2.1.2.2.1.10'],
                               capture_output=True, text=True, timeout=1.5)
            if res.returncode == 0:
                # Sumamos octetos de todas las interfaces activas
                current_octets = sum([int(l.split('Counter32:')[1]) for l in res.stdout.strip().split('\n') if 'Counter32:' in l])
                now = time.time()

                if ip in self.last_traffic_data:
                    prev_octets, prev_time = self.last_traffic_data[ip]
                    diff_bits = (current_octets - prev_octets) * 8
                    diff_time = now - prev_time
                    if diff_time > 0:
                        # Convertimos a Mbps
                        metrics['network_usage'] = round(diff_bits / diff_time / 1_000_000, 2)
                
                self.last_traffic_data[ip] = (current_octets, now)
        except: pass

        # DISCO: Uso porcentual
        t_disk = self._raw_snmp_get(ip, '1.3.6.1.2.1.25.2.3.1.5.1')
        u_disk = self._raw_snmp_get(ip, '1.3.6.1.2.1.25.2.3.1.6.1')
        if t_disk and u_disk:
            metrics['disk_usage'] = round((float(u_disk) / float(t_disk)) * 100, 2)

        return metrics

    def get_process_details(self, ip):
        cpu_model = "Procesador Genérico"
        sys_model = "Modelo no detectado"
        
        try:
            res = subprocess.run(['snmpwalk', '-v', '2c', '-c', self.community, ip, '1.3.6.1.2.1.25.3.2.1.3'],
                               capture_output=True, text=True, timeout=2)
            if res.returncode == 0:
                lines = res.stdout.strip().split('\n')
                for line in lines:
                    content = line.split('STRING: ')[1].replace('"', '') if 'STRING: ' in line else ""
                    if ('Intel' in content or 'AMD' in content) and 'OneNote' not in content:
                        cpu_model = content
                    if any(brand in content for brand in ['Inspiron', 'Dell', 'HP', 'Lenovo', 'ThinkPad']):
                        sys_model = content
        except: pass

        if sys_model == "Modelo no detectado":
            sys_info = self._raw_snmp_get(ip, '1.3.6.1.2.1.1.1.0')
            if sys_info:
                sys_model = sys_info.split("Software:")[1].split("-")[0].strip() if "Software:" in sys_info else sys_info[:40]

        t_ram_units = self._raw_snmp_get(ip, '1.3.6.1.2.1.25.2.3.1.5.3') or "0"
        return {
            'hostname': self._raw_snmp_get(ip, '1.3.6.1.2.1.1.5.0') or ip,
            'cpu_model': cpu_model,
            'sys_model': sys_model,
            'total_ram': f"{round(float(t_ram_units) * 65536 / (1024**3), 1)} GB" if t_ram_units != "0" else "N/A",
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