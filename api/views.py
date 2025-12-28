from rest_framework import generics, status, viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action, api_view, permission_classes
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from datetime import datetime, timedelta
import requests
import json
import random
import time

from .models import User, MatchTip, APIRequestLog, CreditTransaction
from .serializers import (
    UserSerializer, UserRegistrationSerializer, LoginSerializer,
    MatchTipSerializer, APIRequestLogSerializer, CreditTransactionSerializer
)
from .scanners import TipScanner, UnderdogTipScanner
from utils.proxy_manager import ProxyManager

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        token = Token.objects.create(user=user)
        
        return Response({
            'user': UserSerializer(user).data,
            'token': token.key,
            'message': 'Registration successful'
        }, status=status.HTTP_201_CREATED)

class LoginView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data
            token, created = Token.objects.get_or_create(user=user)
            
            return Response({
                'user': UserSerializer(user).data,
                'token': token.key,
                'message': 'Login successful'
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return self.request.user

class MatchTipAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Check if user has sufficient credits
        use_proxy = request.data.get('use_proxy', False) or request.query_params.get('use_proxy', 'false').lower() == 'true'
        
        if not request.user.has_sufficient_credits(use_proxy):
            return Response({
                'error': 'Insufficient credits',
                'required_credits': 100 if use_proxy else 200,
                'current_balance': request.user.credit_balance
            }, status=status.HTTP_402_PAYMENT_REQUIRED)
        
        # Parse parameters
        tip_type = request.data.get('tip_type', 'normal') or request.query_params.get('tip_type', 'normal')
        mode = request.data.get('mode', 'normal') or request.query_params.get('mode', 'normal')
        live_only = request.data.get('live_only', False) or request.query_params.get('live_only', 'false').lower() == 'true'
        exclude_major = request.data.get('exclude_major', False) or request.query_params.get('exclude_major', 'false').lower() == 'true'
        time_order = request.data.get('time_order', False) or request.query_params.get('time_order', 'false').lower() == 'true'
        limit = int(request.data.get('limit', 10) or request.query_params.get('limit', 10))
        limit = max(1, min(limit, 100))
        
        # Determine confidence threshold
        threshold = 75 if mode == 'safe' else 69
        
        # Get proxy if requested
        proxy = None
        if use_proxy:
            proxy_manager = ProxyManager()
            proxy = proxy_manager.get_best_proxy()
        
        try:
            # Fetch matches using the scanner
            if tip_type == 'underdog':
                scanner = UnderdogTipScanner()
            else:
                scanner = TipScanner()
            
            matches = scanner.fetch_matches_once(
                threshold_pct=threshold,
                limit=limit,
                live_only=live_only,
                exclude_major=exclude_major,
                time_order=time_order,
                proxy=proxy
            )
            
            # Deduct credits
            if not request.user.deduct_credits(use_proxy):
                return Response({'error': 'Credit deduction failed'}, 
                              status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # Log the API request
            APIRequestLog.objects.create(
                user=request.user,
                endpoint='/api/matches/',
                parameters={
                    'tip_type': tip_type,
                    'mode': mode,
                    'live_only': live_only,
                    'exclude_major': exclude_major,
                    'time_order': time_order,
                    'limit': limit,
                    'use_proxy': use_proxy
                },
                credits_used=100 if use_proxy else 200,
                response_count=len(matches),
                used_proxy=use_proxy
            )
            
            # Create credit transaction record
            CreditTransaction.objects.create(
                user=request.user,
                transaction_type='api_call',
                amount=-(100 if use_proxy else 200),
                description=f'API call for {tip_type} tips (proxy: {use_proxy})'
            )
            
            return Response({
                'success': True,
                'count': len(matches),
                'credits_used': 100 if use_proxy else 200,
                'credits_remaining': request.user.credit_balance,
                'matches': matches
            })
            
        except Exception as e:
            return Response({
                'error': str(e),
                'success': False
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class MatchTipViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = MatchTipSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['tip_type', 'confidence_level', 'is_live', 'is_major_league']
    
    def get_queryset(self):
        queryset = MatchTip.objects.all()
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            try:
                start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
                queryset = queryset.filter(match_time__date__gte=start_datetime.date())
            except ValueError:
                pass
        
        if end_date:
            try:
                end_datetime = datetime.strptime(end_date, '%Y-%m-%d')
                queryset = queryset.filter(match_time__date__lte=end_datetime.date())
            except ValueError:
                pass
        
        # Filter by league
        league = self.request.query_params.get('league')
        if league:
            queryset = queryset.filter(league__icontains=league)
        
        # Order by match time (upcoming first)
        queryset = queryset.order_by('match_time')
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def today(self, request):
        today = timezone.now().date()
        tips = MatchTip.objects.filter(match_time__date=today)
        serializer = self.get_serializer(tips, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        now = timezone.now()
        upcoming = MatchTip.objects.filter(match_time__gte=now).order_by('match_time')
        serializer = self.get_serializer(upcoming, many=True)
        return Response(serializer.data)

class APIRequestLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = APIRequestLogSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return APIRequestLog.objects.filter(user=self.request.user).order_by('-timestamp')

class CreditTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CreditTransactionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return CreditTransaction.objects.filter(user=self.request.user).order_by('-created_at')

class BuyCreditsView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        amount = request.data.get('amount')
        payment_method = request.data.get('payment_method')
        
        if not amount or amount <= 0:
            return Response({'error': 'Invalid amount'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        # Here you would integrate with payment gateway
        # For now, just add credits
        request.user.credit_balance += amount
        request.user.save()
        
        # Create transaction record
        CreditTransaction.objects.create(
            user=request.user,
            transaction_type='purchase',
            amount=amount,
            description=f'Credit purchase via {payment_method}'
        )
        
        return Response({
            'success': True,
            'new_balance': request.user.credit_balance,
            'message': f'Successfully purchased {amount} credits'
        })

class HealthCheckView(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request):
        return Response({
            'status': 'healthy',
            'timestamp': timezone.now().isoformat(),
            'service': 'Tip API'
        })

@api_view(['GET'])
@permission_classes([AllowAny])
def api_documentation(request):
    return Response({
        'endpoints': {
            'auth': {
                'register': 'POST /api/auth/register/',
                'login': 'POST /api/auth/login/',
                'profile': 'GET /api/auth/profile/'
            },
            'matches': {
                'live_query': 'GET /api/matches/',
                'list': 'GET /api/tips/',
                'today': 'GET /api/tips/today/',
                'upcoming': 'GET /api/tips/upcoming/'
            },
            'user': {
                'credits': 'GET /api/credits/',
                'buy_credits': 'POST /api/credits/buy/',
                'transactions': 'GET /api/credits/transactions/',
                'api_logs': 'GET /api/logs/'
            }
        },
        'parameters': {
            'live_query': {
                'tip_type': 'normal or underdog',
                'mode': 'normal or safe',
                'live_only': 'true/false',
                'exclude_major': 'true/false',
                'time_order': 'true/false',
                'limit': 'number (1-100)',
                'use_proxy': 'true/false (100 credits with proxy, 200 without)'
            }
        }
    })