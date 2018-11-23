from django.contrib import admin
from advisor.models import Advisor, ChangeDealerGroup, AccountGroup, SingleInvestorTransfer, BulkInvestorTransfer
from firm.admin import FirmFilter


def approve_application(modeladmin, request, queryset):
    for obj in queryset.all():
        obj.approve()


approve_application.short_description = "Approve application(s)"


def approve_changes(modeladmin, request, queryset):
    for obj in queryset.all():
        obj.approve()
    messages.info(request, "Changes have been approved and applied")


class AdvisorAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone_num', 'is_accepted', 'is_confirmed', 'firm',
                    'geolocation_lock')
    list_filter = ('is_accepted', FirmFilter)
    actions = (approve_application,)

    pass


class AdvisorChangeDealerGroupAdmin(admin.ModelAdmin):
    list_display = ('advisor', 'new_email', 'old_firm', 'new_firm', 'approved', 'create_at', 'approved_at')
    list_filter = ('advisor', 'old_firm', 'new_firm', 'approved')
    actions = (approve_changes,)


class AdvisorBulkInvestorTransferAdmin(admin.ModelAdmin):
    filter_horizontal = ('investors',)
    list_display = ('from_advisor', 'to_advisor', 'approved', 'create_at', 'approved_at')
    list_filter = ('from_advisor', 'to_advisor', 'approved')
    actions = (approve_changes,)


class AdvisorSingleInvestorTransferAdmin(admin.ModelAdmin):
    list_display = ('from_advisor', 'to_advisor', 'firm', 'investor', 'approved', 'create_at', 'approved_at')
    list_filter = ('from_advisor', 'to_advisor', 'investor', 'approved')
    actions = (approve_changes,)


admin.site.register(Advisor, AdvisorAdmin)
admin.site.register(ChangeDealerGroup, AdvisorChangeDealerGroupAdmin)
admin.site.register(AccountGroup)
admin.site.register(SingleInvestorTransfer, AdvisorSingleInvestorTransferAdmin)
admin.site.register(BulkInvestorTransfer, AdvisorBulkInvestorTransferAdmin)
