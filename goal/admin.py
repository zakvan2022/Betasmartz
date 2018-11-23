from django.contrib import admin, messages
from django.shortcuts import HttpResponseRedirect, render_to_response
from goal.models import Goal, GoalMetric, GoalMetricGroup, \
     GoalSetting, GoalType, Portfolio, PortfolioItem, Transaction
from execution.models import ExecutionRequest
import nested_admin


def execute_transaction(modeladmin, request, queryset):
    context = {'STATIC_URL': settings.STATIC_URL, 'MEDIA_URL': settings.MEDIA_URL, 'item_class': 'transaction'}

    if queryset.count() > 1:
        return render_to_response('admin/betasmartz/error_only_one_item.html', context)

    else:
        return HttpResponseRedirect('/betasmartz_admin/transaction/{pk}/execute?next=/admin/main/firm/'
                                    .format(pk=queryset.all()[0].pk))


def rebalance(modeladmin, request, queryset):
    context = {'STATIC_URL': settings.STATIC_URL, 'MEDIA_URL': settings.MEDIA_URL, 'item_class': 'transaction'}

    if queryset.count() > 1:
        return render_to_response('admin/betasmartz/error_only_one_item.html', context)

    else:
        return HttpResponseRedirect('/betasmartz_admin/rebalance/{pk}?next=/admin/main/firm/'
                                    .format(pk=queryset.all()[0].pk))


def process(modeladmin, request, queryset):
    from datetime import datetime
    from execution.end_of_day import process
    from portfolios.providers.execution.django import ExecutionProviderDjango
    from portfolios.providers.data.django import DataProviderDjango
    data_provider = DataProviderDjango(datetime.now().date())
    execution_provider = ExecutionProviderDjango()
    try:
        process(data_provider, execution_provider, 5, queryset)
        modeladmin.message_user(request, "Selected Goals has been processed successfully.")
    except Exception as e:
        modeladmin.message_user(request, "Error! Can't process.", level=messages.ERROR)


class GoalMetricInline(admin.StackedInline):
    model = GoalMetric


class GoalMetricGroupAdmin(admin.ModelAdmin):
    model = GoalMetricGroup
    inlines = (GoalMetricInline,)


class PortfolioItemInline(nested_admin.NestedTabularInline):
    model = PortfolioItem
    extra = 0
    can_delete = False


class PortfolioInline(nested_admin.NestedStackedInline):
    model = Portfolio
    inlines = (PortfolioItemInline,)


class GoalSettingAdmin(nested_admin.NestedModelAdmin):
    model = GoalSetting
    inlines = (PortfolioInline,)


class GoalTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'group', 'default_term', 'risk_sensitivity', 'order')
    list_editable = ('group', 'default_term', 'risk_sensitivity', 'order')


class GoalAdmin(admin.ModelAdmin):
    list_display = ('account', 'name', 'type')
    actions = (rebalance, process)


class PositionLotAdmin(admin.ModelAdmin):
    list_display = ('execution_distribution', 'quantity')


class PortfolioAdmin(admin.ModelAdmin):
    inlines = (PortfolioItemInline,)


class PortfolioItemAdmin(admin.ModelAdmin):
    pass


class ExecutionRequestInline(admin.TabularInline):
    model = ExecutionRequest


class TransactionAdmin(admin.ModelAdmin):
#    list_display = ('account', 'type', 'from_account', 'to_account', 'status', 'amount', 'created')
    list_display = ('reason', 'from_goal', 'to_goal', 'status', 'amount', 'created')
    inlines = (ExecutionRequestInline,)
    actions = (execute_transaction, )
    list_filter = ('status', )


admin.site.register(Goal, GoalAdmin)
admin.site.register(GoalType, GoalTypeAdmin)
admin.site.register(GoalSetting, GoalSettingAdmin)
admin.site.register(GoalMetricGroup, GoalMetricGroupAdmin)
admin.site.register(Portfolio, PortfolioAdmin)
admin.site.register(PortfolioItem, PortfolioItemAdmin)
admin.site.register(Transaction, TransactionAdmin)
