from django.template import Library
from django.utils.safestring import mark_safe
from django.contrib.humanize.templatetags.humanize import intcomma
from django.utils.timezone import now
from client.models import Client, ClientAccount
import time

register = Library()


#example: {{ field|css:'active' }}
@register.filter(name='css')
def css(field, value):
    return field.as_widget(attrs={'class': value})


#example: {{ value|percantage100:2 }}
@register.filter
def percentage100(value, decimals=2):
    try:
        return ('%.' + str(decimals) + 'f') % (float(value) * 100) + '%'
    except ValueError:
        pass


#example: {{ value|percantage:2 }}
@register.filter
def percentage(value, decimals=2):
    try:
        return ('%.' + str(decimals) + 'f') % float(value) + '%'
    except ValueError:
        pass


#example: {{ value|currency:2:'$' }}
@register.filter
def currency(value, decimals=2, symbol='$'):
    try:
        value = round(float(value), decimals)
        if decimals > 0:
            return "%s%s%s" % (symbol, intcomma(int(value)), (("%0." + str(decimals) + "f") % value)[-(decimals+1):])
        else:
            return "%s%s" % (symbol, intcomma(int(value)))
    except (ValueError, TypeError):
        return ''


#example: {{ birthday|age }}
@register.filter
def age(birthday, d=None):
    if d is None:
        d = now().today()
    return (d.year - birthday.year) - int((d.month, d.day) < (birthday.month, birthday.day))


@register.filter
def phone(value):
    if not value:
        return ''

    return value


# example: {{ request.resolver_match.view_name|menu_active:'url-name-a, url-name-b, url-name-c' }}
@register.filter
def menu_active(value, url_names=''):
    url_names = url_names.replace(' ', '').split(',')
    return 'active' if value in url_names else ''

@register.filter
def index(ary, i):
    return ary[int(i)]

@register.filter
def account_type_text(acc_type):
    return ClientAccount.get_account_type_text(acc_type)

@register.filter
def occupation_text(occupation):
    return Client.get_occupation_text(occupation)

@register.filter
def employment_status_text(employment_status):
    return Client.get_employment_status_text(employment_status)

@register.filter
def employer_type_text(employer_type):
    return Client.get_employer_type_text(employer_type)

@register.filter
def filing_status_text(filing_status):
    return Client.get_filing_status_text(filing_status)

@register.filter
def to_class_name(value):
    return value.__class__.__name__

@register.filter
def to_isoformat(dt):
    return dt.strftime('%Y-%m-%d %H:%M:%S')

#example: {{ items|sum_percent:2 }}
@register.filter
def sum_percent(items, upto_index):
    total = 0
    for i in range(upto_index - 1):
        total += items[i]['percent']
    return total
