from django.urls import path
from . import views

urlpatterns = [
    path('receive/',        views.SMSReceiveView.as_view()),
    path('ussd/stealth/',   views.StealthPulseView.as_view()),
    path('ussd/', views.USSDView.as_view(), name='ussd'),
]