import django_filters as filters
from django import forms
from main.views.firm.filters import SearchFilter
from .models import Campaign, TargetUser

ATTRS_ONCHANGE= {'onchange': 'this.form.submit();'}

class CampaignFilterSet(filters.FilterSet):
    search = SearchFilter(widget=forms.TextInput(
        attrs=dict({'placeholder': 'Search...'}, **ATTRS_ONCHANGE)),
        lookup_fields=['title', 'search_term'])

    class Meta:
        model = Campaign
        fields = ['search']

class TargetUserFilterSet(filters.FilterSet):
    search = SearchFilter(widget=forms.TextInput(
        attrs=dict({'placeholder': 'Search...'}, **ATTRS_ONCHANGE)),
        lookup_fields=['twitter_username', 'twitter_display_name'])

    class Meta:
        model = TargetUser
        fields = ['search']
