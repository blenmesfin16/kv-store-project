from django.urls import path
from core import views

urlpatterns = [
    path('set/<str:key>/', views.set_key),
    path('get/<str:key>/', views.get_key),
    path('_internal_set/<str:key>/', views.internal_set),
    path('ping/', views.ping),
    path('join/', views.join_cluster),
    path('get_all_keys/', views.get_all_keys),
    path('recover/', views.recover),
]