from django.urls import path
from . import crm_views as views

app_name = 'crm'
urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('login/', views.StaffLoginView.as_view(), name='login'),
    path('logout/', views.StaffLogoutView.as_view(), name='logout'),
    path('orders/', views.orders, name='orders'),
    path('orders/<uuid:pk>/', views.order_detail, name='order_detail'),
    path('orders/<uuid:pk>/status/', views.order_status, name='order_status'),
    path('orders/<uuid:pk>/notes/', views.order_note, name='order_note'),
    path('customers/', views.customers, name='customers'),
    path('customers/<str:key>/', views.customer_detail, name='customer_detail'),
    path('customers/<str:key>/notes/', views.customer_note, name='customer_note'),
    path('inventory/', views.inventory, name='inventory'),
    path('inventory/<uuid:pk>/', views.inventory_detail, name='inventory_detail'),
    path('inventory/<uuid:pk>/variants/<int:variant_id>/', views.inventory_detail, name='variant_detail'),
    path('reports/', views.reports, name='reports'),
]
