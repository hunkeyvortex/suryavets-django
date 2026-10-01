from django.urls import path, re_path, reverse_lazy
from django.contrib.auth import views as auth_views
from . import public_views
from . import catalog_views, views, account_views as account
from . import payment_views

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
    path('checkout/payment/<uuid:order_id>/', payment_views.payment, name='payment'),
    path('payments/razorpay/webhook/', payment_views.webhook, name='razorpay_webhook'),
    path('checkout/confirmation/<uuid:order_id>/', views.order_confirmation, name='order_confirmation'),
    
    # Search
    path('search/', catalog_views.product_search, name='search'),
    
    # Authentication
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('account/', account.dashboard, name='profile'),
    path('account/orders/', account.orders, name='orders'),
    path('account/orders/<uuid:order_id>/', account.order_detail, name='order_detail'),
    path('account/orders/<uuid:order_id>/reorder/', account.reorder, name='reorder'),
    path('account/orders/<uuid:order_id>/cancel/', account.cancel, name='cancel_order'),
    path('account/orders/<uuid:order_id>/return/', account.request_return, name='request_return'),
    path('account/orders/<str:number>/', account.order_detail, name='order_number'),
    path('account/addresses/', account.addresses, name='addresses'),
    path('account/addresses/<int:pk>/edit/', account.addresses, name='address_edit'),
    path('account/addresses/<int:pk>/<str:action>/', account.address_action, name='address_action'),
    path('account/pets/', account.pets, name='pets'),
    path('account/pets/<int:pk>/edit/', account.pets, name='pet_edit'),
    path('account/pets/<int:pk>/delete/', account.pet_delete, name='pet_delete'),
    path('account/wishlist/', account.wishlist, name='wishlist'),
    path('account/wishlist/save/<uuid:product_id>/', account.wishlist_save, name='wishlist_save'),
    path('account/wishlist/<int:pk>/delete/', account.wishlist_delete, name='wishlist_delete'),
    path('account/profile/', account.profile, name='profile_edit'),
    path('account/security/', account.security, name='security'),
    path('account/support/', account.support, name='support'),
    
    # Informational pages
    path('about/', views.about, name='about'),
    path('contact/', public_views.contact, name='contact'),
    path('help/', views.help, name='help'),
    path('shipping/', views.shipping, name='shipping'),
    path('privacy/', views.privacy, name='privacy'),
    path('terms/', views.terms, name='terms'),
    path('returns/', views.returns, name='returns'),
    
    # Newsletter
    path('newsletter/', public_views.newsletter, name='newsletter_signup'),
    path('password-reset/', public_views.SafePasswordResetView.as_view(), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='registration/reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='registration/reset_confirm.html', success_url=reverse_lazy('shop:password_reset_complete')), name='password_reset_confirm'),
    path('reset/complete/', auth_views.PasswordResetCompleteView.as_view(template_name='registration/reset_complete.html'), name='password_reset_complete'),
]
