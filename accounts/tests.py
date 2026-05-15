# accounts/tests.py

from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from accounts.models import NGOUser, Organisation


class OrganisationSetup:
    """
    Shared helper — creates a test organisation once.
    Every test class that needs an organisation inherits this.
    """
    @classmethod
    def create_organisation(cls):
        return Organisation.objects.create(
            name='WARIF',
            city='Lagos',
            state='Lagos',
            phone='08012345678',
            email='info@warif.org',
        )


class SignupTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.url = '/api/auth/signup/'
        self.org = Organisation.objects.create(
            name='WARIF',
            city='Lagos',
            state='Lagos',
        )
        self.valid_data = {
            'username': 'david_warif',
            'email': 'david@warif.org',
            'password': 'securepass123',
            'organisation_id': self.org.id,
            'role': 'COORDINATOR',
        }

    def test_signup_valid_data_returns_201(self):
        response = self.client.post(self.url, self.valid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_signup_returns_token(self):
        response = self.client.post(self.url, self.valid_data, format='json')
        self.assertIn('tokens', response.data)
        self.assertTrue(len(response.data['tokens']['access']) > 0)

    def test_signup_returns_user_profile(self):
        response = self.client.post(self.url, self.valid_data, format='json')
        self.assertIn('user', response.data)
        self.assertEqual(response.data['user']['username'], 'david_warif')
        self.assertEqual(response.data['user']['role'], 'COORDINATOR')

    def test_signup_links_organisation(self):
        self.client.post(self.url, self.valid_data, format='json')
        user = NGOUser.objects.get(username='david_warif')
        self.assertEqual(user.organisation.name, 'WARIF')

    def test_signup_missing_password_returns_400(self):
        bad_data = self.valid_data.copy()
        bad_data.pop('password')
        response = self.client.post(self.url, bad_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_signup_invalid_organisation_returns_400(self):
        bad_data = self.valid_data.copy()
        bad_data['organisation_id'] = 99999
        response = self.client.post(self.url, bad_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_signup_duplicate_username_returns_400(self):
        self.client.post(self.url, self.valid_data, format='json')
        response = self.client.post(self.url, self.valid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_signup_short_password_returns_400(self):
        bad_data = self.valid_data.copy()
        bad_data['password'] = '123'
        response = self.client.post(self.url, bad_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class LoginTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.url = '/api/auth/login/'
        self.org = Organisation.objects.create(
            name='WARIF',
            city='Lagos',
            state='Lagos',
        )
        self.user = NGOUser.objects.create_user(
            username='david_warif',
            password='securepass123',
            organisation=self.org,
            role='COORDINATOR',
        )

    def test_login_valid_credentials_returns_200(self):
        response = self.client.post(self.url, {
            'username': 'david_warif',
            'password': 'securepass123',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_login_returns_token(self):
        response = self.client.post(self.url, {
            'username': 'david_warif',
            'password': 'securepass123',
        }, format='json')
        self.assertIn('tokens', response.data)
        self.assertIn('access', response.data['tokens'])

    def test_login_returns_user_data(self):
        response = self.client.post(self.url, {
            'username': 'david_warif',
            'password': 'securepass123',
        }, format='json')
        self.assertIn('user', response.data)
        self.assertEqual(response.data['user']['username'], 'david_warif')

    def test_login_wrong_password_returns_401(self):
        response = self.client.post(self.url, {
            'username': 'david_warif',
            'password': 'wrongpassword',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_wrong_username_returns_401(self):
        response = self.client.post(self.url, {
            'username': 'nobody',
            'password': 'securepass123',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_missing_fields_returns_400(self):
        response = self.client.post(self.url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class LogoutTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.org = Organisation.objects.create(
            name='WARIF',
            city='Lagos',
            state='Lagos',
        )
        self.user = NGOUser.objects.create_user(
            username='david_warif',
            password='securepass123',
            organisation=self.org,
            role='COORDINATOR',
        )
        # Log in and get token
        response = self.client.post('/api/auth/login/', {
            'username': 'david_warif',
            'password': 'securepass123',
        }, format='json')
        
        self.token = response.data['tokens']['access']

        self.refresh_token = response.data['tokens']['refresh']

    def test_logout_with_valid_token_returns_200(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
        response = self.client.post('/api/auth/logout/', 
        {'refresh': self.refresh_token}, 
        format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_logout_without_token_returns_401(self):
        response = self.client.post('/api/auth/logout/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_token_invalid_after_logout(self):

        # 1. Log in to get a fresh set of tokens
        login_response = self.client.post('/api/auth/login/', {
            'username': 'david_warif',
            'password': 'securepass123',
        }, format='json')
        
        access_token = login_response.data['tokens']['access']
        refresh_token = login_response.data['tokens']['refresh']
        
        # 2. Authenticate the client using the Access Token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        # 3. Trigger logout by passing the refresh token to the blacklist
        logout_response = self.client.post('/api/auth/logout/', {'refresh': refresh_token}, format='json')
        self.assertEqual(logout_response.status_code, status.HTTP_200_OK)
        
        # 4. Clear credentials to act as a clean user attempt
        self.client.credentials()
        
        # 5. TRY TO REFRESH: Attempt to get a new access token using the blacklisted refresh token
        refresh_response = self.client.post('/api/auth/refresh/', {'refresh': refresh_token}, format='json')
        
        # This must fail now because the refresh token is blacklisted!
        self.assertEqual(refresh_response.status_code, status.HTTP_401_UNAUTHORIZED)


class ProfileTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.org = Organisation.objects.create(
            name='WARIF',
            city='Lagos',
            state='Lagos',
        )
        self.user = NGOUser.objects.create_user(
            username='david_warif',
            password='securepass123',
            organisation=self.org,
            role='COORDINATOR',
        )
        response = self.client.post('/api/auth/login/', {
            'username': 'david_warif',
            'password': 'securepass123',
        }, format='json')
        
        self.token = response.data['tokens']['access']

    def test_profile_with_token_returns_200(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
        response = self.client.get('/api/auth/profile/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_profile_returns_correct_data(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
        response = self.client.get('/api/auth/profile/')
        self.assertEqual(response.data['username'], 'david_warif')
        self.assertEqual(response.data['role'], 'COORDINATOR')
        self.assertEqual(response.data['organisation']['name'], 'WARIF')
        self.assertEqual(response.data['organisation']['city'], 'Lagos')

    def test_profile_without_token_returns_401(self):
        response = self.client.get('/api/auth/profile/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class PermissionsTest(TestCase):
    """
    Tests that field staff cannot access coordinator-only endpoints.
    """

    def setUp(self):
        self.client = APIClient()
        self.org = Organisation.objects.create(
            name='WARIF',
            city='Lagos',
            state='Lagos',
        )
        # Create a field staff user
        self.field_staff = NGOUser.objects.create_user(
            username='amaka_warif',
            password='securepass123',
            organisation=self.org,
            role='FIELD_STAFF',
        )
        # Create a coordinator
        self.coordinator = NGOUser.objects.create_user(
            username='david_warif',
            password='securepass123',
            organisation=self.org,
            role='COORDINATOR',
        )


    def get_token(self, username, password):
        response = self.client.post('/api/auth/login/', {
            'username': username,
            'password': password,
        }, format='json')
        return response.data['tokens']['access']

    def test_coordinator_can_access_coordinator_dashboard(self):
        token = self.get_token('david_warif', 'securepass123')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = self.client.get('/api/coordinator-dashboard/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_field_staff_cannot_access_coordinator_dashboard(self):
        token = self.get_token('amaka_warif', 'securepass123')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = self.client.get('/api/coordinator-dashboard/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_field_staff_can_access_ngo_dashboard(self):
        token = self.get_token('amaka_warif', 'securepass123')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = self.client.get('/api/dashboard/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_unauthenticated_user_cannot_access_dashboard(self):
        response = self.client.get('/api/dashboard/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
