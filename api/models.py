from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid

class User(AbstractUser):
    api_key = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    credit_balance = models.IntegerField(default=1000, validators=[MinValueValidator(0)])
    earned_tokens = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    referral_code = models.CharField(max_length=50, unique=True, null=True, blank=True)
    invited_by = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True)
    is_premium = models.BooleanField(default=False)
    
    # Proxy settings
    proxy_enabled = models.BooleanField(default=False)
    proxy_host = models.CharField(max_length=255, null=True, blank=True)
    proxy_port = models.IntegerField(null=True, blank=True)
    proxy_username = models.CharField(max_length=255, null=True, blank=True)
    proxy_password = models.CharField(max_length=255, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'users'
    
    def __str__(self):
        return self.username
    
    def has_sufficient_credits(self, use_proxy=False):
        if use_proxy:
            return self.credit_balance >= 100
        return self.credit_balance >= 200
    
    def deduct_credits(self, use_proxy=False):
        if use_proxy:
            deduction = 100
        else:
            deduction = 200
        
        if self.credit_balance >= deduction:
            self.credit_balance -= deduction
            self.save()
            return True
        return False

class MatchTip(models.Model):
    TIP_TYPES = [
        ('normal', 'Normal'),
        ('underdog', 'Underdog'),
    ]
    
    match_id = models.CharField(max_length=100, db_index=True)
    tip_type = models.CharField(max_length=20, choices=TIP_TYPES, default='normal')
    
    league = models.CharField(max_length=255)
    home_team = models.CharField(max_length=255)
    away_team = models.CharField(max_length=255)
    match_time = models.DateTimeField()
    
    pick = models.CharField(max_length=255)
    odds = models.DecimalField(max_digits=5, decimal_places=2)
    percentage = models.DecimalField(max_digits=5, decimal_places=2)
    market = models.CharField(max_length=255)
    
    total_money = models.DecimalField(max_digits=10, decimal_places=2)
    dominant_money = models.DecimalField(max_digits=10, decimal_places=2)
    
    confidence_level = models.CharField(max_length=20, choices=[
        ('high', 'High (85%+)'),
        ('medium', 'Medium (69-84%)'),
        ('low', 'Low (<69%)'),
    ])
    
    is_live = models.BooleanField(default=False)
    is_major_league = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'match_tips'
        indexes = [
            models.Index(fields=['match_time', 'tip_type']),
            models.Index(fields=['confidence_level', 'tip_type']),
        ]
    
    def __str__(self):
        return f"{self.home_team} vs {self.away_team} - {self.pick}"

class APIRequestLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='api_requests')
    endpoint = models.CharField(max_length=255)
    parameters = models.JSONField(default=dict)
    credits_used = models.IntegerField()
    response_count = models.IntegerField(default=0)
    used_proxy = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'api_request_logs'
        ordering = ['-timestamp']

class Subscription(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subscriptions')
    plan_type = models.CharField(max_length=50)
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'subscriptions'

class CreditTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('api_call', 'API Call'),
        ('purchase', 'Credit Purchase'),
        ('refund', 'Refund'),
        ('admin_adjustment', 'Admin Adjustment'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='credit_transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.IntegerField()
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add_add=True)
    
    class Meta:
        db_table = 'credit_transactions'
        ordering = ['-created_at']

class Proxy(models.Model):
    host = models.CharField(max_length=255)
    port = models.IntegerField()
    username = models.CharField(max_length=255, null=True, blank=True)
    password = models.CharField(max_length=255, null=True, blank=True)
    protocol = models.CharField(max_length=10, default='http')
    is_active = models.BooleanField(default=True)
    success_rate = models.FloatField(default=0.0)
    last_used = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'proxies'
        verbose_name_plural = 'proxies'
    
    def __str__(self):
        return f"{self.protocol}://{self.host}:{self.port}"