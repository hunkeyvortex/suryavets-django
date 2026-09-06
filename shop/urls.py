from django.urls import path, re_path
from . import catalog_views, views

app_name = 'shop'

urlpatterns = [
    # Home
    path('', views.index, name='index'),
    
    # Categories - Custom slug pattern to allow & character
    path('categories/', catalog_views.product_list, name='category_list'),
    re_path(r'^category/(?P<category_slug>[-a-zA-Z0-9_&]+)/$', catalog_views.category_detail, name='category_detail'),
    re_path(r'^category/(?P<category_slug>[-a-zA-Z0-9_&]+)/(?P<subcategory_slug>[-a-zA-Z0-9_&]+)/$', catalog_views.subcategory_detail, name='subcategory_detail'),
    
    # Products
    re_path(r'^product/(?P<product_slug>[-a-zA-Z0-9_&]+)/$', catalog_views.product_detail, name='product_detail'),
    path('product/<uuid:product_id>/add/', views.add_to_cart, name='add_to_cart'),
    
    # Cart
    path('cart/', views.cart_detail, name='cart'),
    path('cart/update/<int:item_id>/', views.update_cart_item, name='update_cart_item'),
    path('cart/remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    
    # Checkout
    path('checkout/', views.checkout, name='checkout'),
    
    # Search
    path('search/', catalog_views.product_search, name='search'),
    
    # Authentication
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('account/', views.profile_view, name='profile'),
    path('account/addresses/', views.addresses_view, name='addresses'),
    path('account/orders/<uuid:order_id>/', views.order_detail, name='order_detail'),
    
    # Informational pages
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('help/', views.help, name='help'),
    path('shipping/', views.shipping, name='shipping'),
    path('privacy/', views.privacy, name='privacy'),
    path('terms/', views.terms, name='terms'),
    path('returns/', views.returns, name='returns'),
    
    # Newsletter
    path('newsletter/', views.newsletter_signup, name='newsletter_signup'),
]
