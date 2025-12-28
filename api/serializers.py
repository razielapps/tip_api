from rest_framework import serializers
from .models import User, MatchTip, APIRequestLog, Subscription, CreditTransaction
from django.contrib.auth import authenticate
import uuid


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "api_key",
            "credit_balance",
            "earned_tokens",
            "is_premium",
            "proxy_enabled",
        ]
        read_only_fields = ["api_key", "credit_balance", "earned_tokens"]


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    referral_code = serializers.CharField(required=False)

    class Meta:
        model = User
        fields = ["username", "email", "password", "referral_code"]

    def create(self, validated_data):
        referral_code = validated_data.pop("referral_code", None)
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"],
            referral_code=str(uuid.uuid4())[:8],
            credit_balance=1000,
        )

        if referral_code:
            try:
                inviter = User.objects.get(referral_code=referral_code)
                user.invited_by = inviter
                user.save()
            except User.DoesNotExist:
                pass

        return user


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(username=data["username"], password=data["password"])
        if user and user.is_active:
            return user
        raise serializers.ValidationError("Invalid credentials")


class MatchTipSerializer(serializers.ModelSerializer):
    match = serializers.SerializerMethodField()
    match_kickoff = serializers.DateTimeField(source="match_time")
    is_hot = serializers.SerializerMethodField()

    class Meta:
        model = MatchTip
        fields = [
            "id",
            "match_id",
            "tip_type",
            "league",
            "match",
            "match_kickoff",
            "pick",
            "odds",
            "percentage",
            "market",
            "total_money",
            "dominant_money",
            "confidence_level",
            "is_live",
            "is_major_league",
            "is_hot",
            "created_at",
        ]

    def get_match(self, obj):
        return f"{obj.home_team} vs {obj.away_team}"

    def get_is_hot(self, obj):
        return obj.confidence_level == "high"


class APIRequestLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = APIRequestLog
        fields = "__all__"


class CreditTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CreditTransaction
        fields = "__all__"
