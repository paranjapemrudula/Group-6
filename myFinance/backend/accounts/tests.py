from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from .models import PasswordResetSession, RecoveryCode, SecurityQuestion, UserProfile
from .views import build_totp_code

User = get_user_model()


class AccountRecoveryApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.questions = [
            SecurityQuestion.objects.create(question_text='What was the name of your first school?'),
            SecurityQuestion.objects.create(question_text='What is your mother’s birth city?'),
        ]

    def test_signup_returns_recovery_codes_and_creates_security_answers(self):
<<<<<<< HEAD
        response = self.client.post(
            '/api/signup/',
            {
                'username': 'mrudu',
                'email': 'mrudu@example.com',
                'password': 'StrongPass123',
                'confirm_password': 'StrongPass123',
                'phone_number': '9999999999',
                'security_answers': [
                    {'question_id': self.questions[0].id, 'answer': 'Alpha School'},
                    {'question_id': self.questions[1].id, 'answer': 'Mysuru'},
                ],
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(response.data['recovery_codes']), 6)
        self.assertTrue(User.objects.filter(username='mrudu').exists())
=======
        response = self.client.post('/api/signup/', {
            'username': 'mrudu',
            'email': 'mrudu@example.com',
            'password': 'StrongPass123',
            'confirm_password': 'StrongPass123',
            'phone_number': '9999999999',
            'security_answers': [
                {'question_id': self.questions[0].id, 'answer': 'Alpha School'},
                {'question_id': self.questions[1].id, 'answer': 'Mysuru'},
            ],
        }, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(response.data['recovery_codes']), 6)
>>>>>>> 976cc83ad358ca0afbd53314dddde500db23c137
        self.assertEqual(UserProfile.objects.count(), 1)
        self.assertEqual(RecoveryCode.objects.count(), 6)

    def test_password_reset_fallback_and_confirm(self):
<<<<<<< HEAD
        signup = self.client.post(
            '/api/signup/',
            {
                'username': 'reset-user',
                'email': 'reset@example.com',
                'password': 'StrongPass123',
                'confirm_password': 'StrongPass123',
                'security_answers': [
                    {'question_id': self.questions[0].id, 'answer': 'Alpha School'},
                    {'question_id': self.questions[1].id, 'answer': 'Mysuru'},
                ],
            },
            format='json',
        )
        recovery_code = signup.data['recovery_codes'][0]

        start = self.client.post('/api/password-reset/start/', {'username': 'reset-user'}, format='json')
        self.assertEqual(start.status_code, 200)
        self.assertEqual(len(start.data['security_questions']), 2)

        fallback = self.client.post(
            '/api/password-reset/fallback/',
            {
                'username': 'reset-user',
                'security_answers': [
                    {'question_id': self.questions[0].id, 'answer': 'Alpha School'},
                    {'question_id': self.questions[1].id, 'answer': 'Mysuru'},
                ],
                'recovery_code': recovery_code,
            },
            format='json',
        )
        self.assertEqual(fallback.status_code, 200)
        token = fallback.data['reset_token']

        confirm = self.client.post(
            '/api/password-reset/confirm/',
            {
                'reset_token': token,
                'new_password': 'NewPass123',
                'confirm_password': 'NewPass123',
            },
            format='json',
        )
        self.assertEqual(confirm.status_code, 200)

        user = User.objects.get(username='reset-user')
        self.assertTrue(user.check_password('NewPass123'))
=======
        signup = self.client.post('/api/signup/', {
            'username': 'reset-user',
            'email': 'reset@example.com',
            'password': 'StrongPass123',
            'confirm_password': 'StrongPass123',
            'security_answers': [
                {'question_id': self.questions[0].id, 'answer': 'Alpha School'},
                {'question_id': self.questions[1].id, 'answer': 'Mysuru'},
            ],
        }, format='json')
        recovery_code = signup.data['recovery_codes'][0]
        fallback = self.client.post('/api/password-reset/fallback/', {
            'username': 'reset-user',
            'security_answers': [
                {'question_id': self.questions[0].id, 'answer': 'Alpha School'},
                {'question_id': self.questions[1].id, 'answer': 'Mysuru'},
            ],
            'recovery_code': recovery_code,
        }, format='json')
        self.assertEqual(fallback.status_code, 200)
        token = fallback.data['reset_token']
        confirm = self.client.post('/api/password-reset/confirm/', {
            'reset_token': token,
            'new_password': 'NewPass123',
            'confirm_password': 'NewPass123',
        }, format='json')
        self.assertEqual(confirm.status_code, 200)
        self.assertTrue(User.objects.get(username='reset-user').check_password('NewPass123'))
>>>>>>> 976cc83ad358ca0afbd53314dddde500db23c137
        self.assertTrue(PasswordResetSession.objects.get(token=token).is_used)

    @patch('accounts.views.verify_totp')
    def test_totp_setup_and_reset_flow(self, mock_verify_totp):
        user = User.objects.create_user(username='totp-user', password='StrongPass123')
        UserProfile.objects.create(user=user)
        self.client.force_authenticate(user=user)
<<<<<<< HEAD

        setup = self.client.post('/api/totp/setup/', {}, format='json')
        self.assertEqual(setup.status_code, 200)
        self.assertIn('otpauth_url', setup.data)

        mock_verify_totp.return_value = True
        verify = self.client.post('/api/totp/verify/', {'otp': '123456'}, format='json')
        self.assertEqual(verify.status_code, 200)

        self.client.force_authenticate(user=None)
        reset = self.client.post(
            '/api/password-reset/totp/',
            {'username': 'totp-user', 'otp': '123456'},
            format='json',
        )
        self.assertEqual(reset.status_code, 200)
        self.assertEqual(reset.data['method'], 'totp')
=======
        setup = self.client.post('/api/totp/setup/', {}, format='json')
        self.assertEqual(setup.status_code, 200)
        mock_verify_totp.return_value = True
        verify = self.client.post('/api/totp/verify/', {'otp': '123456'}, format='json')
        self.assertEqual(verify.status_code, 200)
        self.client.force_authenticate(user=None)
        reset = self.client.post('/api/password-reset/totp/', {'username': 'totp-user', 'otp': '123456'}, format='json')
        self.assertEqual(reset.status_code, 200)
>>>>>>> 976cc83ad358ca0afbd53314dddde500db23c137

    def test_totp_password_reset_with_real_generated_code(self):
        user = User.objects.create_user(username='real-totp', password='StrongPass123')
        UserProfile.objects.create(user=user)
        self.client.force_authenticate(user=user)
<<<<<<< HEAD

        setup = self.client.post('/api/totp/setup/', {}, format='json')
        self.assertEqual(setup.status_code, 200)
        secret = setup.data['secret']

        verify_response = self.client.post('/api/totp/verify/', {'otp': build_totp_code(secret)}, format='json')
        self.assertEqual(verify_response.status_code, 200)

        self.client.force_authenticate(user=None)
        reset = self.client.post(
            '/api/password-reset/totp/',
            {'username': 'real-totp', 'otp': build_totp_code(secret)},
            format='json',
        )
        self.assertEqual(reset.status_code, 200)
        self.assertEqual(reset.data['method'], 'totp')
=======
        setup = self.client.post('/api/totp/setup/', {}, format='json')
        secret = setup.data['secret']
        verify_response = self.client.post('/api/totp/verify/', {'otp': build_totp_code(secret)}, format='json')
        self.assertEqual(verify_response.status_code, 200)
        self.client.force_authenticate(user=None)
        reset = self.client.post('/api/password-reset/totp/', {'username': 'real-totp', 'otp': build_totp_code(secret)}, format='json')
        self.assertEqual(reset.status_code, 200)
>>>>>>> 976cc83ad358ca0afbd53314dddde500db23c137
