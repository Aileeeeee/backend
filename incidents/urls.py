from django.urls import path, include
from . import views



urlpatterns = [
    path('incidents/', views.IncidentListView.as_view()),
    path('incidents/<int:pk>/', views.IncidentDetailView.as_view()),
    path('incidents/submit/', views.IncidentSubmitView.as_view()),
    path('incidents/stats/', views.IncidentStatsView.as_view()),
    path('incidents/<int:pk>/acknowledge/', views.AcknowledgeIncidentView.as_view()),
    path('dashboard/', views.NGODashboardView.as_view()),
    path('coordinator-dashboard/', views.CoordinatorDashboardView.as_view()),
    path('users/register/', views.RegisterDeviceView.as_view()),
    path('contacts/', views.TrustedContactListCreateView.as_view()),
    path('contacts/<int:pk>/', views.TrustedContactDeleteView.as_view()),
]