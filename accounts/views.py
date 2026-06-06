from django.contrib.auth import authenticate, get_user_model
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import SignupSerializer, UserProfileSerializer,OrganisationSerializer
from .models import Organisation

User = get_user_model()

# Helper function to generate tokens manually
def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }

class SignupView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        print("REQUEST DATA:", request.data)
        if serializer.is_valid():
            user = serializer.save()
            # 2. Use SimpleJWT tokens
            tokens = get_tokens_for_user(user)

            return Response({
                'tokens': tokens,
                'user': UserProfileSerializer(user).data,
                'message': 'Account created successfully.'
            }, status=status.HTTP_201_CREATED)
        print("SERIALIZER ERRORS:", serializer.errors)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        if not username or not password:
            return Response(
                {'error': 'Username and password are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = authenticate(username=username, password=password)

        if user:
            # 3. Use SimpleJWT tokens
            tokens = get_tokens_for_user(user)
            return Response({
                'tokens': tokens,
                'user': UserProfileSerializer(user).data,
            }, status=status.HTTP_200_OK)

        return Response(
            {'error': 'Invalid username or password.'},
            status=status.HTTP_401_UNAUTHORIZED
        )

class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()  # Destroys the refresh token's validity
            return Response({"message": "Successfully logged out."}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": "Invalid or missing refresh token."}, status=status.HTTP_400_BAD_REQUEST)

        # 4. Note: With SimpleJWT, "Logging out" on the server usually involves 
        # blacklisting the refresh token. If you haven't enabled the Blacklist app, 
        # the client simply deletes the token locally.

class ProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
class OrganisationSearchView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        query = request.query_params.get('q', '')
        if len(query) < 2:
            return Response([])
        orgs = Organisation.objects.filter(
            is_active=True,
            name__icontains=query
        )[:10]
        serializer = OrganisationSerializer(orgs, many=True)
        return Response(serializer.data)