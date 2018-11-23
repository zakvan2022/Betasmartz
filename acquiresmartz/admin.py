from django.contrib import admin
from .models import Campaign, PersonalityInsight, TargetUser

class CampaignAdmin(admin.ModelAdmin):
    list_display = ('title', 'search_term', 'firm')

class PersonalityInsightInline(admin.StackedInline):
    model = PersonalityInsight

class TargetUserAdmin(admin.ModelAdmin):
    list_display = ('twitter_username', 'campaign', 'twitter_id')
    inlines = (PersonalityInsightInline,)

admin.site.register(TargetUser, TargetUserAdmin)
admin.site.register(Campaign, CampaignAdmin)
