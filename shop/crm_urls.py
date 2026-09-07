from django.urls import path
from . import crm_views as views
from . import crm_catalog_views as catalog

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
    path('inventory/new/', catalog.product_create, name='product_create'),
    path('inventory/<uuid:pk>/edit/', catalog.product_edit, name='product_edit'),
    path('inventory/<uuid:pk>/archive/', catalog.product_archive, name='product_archive'),
    path('inventory/<uuid:pk>/packs/<int:variant_id>/edit/', catalog.variant_edit, name='variant_edit'),
    path('inventory/<uuid:pk>/packs/new/', catalog.variant_edit, name='variant_create'),
    path('inventory/<uuid:pk>/images/<int:image_id>/', catalog.image_edit, name='image_edit'),
    path('inventory/<uuid:pk>/', views.inventory_detail, name='inventory_detail'),
    path('inventory/<uuid:pk>/variants/<int:variant_id>/', views.inventory_detail, name='variant_detail'),
    path('reports/', views.reports, name='reports'),
    path('coupons/', views.coupons, name='coupons'),
    path('coupons/new/', views.coupon_edit, name='coupon_create'),
    path('coupons/<int:pk>/', views.coupon_edit, name='coupon_edit'),
]
