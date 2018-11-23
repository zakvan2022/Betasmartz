from django.conf import settings
from django.contrib import admin
from import_export import resources
from execution.models import PositionLot, ExecutionRequest, Order


class ExecutionRequestAdmin(admin.ModelAdmin):
    model = ExecutionRequest


class OrderAdmin(admin.ModelAdmin):
    model = Order


class PositionLotAdmin(admin.ModelAdmin):
    list_display = ('execution_distribution', 'quantity')


admin.site.register(ExecutionRequest, ExecutionRequestAdmin)
admin.site.register(Order, OrderAdmin)
admin.site.register(PositionLot, PositionLotAdmin)


if settings.DEBUG:
    from execution.models import (MarketOrderRequest, Execution, ExecutionDistribution)

    admin.site.register(MarketOrderRequest)
    admin.site.register(Execution)
    admin.site.register(ExecutionDistribution)
