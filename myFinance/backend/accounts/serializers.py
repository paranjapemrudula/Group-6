from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password, make_password
from rest_framework import serializers

from .models import PasswordResetSession, RecoveryCode, SecurityQuestion, UserProfile, UserSecurityAnswer

User = get_user_model()


class SecurityQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SecurityQuestion
        fields = ('id', 'question_text')


class SecurityAnswerInputSerializer(serializers.Serializer):
    question_id = serializers.IntegerField()
    answer = serializers.CharField(write_only=True, trim_whitespace=True, min_length=2, max_length=255)


class SignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True, min_length=8)
    phone_number = serializers.CharField(write_only=True, required=False, allow_blank=True, max_length=32)
    security_answers = SecurityAnswerInputSerializer(many=True, write_only=True, min_length=2, max_length=2)
    recovery_codes = serializers.ListField(read_only=True)

    class Meta:
        model = User
        fields = (
#<<<<<<< HEAD
            'id',
            'username',
            'email',
            'password',
            'confirm_password',
            'phone_number',
            'security_answers',
            'recovery_codes',
#=======
            'id', 'username', 'email', 'password', 'confirm_password',
            'phone_number', 'security_answers', 'recovery_codes',
#>>>>>>> 976cc83ad358ca0afbd53314dddde500db23c137
        )

    def validate(self, attrs):
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError({'confirm_password': 'Passwords do not match.'})
#<<<<<<< HEAD

#=======
#>>>>>>> 976cc83ad358ca0afbd53314dddde500db23c137
        answers = attrs.get('security_answers') or []
        question_ids = [item['question_id'] for item in answers]
        if len(set(question_ids)) != 2:
            raise serializers.ValidationError({'security_answers': 'Choose two different security questions.'})
#<<<<<<< HEAD

#=======
#>>>>>>> 976cc83ad358ca0afbd53314dddde500db23c137
        available_ids = set(SecurityQuestion.objects.filter(id__in=question_ids, is_active=True).values_list('id', flat=True))
        if len(available_ids) != 2:
            raise serializers.ValidationError({'security_answers': 'One or more selected questions are invalid.'})
        return attrs

    def create(self, validated_data):
        phone_number = validated_data.pop('phone_number', '')
        answers = validated_data.pop('security_answers', [])
        validated_data.pop('confirm_password', None)
        password = validated_data.pop('password')
#<<<<<<< HEAD

        user = User.objects.create_user(password=password, **validated_data)
        UserProfile.objects.create(user=user, phone_number=phone_number)

        question_map = {
            question.id: question for question in SecurityQuestion.objects.filter(
                id__in=[item['question_id'] for item in answers]
            )
        }
#=======
        user = User.objects.create_user(password=password, **validated_data)
        UserProfile.objects.create(user=user, phone_number=phone_number)
        question_map = {q.id: q for q in SecurityQuestion.objects.filter(id__in=[item['question_id'] for item in answers])}
#>>>>>>> 976cc83ad358ca0afbd53314dddde500db23c137
        for item in answers:
            UserSecurityAnswer.objects.create(
                user=user,
                question=question_map[item['question_id']],
                answer_hash=make_password(item['answer'].strip().lower()),
            )
#<<<<<<< HEAD

#=======
#>>>>>>> 976cc83ad358ca0afbd53314dddde500db23c137
        raw_recovery_codes = self.context['generate_recovery_codes'](user=user)
        user._raw_recovery_codes = raw_recovery_codes
        return user


class MeSerializer(serializers.ModelSerializer):
    phone_number = serializers.CharField(source='profile.phone_number', read_only=True)
    totp_enabled = serializers.BooleanField(source='profile.totp_enabled', read_only=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'date_joined', 'phone_number', 'totp_enabled')


class PasswordResetStartSerializer(serializers.Serializer):
    username = serializers.CharField(trim_whitespace=True)


class PasswordResetTotpSerializer(serializers.Serializer):
    username = serializers.CharField(trim_whitespace=True)
    otp = serializers.CharField(trim_whitespace=True, min_length=6, max_length=6)

    def validate_otp(self, value):
        normalized = ''.join(char for char in value if char.isdigit())
        if len(normalized) != 6:
            raise serializers.ValidationError('Enter a valid 6-digit OTP.')
        return normalized


class PasswordResetFallbackSerializer(serializers.Serializer):
    username = serializers.CharField(trim_whitespace=True)
    security_answers = SecurityAnswerInputSerializer(many=True, min_length=2, max_length=2)
    recovery_code = serializers.CharField(trim_whitespace=True, min_length=8, max_length=64)

    def validate(self, attrs):
        answers = attrs.get('security_answers') or []
#<<<<<<< HEAD
        question_ids = [item['question_id'] for item in answers]
        if len(set(question_ids)) != 2:
#=======
         if len({item['question_id'] for item in answers}) != 2:
#>>>>>>> 976cc83ad358ca0afbd53314dddde500db23c137
            raise serializers.ValidationError({'security_answers': 'Provide answers for two different questions.'})
        return attrs


class PasswordResetConfirmSerializer(serializers.Serializer):
    reset_token = serializers.CharField(trim_whitespace=True)
    new_password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True, min_length=8)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({'confirm_password': 'Passwords do not match.'})
        return attrs


class TotpVerifySerializer(serializers.Serializer):
    otp = serializers.CharField(trim_whitespace=True, min_length=6, max_length=6)

    def validate_otp(self, value):
        normalized = ''.join(char for char in value if char.isdigit())
        if len(normalized) != 6:
            raise serializers.ValidationError('Enter a valid 6-digit OTP.')
        return normalized


def match_security_answers(*, user, answers):
#<<<<<< HEAD
    stored_answers = {
        item.question_id: item
        for item in UserSecurityAnswer.objects.filter(user=user, question_id__in=[entry['question_id'] for entry in answers])
    }
#=======
    stored_answers = {item.question_id: item for item in UserSecurityAnswer.objects.filter(user=user, question_id__in=[entry['question_id'] for entry in answers])}
#>>>>>>> 976cc83ad358ca0afbd53314dddde500db23c137
    if len(stored_answers) != 2:
        return False
    for answer in answers:
        stored = stored_answers.get(answer['question_id'])
        if not stored or not check_password(answer['answer'].strip().lower(), stored.answer_hash):
            return False
    return True


def use_recovery_code(*, user, raw_code):
    for recovery_code in RecoveryCode.objects.filter(user=user, is_used=False):
        if check_password(raw_code.strip(), recovery_code.code_hash):
            recovery_code.mark_used()
            return True
    return False


def find_reset_session(raw_token):
    try:
        return PasswordResetSession.objects.get(token=raw_token)
    except PasswordResetSession.DoesNotExist:
        return None
