from django.conf import settings
from django.contrib import admin
from django.shortcuts import HttpResponseRedirect, render_to_response
from genericadmin.admin import BaseGenericModelAdmin, GenericAdminModelAdmin
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from .models import Region, Address, USFips, USState, USZipcode


class RegionAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'country')


class AddressAdmin(admin.ModelAdmin):
    list_display = ('address', 'post_code', 'global_id', 'region')


class USStateAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'region')


class USFipsAdmin(admin.ModelAdmin):
    list_display = ('fips', 'county_name', 'rucc')


class USZipcodeAdmin(admin.ModelAdmin):
    list_display = ('zip_code', 'zip_name', 'fips', 'phone_area_code')


admin.site.register(Region, RegionAdmin)
admin.site.register(Address, AddressAdmin)
admin.site.register(USState, USStateAdmin)
admin.site.register(USFips, USFipsAdmin)
admin.site.register(USZipcode, USZipcodeAdmin)
