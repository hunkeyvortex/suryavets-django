from django import template
from decimal import Decimal, InvalidOperation

register = template.Library()


@register.filter
def money(value):
    """Group exact Decimal prices without converting money to binary floats."""
    try:
        amount = Decimal(str(value))
        return format(amount, ',.2f') if amount.is_finite() else ''
    except (ValueError, TypeError, InvalidOperation):
        return ''

@register.filter
def multiply(value, arg):
    """Multiply value by arg"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0
