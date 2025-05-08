from django import template
from django.template.defaultfilters import floatformat
from decimal import Decimal, InvalidOperation, ConversionSyntax

register = template.Library()

@register.filter
def currency(value, symbol='R'):
    """
    Format a value as currency with the given symbol.
    
    Example usage: {{ value|currency }} or {{ value|currency:'$' }}
    """
    if value is None or value == '':
        return ''
    
    try:
        # Handle values that are already decimal or float
        if isinstance(value, (Decimal, float, int)):
            formatted_value = floatformat(value, 2)
            return f"{symbol}{formatted_value}"
        
        # Try to convert string values to Decimal
        if isinstance(value, str):
            value = value.strip()
        
        value = Decimal(value)
        return f"{symbol}{floatformat(value, 2)}"
    except (ValueError, TypeError, InvalidOperation, ConversionSyntax):
        # Return just the symbol for error cases to avoid breaking the display
        return f"{symbol}0.00"
