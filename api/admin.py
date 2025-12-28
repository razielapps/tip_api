from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, MatchTip, APIRequestLog, CreditTransaction, Proxy

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'credit_balance', 'is_premium', 'is_active')
    list_filter = ('is_premium', 'is_staff', 'is_active')
    search_fields = ('username', 'email', 'api_key')
    readonly_fields = ('api_key',)
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('email',)}),
        ('API Info', {'fields': ('api_key', 'credit_balance', 'earned_tokens')}),
        ('Proxy Settings', {'fields': ('proxy_enabled', 'proxy_host', 'proxy_port')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'is_premium')}),
    )

@admin.register(MatchTip)
class MatchTipAdmin(admin.ModelAdmin):
    list_display = ('match_id', 'tip_type', 'league', 'match_time', 'confidence_level')
    list_filter = ('tip_type', 'confidence_level', 'is_live')
    search_fields = ('league', 'home_team', 'away_team')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(APIRequestLog)
class APIRequestLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'endpoint', 'credits_used', 'timestamp')
    list_filter = ('used_proxy',)
    search_fields = ('user__username', 'endpoint')
    readonly_fields = ('timestamp',)

@admin.register(Proxy)
class ProxyAdmin(admin.ModelAdmin):
    list_display = ('host', 'port', 'protocol', 'success_rate', 'is_active')
    list_filter = ('protocol', 'is_active')
    readonly_fields = ('success_rate', 'last_used')

admin.site.register(CreditTransaction)