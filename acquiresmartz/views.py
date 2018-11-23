from django.shortcuts import render
from django.core.exceptions import ObjectDoesNotExist
from django.views.generic import (CreateView, DeleteView, DetailView, ListView,
                                  TemplateView, UpdateView)
from .filters import CampaignFilterSet, TargetUserFilterSet
from .forms import CampaignForm, TargetUserForm
from .ibm_watson import get_tweets_list_in_campaign
from .models import Campaign, PersonalityInsight, TargetUser
from django.contrib import messages
from django.core.urlresolvers import reverse
from main.views.base import LegalView

class FirmAcquireSmartzLeads(ListView, LegalView):
    template_name = 'firm/acquiresmartz-leads.html'
    model = Campaign

    def get_context_data(self, **kwargs):
        ctx = super(FirmAcquireSmartzLeads, self).get_context_data(**kwargs)
        campaign_filter = CampaignFilterSet(self.request.GET,
                                            queryset=Campaign.objects.filter(firm=self.firm))
        if 'pk' in self.kwargs:
            pk = int(self.kwargs['pk'])
            try:
                campaign = Campaign.objects.get(pk=pk)
                tweets = get_tweets_list_in_campaign(campaign)
                target_twitter_ids = TargetUser.objects.all().values_list('twitter_id', flat=True)
                for item in tweets:
                    item['is_target_user'] = item['twitter_id'] in target_twitter_ids
            except ObjectDoesNotExist:
                tweets = None
        else:
            pk = None
            tweets = None

        ctx.update({
            'pk': pk,
            'campaign_filter': campaign_filter,
            'tweets': tweets
        })
        return ctx


class FirmAcquireSmartzCampaignNew(CreateView, LegalView):
    template_name = 'firm/acquiresmartz-campaign.html'
    model = Campaign
    form_class = CampaignForm

    def get_success_url(self):
        messages.success(self.request, "New campaign added successfully")
        return reverse('firm:acquiresmartz:leads')


class FirmAcquireSmartzCampaignEdit(UpdateView, LegalView):
    template_name = 'firm/acquiresmartz-campaign.html'
    model = Campaign
    form_class = CampaignForm

    def get_success_url(self):
        messages.success(self.request, "Your campaign updated successfully")
        return reverse('firm:acquiresmartz:leads')


class FirmAcquireSmartzTargets(ListView, LegalView):
    template_name = 'firm/acquiresmartz-targets.html'
    model = TargetUser

    def get_context_data(self, **kwargs):
        ctx = super(FirmAcquireSmartzTargets, self).get_context_data(**kwargs)
        campaign_filter = CampaignFilterSet(self.request.GET,
                                            queryset=Campaign.objects.filter(firm=self.firm))
        qs = self.get_queryset()

        if 'pk' in self.kwargs:
            pk = int(self.kwargs['pk'])
            qs = qs.filter(campaign_id=pk)
        else:
            pk = None

        target_user_filter = TargetUserFilterSet(self.request.GET, queryset=qs)

        ctx.update({
            'pk': pk,
            'campaign_filter': campaign_filter,
            'target_user_filter': target_user_filter
        })
        return ctx


class FirmAcquireSmartzAddTargetUser(CreateView, LegalView):
    template_name = 'firm/acquiresmartz-targets.html'
    model = TargetUser
    form_class = TargetUserForm

    def get_success_url(self):
        messages.success(self.request, "New target user added successfully")
        return reverse('firm:acquiresmartz:targets')

    def get(self, **kwargs):
        return reverse('firm:acquiresmartz:targets')


class FirmAcquireSmartzPersonalityInsights(DetailView, LegalView):
    template_name = 'firm/acquiresmartz-personality-insights.html'
    model = TargetUser

    def get_context_data(self, **kwargs):
        ctx = super(FirmAcquireSmartzPersonalityInsights, self).get_context_data(**kwargs)
        pk = self.kwargs.get("pk", None)
        target_user = TargetUser.objects.get(pk=pk)
        ctx.update({"personality_insights": target_user.get_personality_insight_data()})
        return ctx


class FirmAcquireSmartzCognitics(TemplateView, LegalView):
    template_name = 'firm/acquiresmartz-cognitics.html'
    model = TargetUser
    form_class = TargetUserForm

    def get_context_data(self, **kwargs):
        ctx = super(FirmAcquireSmartzCognitics, self).get_context_data(**kwargs)
        campaign_filter = CampaignFilterSet(self.request.GET,
                                            queryset=Campaign.objects.filter(firm=self.firm))
        if 'pk' in self.kwargs:
            pk = int(self.kwargs['pk'])
        else:
            pk = None

        ctx.update({
            'pk': pk,
            'campaign_filter': campaign_filter
        })
        return ctx
