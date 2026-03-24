import base64
import hashlib
import hmac
import secrets
import struct
import time
from urllib.parse import quote

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.db import transaction
<<<<<<< HEAD
from django.utils import timezone
=======
>>>>>>> 976cc83ad358ca0afbd53314dddde500db23c137
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import PasswordResetSession, RecoveryCode, SecurityQuestion, UserProfile
from .serializers import (
    MeSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetFallbackSerializer,
    PasswordResetStartSerializer,
    PasswordResetTotpSerializer,
    SecurityQuestionSerializer,
    SignupSerializer,
    TotpVerifySerializer,
    find_reset_session,
    match_security_answers,
    use_recovery_code,
)

User = get_user_model()

DEFAULT_SECURITY_QUESTIONS = [
    'What was the name of your first school?',
    'What is your mother’s birth city?',
    'What was your childhood nickname?',
    'What is the name of your favorite teacher?',
]


def ensure_default_security_questions():
    for question in DEFAULT_SECURITY_QUESTIONS:
        SecurityQuestion.objects.get_or_create(question_text=question, defaults={'is_active': True})


def generate_recovery_codes(*, user, count=6):
    RecoveryCode.objects.filter(user=user).delete()
    raw_codes = []
    for _ in range(count):
        raw_code = f'{secrets.token_hex(2).upper()}-{secrets.token_hex(2).upper()}'
        RecoveryCode.objects.create(user=user, code_hash=make_password(raw_code))
        raw_codes.append(raw_code)
    return raw_codes


def generate_totp_secret():
    return base64.b32encode(secrets.token_bytes(20)).decode('utf-8').rstrip('=')


def _normalize_base32_secret(secret):
    padding = '=' * ((8 - len(secret) % 8) % 8)
    return f'{secret}{padding}'


def build_totp_code(secret, timestamp=None, step=30, digits=6):
    if timestamp is None:
        timestamp = int(time.time())
    counter = int(timestamp // step)
    key = base64.b32decode(_normalize_base32_secret(secret), casefold=True)
    message = struct.pack('>Q', counter)
    digest = hmac.new(key, message, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    binary = struct.unpack('>I', digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return str(binary % (10**digits)).zfill(digits)


def verify_totp(secret, otp, window=4):
    now = int(time.time())
    for offset in range(-window, window + 1):
<<<<<<< HEAD
        candidate_time = now + (offset * 30)
        if build_totp_code(secret, timestamp=candidate_time) == otp:
=======
        if build_totp_code(secret, timestamp=now + (offset * 30)) == otp:
>>>>>>> 976cc83ad358ca0afbd53314dddde500db23c137
            return True
    return False


def create_reset_session(*, user, method):
<<<<<<< HEAD
    session = PasswordResetSession.objects.create(
=======
    return PasswordResetSession.objects.create(
>>>>>>> 976cc83ad358ca0afbd53314dddde500db23c137
        user=user,
        token=secrets.token_urlsafe(32),
        method=method,
        expires_at=PasswordResetSession.default_expiry(),
    )
<<<<<<< HEAD
    return session
=======
>>>>>>> 976cc83ad358ca0afbd53314dddde500db23c137


class SecurityQuestionListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        ensure_default_security_questions()
<<<<<<< HEAD
        questions = SecurityQuestion.objects.filter(is_active=True)
        return Response(SecurityQuestionSerializer(questions, many=True).data)
=======
        return Response(SecurityQuestionSerializer(SecurityQuestion.objects.filter(is_active=True), many=True).data)
>>>>>>> 976cc83ad358ca0afbd53314dddde500db23c137


class SignupView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        ensure_default_security_questions()
        serializer = SignupSerializer(data=request.data, context={'generate_recovery_codes': generate_recovery_codes})
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                'user': MeSerializer(user).data,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'recovery_codes': getattr(user, '_raw_recovery_codes', []),
            },
            status=status.HTTP_201_CREATED,
        )


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        UserProfile.objects.get_or_create(user=request.user)
        return Response(MeSerializer(request.user).data)


class TotpSetupView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        if profile.totp_secret:
            secret = profile.totp_secret
        else:
            secret = generate_totp_secret()
            profile.totp_secret = secret
            profile.totp_enabled = False
            profile.save(update_fields=['totp_secret', 'totp_enabled'])
        issuer = 'MyFinance'
        label = quote(f'{issuer}:{request.user.username}')
        otpauth_url = f'otpauth://totp/{label}?secret={secret}&issuer={quote(issuer)}'
        return Response(
            {
                'secret': secret,
                'otpauth_url': otpauth_url,
                'message': 'Scan the QR code with your authenticator app and verify one OTP to enable it. If authenticator is already enabled, this shows your existing setup instead of creating a new secret.',
            }
        )


class TotpVerifyView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = TotpVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        if not profile.totp_secret:
            return Response({'detail': 'Set up authenticator first.'}, status=400)
        if not verify_totp(profile.totp_secret, serializer.validated_data['otp']):
            return Response({'detail': 'Invalid OTP.'}, status=400)
        profile.totp_enabled = True
        profile.save(update_fields=['totp_enabled'])
        return Response({'message': 'Authenticator enabled successfully.'})


class PasswordResetStartView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        ensure_default_security_questions()
        serializer = PasswordResetStartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.filter(username=serializer.validated_data['username']).first()
        if user is None:
            return Response({'detail': 'User not found.'}, status=404)
        profile, _ = UserProfile.objects.get_or_create(user=user)
        answers = user.security_answers.select_related('question').order_by('question_id')
        return Response(
            {
                'username': user.username,
                'totp_enabled': profile.totp_enabled,
<<<<<<< HEAD
                'security_questions': [
                    {'question_id': item.question_id, 'question_text': item.question.question_text}
                    for item in answers
                ],
=======
                'security_questions': [{'question_id': item.question_id, 'question_text': item.question.question_text} for item in answers],
>>>>>>> 976cc83ad358ca0afbd53314dddde500db23c137
            }
        )


class PasswordResetTotpView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetTotpSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.filter(username=serializer.validated_data['username']).first()
        if user is None:
            return Response({'detail': 'User not found.'}, status=404)
        profile, _ = UserProfile.objects.get_or_create(user=user)
        if not profile.totp_enabled or not profile.totp_secret:
            return Response({'detail': 'Authenticator reset is not enabled for this user.'}, status=400)
        if not verify_totp(profile.totp_secret, serializer.validated_data['otp']):
            return Response({'detail': 'Invalid OTP.'}, status=400)
        session = create_reset_session(user=user, method=PasswordResetSession.METHOD_TOTP)
        return Response({'reset_token': session.token, 'method': session.method})


class PasswordResetFallbackView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetFallbackSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.filter(username=serializer.validated_data['username']).first()
        if user is None:
            return Response({'detail': 'User not found.'}, status=404)
<<<<<<< HEAD
        answers = serializer.validated_data['security_answers']
        if not match_security_answers(user=user, answers=answers):
=======
        if not match_security_answers(user=user, answers=serializer.validated_data['security_answers']):
>>>>>>> 976cc83ad358ca0afbd53314dddde500db23c137
            return Response({'detail': 'Security answers did not match.'}, status=400)
        if not use_recovery_code(user=user, raw_code=serializer.validated_data['recovery_code']):
            return Response({'detail': 'Invalid or already-used recovery code.'}, status=400)
        session = create_reset_session(user=user, method=PasswordResetSession.METHOD_FALLBACK)
        return Response({'reset_token': session.token, 'method': session.method})


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        session = find_reset_session(serializer.validated_data['reset_token'])
        if session is None or not session.is_valid():
            return Response({'detail': 'Reset session is invalid or expired.'}, status=400)
        with transaction.atomic():
            session.user.set_password(serializer.validated_data['new_password'])
            session.user.save(update_fields=['password'])
            session.mark_used()
        return Response({'message': 'Password updated successfully.'})
