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
        
        # CPU: Promedio (Ya funcionando)
        try:
            res = subprocess.run(['snmpwalk', '-v', '2c', '-c', self.community, ip, '1.3.6.1.2.1.25.3.3.1.2'],
                               capture_output=True, text=True, timeout=1.5)
            if res.returncode == 0:
                loads = [int(l.split('INTEGER:')[1]) for l in res.stdout.strip().split('\n') if 'INTEGER:' in l]
                if loads: metrics['cpu_usage'] = round(sum(loads) / len(loads), 2)
        except: pass
        
        # RAM e Índices dinámicos
        t_ram = self._raw_snmp_get(ip, '1.3.6.1.2.1.25.2.3.1.5.3')
        u_ram = self._raw_snmp_get(ip, '1.3.6.1.2.1.25.2.3.1.6.3')
        if t_ram and u_ram:
            metrics['ram_usage'] = round((float(u_ram) / float(t_ram)) * 100, 2)

        # RED: Buscamos la interfaz activa con más tráfico (Búsqueda dinámica)
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
        # 1. Nombre Real del Procesador (Filtro avanzado)
        cpu_model = "Procesador Genérico"
        try:
            res = subprocess.run(['snmpwalk', '-v', '2c', '-c', self.community, ip, '1.3.6.1.2.1.25.3.2.1.3'],
                               capture_output=True, text=True, timeout=2)
            if res.returncode == 0:
                # Buscamos la línea que diga Intel o AMD y NO sea un driver virtual
                candidates = [l.split('STRING: ')[1].replace('"', '') for l in res.stdout.strip().split('\n') 
                             if ('Intel' in l or 'AMD' in l) and 'OneNote' not in l]
                if candidates: cpu_model = candidates[0]
        except: pass

        # 2. Modelo del Sistema (SysDescr)
        sys_model = self._raw_snmp_get(ip, '1.3.6.1.2.1.1.1.0') or "Windows Device"
        # Limpiamos el string largo de Windows para que solo diga la versión
        if "Software:" in sys_model:
            sys_model = sys_model.split("Software:")[1].split("-")[0].strip()

        t_ram_units = self._raw_snmp_get(ip, '1.3.6.1.2.1.25.2.3.1.5.3') or "0"
        return {
            'hostname': self._raw_snmp_get(ip, '1.3.6.1.2.1.1.5.0') or ip,
            'cpu_model': cpu_model,
            'sys_model': sys_model, # Nuevo campo
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