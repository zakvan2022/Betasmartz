from django.contrib import admin
from django.contrib.sites.models import Site
from .models import Config, FiscalYear

try:
    admin.site.unregister(Site)
except NotRegistered:
    pass

class ConfigInline(admin.StackedInline):
    model = Config
    extra = 0

class SiteAdmin(admin.ModelAdmin):
	list_display = ('domain', 'name',)
	inlines = (ConfigInline,)


class FiscalYearAdmin(admin.ModelAdmin):
    model = FiscalYear


admin.site.register(Site, SiteAdmin)
admin.site.register(FiscalYear, FiscalYearAdmin)