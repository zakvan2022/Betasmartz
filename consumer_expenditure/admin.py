from django.contrib import admin
from consumer_expenditure.models import AreaQuotient, PeerGroupData
# Register your models here.

class AreaQuotientAdmin(admin.ModelAdmin):
    list_display = ('id', 'quot_city', 'quot_suburb', 'quot_rural',)
    list_editable = ('quot_city', 'quot_suburb', 'quot_rural',)

class PeerGroupDataAdmin(admin.ModelAdmin):
    list_display = ('id', 'age_group', 'expense_cat', 'pc_1', 'pc_2', 'pc_3', 'pc_4', 'pc_5', 'pc_7', 'northeast', 'midwest', 'south', 'west', )
    list_editable = ('pc_1', 'pc_2', 'pc_3', 'pc_4', 'pc_5', 'pc_7', 'northeast', 'midwest', 'south', 'west', )

admin.site.register(AreaQuotient, AreaQuotientAdmin)
admin.site.register(PeerGroupData, PeerGroupDataAdmin)
