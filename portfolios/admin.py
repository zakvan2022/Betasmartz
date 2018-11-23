from django.contrib import admin
from django.conf import settings
from genericadmin.admin import BaseGenericModelAdmin, GenericAdminModelAdmin
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from suit.admin import SortableModelAdmin, SortableTabularInline
from .models import AssetFeature, InvestmentType, Inflation, Dividend, ManagerBenchmarks, \
    MarketIndex, PortfolioProvider, DefaultPortfolioProvider, PortfolioSet, \
    DefaultPortfolioSet, Performer, ProxyAssetClass, ProxyTicker, Ticker, View, \
    LivePortfolio, LivePortfolioItem, Commentary
from client.models import Client


class InflationResource(resources.ModelResource):
    class Meta:
        model = Inflation
        exclude = ('id', 'recorded')
        import_id_fields = ('year', 'month')


class TickerInline(BaseGenericModelAdmin, SortableTabularInline):
    model = ProxyTicker
    sortable = 'ordering'
    extra = 0
    generic_fk_fields = [{
        'ct_field': 'benchmark_content_type',
        'fk_field': 'benchmark_object_id',
    }]


class ManagerBenchmarksAdmin(admin.TabularInline):
    model = ManagerBenchmarks


class PortfolioViewsInline(admin.StackedInline):
    model = View
    extra = 0


class AssetResource(resources.ModelResource):
    class Meta:
        model = ProxyAssetClass


class AssetClassAdmin(GenericAdminModelAdmin, SortableModelAdmin, ImportExportModelAdmin):
    list_display = ('name', 'display_name', 'display_order', 'investment_type')
    inlines = (TickerInline,)
    resource_class = AssetResource
    sortable = 'display_order'


class AssetFeaturesAdmin(admin.ModelAdmin):
    model = AssetFeature
    list_display = ('name', 'description', 'upper_limit')
    list_editable = ('upper_limit',)


class InvestmentTypeAdmin(admin.ModelAdmin):
    model = InvestmentType


class InflationAdmin(ImportExportModelAdmin):
    list_display = 'year', 'month', 'value'
    resource_class = InflationResource


class DefaultDefaultPortfolioProviderAdmin(admin.ModelAdmin):
    list_display = ('default_provider', 'changed')


class DefaultPortfolioSetAdmin(admin.ModelAdmin):
    list_display = ('default_set', 'changed')


class PerformerAdmin(admin.ModelAdmin):
    list_display = ('symbol', 'name', 'group', 'allocation')


class PortfolioProviderAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'TLH', 'portfolio_optimization')


class PortfolioSetAdmin(admin.ModelAdmin):
    filter_horizontal = ('asset_classes',)
    inlines = (PortfolioViewsInline,)


class LivePortfolioItemInline(admin.StackedInline):
    model = LivePortfolioItem
    extra = 0


class LivePortfolioAdmin(admin.ModelAdmin):
    model = LivePortfolio
    inlines = (LivePortfolioItemInline,)


class CommentaryAdmin(admin.ModelAdmin):
    model = Commentary


class TickerAdmin(admin.ModelAdmin):
    inlines = ManagerBenchmarksAdmin,
    list_display = (
        'symbol',
        'unit_price',
        'region_feature',
        'asset_class_feature',
        'investment_type_feature',
        'currency_feature',
    )
    search_fields = ['symbol']

    def region_feature(self, obj):
        return obj.get_region_feature_value()

    def asset_class_feature(self, obj):
        return obj.get_asset_class_feature_value()

    def investment_type_feature(self, obj):
        return obj.get_asset_type_feature_value()

    def currency_feature(self, obj):
        return obj.get_currency_feature_value()


admin.site.register(AssetFeature, AssetFeaturesAdmin)
admin.site.register(DefaultPortfolioProvider, DefaultDefaultPortfolioProviderAdmin)
admin.site.register(DefaultPortfolioSet, DefaultPortfolioSetAdmin)
admin.site.register(Dividend)
admin.site.register(Inflation, InflationAdmin)
admin.site.register(InvestmentType, InvestmentTypeAdmin)
admin.site.register(LivePortfolio, LivePortfolioAdmin)
admin.site.register(MarketIndex)
admin.site.register(Performer, PerformerAdmin)
admin.site.register(PortfolioProvider, PortfolioProviderAdmin)
admin.site.register(PortfolioSet, PortfolioSetAdmin)
admin.site.register(ProxyAssetClass, AssetClassAdmin)
admin.site.register(Commentary, CommentaryAdmin)
admin.site.register(Ticker, TickerAdmin)

if settings.DEBUG:
    from .models import DailyPrice

    class DailyPriceAdmin(GenericAdminModelAdmin):
        model = DailyPrice
        list_display = (
        'date', 'price', 'instrument', 'instrument_content_type', 'instrument_object_id')
        # sortable = 'date'
        # extra = 0
        generic_fk_fields = [{
            'ct_field': 'instrument_content_type',
            'fk_field': 'instrument_object_id',
        }]
        list_editable = (
        'date', 'price', 'instrument_content_type', 'instrument_object_id')

    admin.site.register(DailyPrice, DailyPriceAdmin)
