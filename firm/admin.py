from django.contrib import admin
from .models import Firm, FirmConfig, FirmData, PricingPlan, \
    AuthorisedRepresentative, Supervisor, FirmEmailInvite


class FirmFilter(admin.SimpleListFilter):
    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options.
    title = 'filter by firm'

    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'firm'

    def lookups(self, request, model_admin):
        """
        Returns a list of tuples. The first element in each
        tuple is the coded value for the option that will
        appear in the URL query. The second element is the
        human-readable name for the option that will appear
        in the right sidebar.
        """
        list_id = [[None, "All"]]
        for firm in Firm.objects.all():
            list_id.append([firm.pk, firm.name])

        return list_id

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value
        provided in the query string and retrievable via
        `self.value()`.
        """
        # Compare the requested value (either '80s' or 'other')
        # to decide how to filter the queryset.

        if self.value() is None:
            return queryset.all()

        return queryset.filter(firm__pk=self.value())


def approve_application(modeladmin, request, queryset):
    for obj in queryset.all():
        obj.approve()


approve_application.short_description = "Approve application(s)"


def invite_advisor(modeladmin, request, queryset):
    context = {'STATIC_URL': settings.STATIC_URL, 'MEDIA_URL': settings.MEDIA_URL, 'item_class': 'firm'}

    if queryset.count() > 1:
        return render_to_response('admin/betasmartz/error_only_one_item.html', context)

    else:
        return HttpResponseRedirect('/betasmartz_admin/firm/{pk}/invite_advisor?next=/admin/main/firm/'
                                    .format(pk=queryset.all()[0].pk))


def invite_authorised_representative(modeladmin, request, queryset):
    context = {'STATIC_URL': settings.STATIC_URL, 'MEDIA_URL': settings.MEDIA_URL, 'item_class': 'firm'}

    if queryset.count() > 1:
        return render_to_response('admin/betasmartz/error_only_one_item.html', context)

    else:
        return HttpResponseRedirect('/betasmartz_admin/firm/{pk}/invite_legal?next=/admin/main/firm/'
                                    .format(pk=queryset.all()[0].pk))


def invite_supervisor(modeladmin, request, queryset):
    context = {'STATIC_URL': settings.STATIC_URL, 'MEDIA_URL': settings.MEDIA_URL, 'item_class': 'firm'}

    if queryset.count() > 1:
        return render_to_response('admin/betasmartz/error_only_one_item.html', context)

    else:
        return HttpResponseRedirect('/betasmartz_admin/firm/{pk}/invite_supervisor?next=/admin/main/firm/'
                                    .format(pk=queryset.all()[0].pk))


class FirmConfigInline(admin.StackedInline):
    model = FirmConfig


class FirmDataInline(admin.StackedInline):
    model = FirmData


class FirmAdmin(admin.ModelAdmin):
    list_display = ('name',)
    inlines = (FirmDataInline, FirmConfigInline,)
    actions = (invite_authorised_representative, invite_advisor, invite_supervisor)


class PricingPlanAdmin(admin.ModelAdmin):
    list_display = 'firm', 'bps', 'fixed', 'system_bps', 'system_fixed'


class AuthorisedRepresentativeAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone_num', 'is_accepted', 'is_confirmed', 'firm',
                    'geolocation_lock')
    list_filter = ('is_accepted', FirmFilter)
    actions = (approve_application,)


class SupervisorAdmin(admin.ModelAdmin):
    list_display = ('user', 'firm', 'can_write',)
    list_filter = (FirmFilter,)


class FirmEmailInviteAdmin(admin.ModelAdmin):
    model = FirmEmailInvite


admin.site.register(Firm, FirmAdmin)
admin.site.register(PricingPlan, PricingPlanAdmin)
admin.site.register(AuthorisedRepresentative, AuthorisedRepresentativeAdmin)
admin.site.register(Supervisor, SupervisorAdmin)
admin.site.register(FirmEmailInvite, FirmEmailInviteAdmin)
