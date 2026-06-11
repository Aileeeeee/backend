from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [
    path('signup/', views.SignupView.as_view()),
    path('login/', views.LoginView.as_view()),
    path('logout/', views.LogoutView.as_view()),
    path('profile/', views.ProfileView.as_view()),
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('organisations/search/', views.OrganisationSearchView.as_view()),
    path('username-suggestions/', views.UsernameAvailabilityView.as_view()),
]
