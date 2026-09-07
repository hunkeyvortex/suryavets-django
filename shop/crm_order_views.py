from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from .crm_views import staff_page, page_context
from .account_forms import ReviewForm, SupportReplyForm
from .models import Order, SupportRequest, CRMActivity
from .services.order_tracking import update_review
from .services.crm import CRMError


@staff_page('manage_crm_orders')
@require_POST
def review(request, pk):
    get_object_or_404(Order, pk=pk)
    form = ReviewForm(request.POST)
    if form.is_valid():
        try:
            update_review(request.user, pk, **form.cleaned_data)
            messages.success(request, 'Review recorded. No payment transfer or automatic restocking was performed.')
        except CRMError as error:
            messages.error(request, str(error))
    else:
        messages.error(request, 'Enter a valid review outcome and note.')
    return redirect('crm:order_detail', pk=pk)


@staff_page()
def support(request):
    rows = SupportRequest.objects.select_related('user', 'order')
    if request.GET.get('state') in ('open', 'resolved'):
        rows = rows.filter(state=request.GET['state'])
    return render(request, 'crm/support.html', {**page_context(request, rows), 'title': 'Customer support', 'section': 'support'})


@staff_page('write_crm_notes')
@transaction.atomic
def support_detail(request, pk):
    ticket = get_object_or_404(SupportRequest.objects.select_for_update(), pk=pk)
    form = SupportReplyForm(request.POST or None, instance=ticket)
    if request.method == 'POST' and form.is_valid():
        form.save(commit=False)
        ticket.responded_by = request.user; ticket.responded_at = timezone.now(); ticket.save()
        CRMActivity.objects.create(actor=request.user, order=ticket.order, kind='note', text=f'Support request #{ticket.pk}: customer-visible reply saved; state {ticket.state}.')
        messages.success(request, 'Reply saved and visible in the customer account.')
        return redirect('crm:support')
    return render(request, 'crm/support_detail.html', {'title': f'Support #{ticket.pk}', 'section': 'support', 'ticket': ticket, 'form': form})
