"""Owned account data only; no contact-email-based access to historical guest orders."""
from functools import wraps
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.core.paginator import Paginator
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST
from .models import CustomerAddress, CustomerPet, WishlistItem, Product, Order
from .account_forms import SavedAddressForm, PetForm, ProfileForm, SupportForm
from .services.order_tracking import tracker, customer_can_cancel, record_event
from .services.crm import transition_order, CRMError
from .services.reorder import buy_again


def account_page(view):
    @wraps(view)
    @login_required
    @never_cache
    def wrapped(request, *args, **kwargs):
        response = view(request, *args, **kwargs)
        response['Cache-Control'] = 'private, no-store'
        response['X-Robots-Tag'] = 'noindex, nofollow'
        return response
    return wrapped


def show(request, template, title, **context):
    return render(request, 'account/' + template + '.html', {'title': title, **context})


@account_page
def dashboard(request):
    return show(request, 'dashboard', 'My account', orders=request.user.orders.prefetch_related('items')[:3],
                order_count=request.user.orders.count(), pet_count=request.user.pets.count(), wishlist_count=request.user.wishlist.count())


@account_page
def orders(request):
    return show(request, 'orders', 'My orders', page=Paginator(request.user.orders.prefetch_related('items'), 10).get_page(request.GET.get('page')))


@account_page
def order_detail(request, order_id=None, number=None):
    order = get_object_or_404(request.user.orders.prefetch_related('items'), **({'pk': order_id} if order_id else {'order_number': number}))
    return show(request, 'order_detail', order.order_number, order=order, stages=tracker(order),
                events=order.events.filter(customer_visible=True), can_cancel=customer_can_cancel(order))


@account_page
@require_POST
def reorder(request, order_id):
    get_object_or_404(request.user.orders, pk=order_id)
    added, skipped = buy_again(request.user, order_id)
    if added: messages.success(request, f'{added} items added at current prices. Please review your basket before checkout.')
    for warning in skipped: messages.warning(request, warning)
    return redirect('shop:cart')


@account_page
@require_POST
def cancel(request, order_id):
    order = get_object_or_404(request.user.orders, pk=order_id)
    if not customer_can_cancel(order):
        messages.error(request, 'This order cannot be cancelled automatically. Contact support for review.')
    else:
        try:
            transition_order(request.user, order.pk, order.status, 'cancelled', 'Customer requested cancellation', customer=True,
                             customer_note='You cancelled this order. No payment refund was issued by this action.')
            messages.success(request, 'Order cancelled. No refund was issued by this action.')
        except CRMError as error:
            messages.error(request, str(error))
    return redirect('shop:order_detail', order_id=order.pk)


@account_page
@require_POST
@transaction.atomic
def request_return(request, order_id):
    order = get_object_or_404(Order.objects.select_for_update(), pk=order_id, user=request.user)
    reason = request.POST.get('reason', '').strip()
    if order.status != 'delivered' or order.return_status or not 3 <= len(reason) <= 1000:
        messages.error(request, 'Returns require a delivered order, a reason, and no previous return review. Contact support for help.')
    else:
        order.return_status = 'requested'
        order.save(update_fields=['return_status', 'updated_at'])
        record_event(order, 'requested', kind='return', actor=request.user, customer_note=reason)
        messages.success(request, 'Return review requested. Eligibility and any refund require staff approval.')
    return redirect('shop:order_detail', order_id=order.pk)


@account_page
def addresses(request, pk=None):
    instance = get_object_or_404(request.user.addresses, pk=pk) if pk else None
    form = SavedAddressForm(request.POST or None, instance=instance)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            # Serialize default changes for this user, including the first address.
            get_user_model().objects.select_for_update().get(pk=request.user.pk)
            address = form.save(commit=False)
            address.user = request.user
            if address.is_default_shipping: request.user.addresses.update(is_default_shipping=False)
            address.save()
        messages.success(request, 'Address saved.')
        return redirect('shop:addresses')
    return show(request, 'addresses', 'Saved addresses', form=form, addresses=request.user.addresses.all())


@account_page
@require_POST
@transaction.atomic
def address_action(request, pk, action):
    get_user_model().objects.select_for_update().get(pk=request.user.pk)
    address = get_object_or_404(request.user.addresses, pk=pk)
    if action == 'delete': address.delete()
    elif action == 'default':
        request.user.addresses.update(is_default_shipping=False)
        address.is_default_shipping = True
        address.save(update_fields=['is_default_shipping'])
    return redirect('shop:addresses')


@account_page
def pets(request, pk=None):
    instance = get_object_or_404(request.user.pets, pk=pk) if pk else None
    form = PetForm(request.POST or None, instance=instance)
    if request.method == 'POST' and form.is_valid():
        pet = form.save(commit=False); pet.user = request.user; pet.save()
        messages.success(request, 'Pet profile saved.')
        return redirect('shop:pets')
    return show(request, 'pets', 'My pets', form=form, pets=request.user.pets.select_related('pet_type'))


@account_page
@require_POST
def pet_delete(request, pk):
    get_object_or_404(request.user.pets, pk=pk).delete()
    return redirect('shop:pets')


@account_page
def wishlist(request):
    rows = request.user.wishlist.select_related('product', 'product__brand', 'product__product_type').prefetch_related('product__images', 'product__variants', 'product__family_members__variants', 'product__family_members__images')
    return show(request, 'wishlist', 'Wishlist', page=Paginator(rows, 12).get_page(request.GET.get('page')))


@account_page
@require_POST
def wishlist_save(request, product_id):
    product = get_object_or_404(Product, pk=product_id, is_active=True)
    WishlistItem.objects.get_or_create(user=request.user, product=product)
    messages.success(request, 'Saved to your wishlist.')
    return redirect('shop:wishlist')


@account_page
@require_POST
def wishlist_delete(request, pk):
    get_object_or_404(request.user.wishlist, pk=pk).delete()
    return redirect('shop:wishlist')


@account_page
def profile(request):
    form = ProfileForm(request.POST or None, instance=request.user)
    if request.method == 'POST' and form.is_valid():
        form.save(); messages.success(request, 'Profile updated.')
        return redirect('shop:profile_edit')
    return show(request, 'form', 'Profile', form=form, intro='Your contact details. Email changes require identity verification through support.')


@account_page
def security(request):
    form = PasswordChangeForm(request.user, request.POST or None) if request.user.has_usable_password() else None
    if request.method == 'POST' and form and form.is_valid():
        user = form.save(); update_session_auth_hash(request, user)
        messages.success(request, 'Password changed. Other sessions must sign in again.')
        return redirect('shop:security')
    return show(request, 'form', 'Account security', form=form, intro='Change your password using your current password. If your account has no password, contact support; never share a password or OTP.')


@account_page
def support(request):
    form = SupportForm(request.POST or None, user=request.user)
    if request.method == 'POST' and form.is_valid():
        ticket = form.save(commit=False); ticket.user = request.user; ticket.save()
        messages.success(request, 'Your request has been saved for our team.')
        return redirect('shop:support')
    return show(request, 'support', 'Help & support', form=form,
                page=Paginator(request.user.support_requests.select_related('order'), 10).get_page(request.GET.get('page')))
