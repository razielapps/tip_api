import random
from datetime import datetime, timedelta
from django.utils import timezone

class ProxyManager:
    def __init__(self):
        from api.models import Proxy
        self.Proxy = Proxy
    
    def get_best_proxy(self):
        """Get the best available proxy based on success rate"""
        active_proxies = self.Proxy.objects.filter(
            is_active=True,
            last_used__lte=timezone.now() - timedelta(minutes=1)
        ).order_by('-success_rate')
        
        if active_proxies.exists():
            proxy = active_proxies.first()
            proxy.last_used = timezone.now()
            proxy.save()
            
            if proxy.username and proxy.password:
                return f"{proxy.protocol}://{proxy.username}:{proxy.password}@{proxy.host}:{proxy.port}"
            else:
                return f"{proxy.protocol}://{proxy.host}:{proxy.port}"
        
        return None
    
    def update_proxy_success(self, proxy_string, success=True):
        """Update proxy success rate"""
        try:
            # Parse proxy string
            protocol = proxy_string.split('://')[0]
            host_port = proxy_string.split('://')[1].split('@')[-1]
            host = host_port.split(':')[0]
            port = int(host_port.split(':')[1])
            
            proxy = self.Proxy.objects.get(
                host=host,
                port=port,
                protocol=protocol
            )
            
            # Update success rate (simple moving average)
            proxy.success_rate = (proxy.success_rate * 0.8) + (100 * 0.2 if success else 0 * 0.2)
            proxy.last_used = timezone.now()
            proxy.save()
            
        except (self.Proxy.DoesNotExist, ValueError, IndexError):
            pass