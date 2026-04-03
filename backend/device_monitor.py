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
        
        # CPU: Promedio
        try:
            res = subprocess.run(['snmpwalk', '-v', '2c', '-c', self.community, ip, '1.3.6.1.2.1.25.3.3.1.2'],
                               capture_output=True, text=True, timeout=1.5)
            if res.returncode == 0:
                loads = [int(l.split('INTEGER:')[1]) for l in res.stdout.strip().split('\n') if 'INTEGER:' in l]
                if loads: metrics['cpu_usage'] = round(sum(loads) / len(loads), 2)
        except: pass
        
        # RAM (Uso dinámico)
        t_ram = self._raw_snmp_get(ip, '1.3.6.1.2.1.25.2.3.1.5.3')
        u_ram = self._raw_snmp_get(ip, '1.3.6.1.2.1.25.2.3.1.6.3')
        if t_ram and u_ram:
            metrics['ram_usage'] = round((float(u_ram) / float(t_ram)) * 100, 2)

        # RED: Tráfico dinámico
        try:
            res = subprocess.run(['snmpwalk', '-v', '2c', '-c', self.community, ip, '1.3.6.1.2.1.2.2.1.10'],
                               capture_output=True, text=True, timeout=1.5)
            if res.returncode == 0:
                octets = [int(l.split('Counter32:')[1]) for l in res.stdout.strip().split('\n') if 'Counter32:' in l]
                if octets: metrics['network_usage'] = round(max(octets) / (1024 * 1024), 2)
        except: pass

        # DISCO (C:)
        t_disk = self._raw_snmp_get(ip, '1.3.6.1.2.1.25.2.3.1.5.1')
        u_disk = self._raw_snmp_get(ip, '1.3.6.1.2.1.25.2.3.1.6.1')
        if t_disk and u_disk:
            metrics['disk_usage'] = round((float(u_disk) / float(t_disk)) * 100, 2)

        return metrics

    def get_process_details(self, ip):
        # 1. Nombre Real del Procesador (Equivalente a wmic cpu get name)
        cpu_model = "Procesador Genérico"
        sys_model = "Modelo no detectado"
        
        try:
            # Hacemos un walk a la tabla de descripciones de hardware
            res = subprocess.run(['snmpwalk', '-v', '2c', '-c', self.community, ip, '1.3.6.1.2.1.25.3.2.1.3'],
                               capture_output=True, text=True, timeout=2)
            if res.returncode == 0:
                lines = res.stdout.strip().split('\n')
                for line in lines:
                    content = line.split('STRING: ')[1].replace('"', '') if 'STRING: ' in line else ""
                    # Buscamos el procesador real (Intel/AMD)
                    if ('Intel' in content or 'AMD' in content) and 'OneNote' not in content:
                        cpu_model = content
                    # Buscamos el modelo del sistema si aparece en la tabla de hardware
                    if any(brand in content for brand in ['Inspiron', 'Dell', 'HP', 'Lenovo', 'ThinkPad']):
                        sys_model = content
        except: pass

        # 2. Si sys_model sigue genérico, usamos SysDescr (Versión OS)
        if sys_model == "Modelo no detectado":
            sys_info = self._raw_snmp_get(ip, '1.3.6.1.2.1.1.1.0')
            if sys_info:
                if "Software:" in sys_info:
                    sys_model = sys_info.split("Software:")[1].split("-")[0].strip()
                else:
                    sys_model = sys_info[:50] # Primeros 50 caracteres si es muy largo

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