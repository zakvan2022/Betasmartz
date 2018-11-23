from __future__ import unicode_literals

from django.contrib import admin

from statements.models import StatementOfAdvice, RecordOfAdvice, RetirementStatementOfAdvice, LivePortfolioReport


class StatementOfAdviceAdmin(admin.ModelAdmin):
    model = StatementOfAdvice


class RecordOfAdviceAdmin(admin.ModelAdmin):
    model = RecordOfAdvice


class RetirementStatementOfAdviceAdmin(admin.ModelAdmin):
    model = RetirementStatementOfAdvice


class LivePortfolioReportAdmin(admin.ModelAdmin):
    model = LivePortfolioReport


admin.site.register(StatementOfAdvice, StatementOfAdviceAdmin)
admin.site.register(RecordOfAdvice, RecordOfAdviceAdmin)
admin.site.register(RetirementStatementOfAdvice, RetirementStatementOfAdviceAdmin)
admin.site.register(LivePortfolioReport, LivePortfolioReportAdmin)
