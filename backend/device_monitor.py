import psutil
import time

class DeviceMonitor:
    def __init__(self):
        self.bandwidth_threshold = 80  # 80% de saturación
        self.previous_net_io = None
        
    def get_network_stats(self, devices):
        """Calcular estadísticas de red"""
        stats = {
            'bandwidth_usage': 0,
            'is_saturated': False,
            'top_consumer': None,
            'total_devices': len(devices),
            'active_devices': 0
        }
        
        # Calcular uso de ancho de banda
        current_net_io = psutil.net_io_counters()
        
        if self.previous_net_io:
            bytes_sent = current_net_io.bytes_sent - self.previous_net_io.bytes_sent
            bytes_recv = current_net_io.bytes_recv - self.previous_net_io.bytes_recv
            
            # Convertir a Mbps (asumiendo medición de 1 segundo)
            bandwidth_mbps = (bytes_sent + bytes_recv) * 8 / 1024 / 1024
            stats['bandwidth_usage'] = round(bandwidth_mbps, 2)
            
            # Determinar saturación (simplificado - asume red 100Mbps)
            stats['is_saturated'] = bandwidth_mbps > 80
        
        self.previous_net_io = current_net_io
        
        # Encontrar dispositivo con mayor consumo
        max_usage = 0
        top_device = None
        
        for ip, device in devices.items():
            if device['is_reachable']:
                stats['active_devices'] += 1
                
                total_usage = (
                    device.get('cpu_usage', 0) +
                    device.get('ram_usage', 0) +
                    device.get('network_usage', 0)
                )
                
                if total_usage > max_usage:
                    max_usage = total_usage
                    top_device = {
                        'ip': ip,
                        'hostname': device.get('hostname', 'Desconocido'),
                        'cpu': device.get('cpu_usage', 0),
                        'ram': device.get('ram_usage', 0),
                        'network': device.get('network_usage', 0)
                    }
        
        stats['top_consumer'] = top_device
        
        return stats