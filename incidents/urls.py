from django.urls import path, include
from incidents.views import IncidentListView, AcknowledgeIncidentView


urlpatterns = [
    path('incidents/', IncidentListView.as_view(),name='incident-list'),
    path('incidents/<int:pk>/acknowledge/', AcknowledgeIncidentView.as_view(), name='acknowledge-incident'),
]