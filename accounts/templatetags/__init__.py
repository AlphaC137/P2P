from django import template
from django.template.defaultfilters import floatformat
from decimal import Decimal

register = template.Library()

@register.filter
def currency(value, symbol='R'):
    """
    Format a value as currency with the given symbol.
    
    Example usage: {{ value|currency }} or {{ value|currency:'$' }}
    """
    if value is None:
        return ''
    
    try:
        value = Decimal(value)
        return f"{symbol}{floatformat(value, 2)}"
    except (ValueError, TypeError):
        return ''
