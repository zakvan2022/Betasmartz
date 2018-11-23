from django import forms
from django.http import QueryDict
from django.utils.safestring import mark_safe
from .models import Campaign, TargetUser

class CampaignForm(forms.ModelForm):
    required_css_class = 'required'

    description = forms.CharField()
    class Meta:
        model = Campaign
        fields = '__all__'

class TargetUserForm(forms.ModelForm):
    class Meta:
        model = TargetUser
        fields = '__all__'
