from django.template.defaultfilters import floatformat
from django.utils.safestring import mark_safe

from django import template

register = template.Library()


@register.filter
def display(value, field_prefix=None):
    """
    Format pricing plan fields
    """
    try:
        bps = getattr(value, '%s_bps' % field_prefix if field_prefix else 'bps')
        fixed = getattr(value, '%s_fixed' % field_prefix if field_prefix else 'fixed')
        parts = []
        if bps:
            parts.append('<span class="bps">%.0f</span> bps' % bps)
        if fixed:
            parts.append('$<span class="fixed">%s</span>' % floatformat(fixed, 2))
        return mark_safe(', '.join(parts) or 'Free')
    except Exception as e:
        print(e)

@register.filter(name='widget_class')
def widget_class(field, css_class):
   return field.as_widget(attrs={"class":css_class})
