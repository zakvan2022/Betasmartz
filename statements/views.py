# -*- coding: utf-8 -*-
from django.views.generic import DetailView
from django.http import FileResponse, HttpResponse
from main.views.base import ClientView, LegalView
from common.utils import get_client_ip
from portfolios.models import LivePortfolio
from statements.chart_configs import ChartData
from statements.models import StatementOfAdvice, RecordOfAdvice, \
    RetirementStatementOfAdvice, LivePortfolioReport, PDFStatement
from django.shortcuts import render_to_response

__all__ = ["StatementView", "RecordView", "RetirementStatementOfAdvice"]


class PDFView(DetailView, ClientView):
    def get_queryset(self):
        return self.model.objects.filter(
            account__primary_owner=self.request.user.client)

    def get(self, request, pk, ext=None):
        obj = self.get_object()
        if(ext.lower() == '.pdf'):
            response = HttpResponse(obj.render_pdf(self.template_name),
                                    content_type='application/pdf')
            response['Content-Disposition'] = 'inline; filename="{}.pdf"'.format(obj.filename)
        else:
            response = HttpResponse(obj.render_template(self.template_name))
        return response


class StatementView(PDFView):
    template_name = StatementOfAdvice.default_template
    model = StatementOfAdvice


class RecordView(PDFView):
    template_name = RecordOfAdvice.default_template
    model = RecordOfAdvice

    def get_queryset(self):
        return RecordOfAdvice.objects.all()


class RetirementView(PDFView):
    template_name = RetirementStatementOfAdvice.default_template
    model = RetirementStatementOfAdvice

    def get_queryset(self):
        return RetirementStatementOfAdvice.objects.all()

    def get(self, request, pk, ext=None):
        obj = RetirementStatementOfAdvice.objects.get(pk=pk)
        client_ip = get_client_ip(request)

        if(ext.lower() == '.pdf'):
            response = HttpResponse(obj.render_pdf(self.template_name, client_ip=client_ip),
                                    content_type='application/pdf')
            response['Content-Disposition'] = 'inline; filename="{}.pdf"'.format(obj.filename)
        else:
            response = HttpResponse(obj.render_template(self.template_name, client_ip=client_ip))
        return response


class FirmPortfolioReportView(DetailView, LegalView):
    template_name = 'statements/firm_portfolio_report/index.html'
    model = LivePortfolioReport

    def get_queryset(self):
        return LivePortfolioReport.objects.all()

    def get(self, request, pk, ext):
        obj = LivePortfolioReport.objects.get(pk=pk)
        if(ext.lower() == '.pdf'):
            response = HttpResponse(obj.pdf, content_type='application/pdf')
            response['Content-Disposition'] = 'inline; filename="{}.pdf"'.format(obj.filename)
        else:
            response = HttpResponse(obj.render_template(self.template_name, configs=None, render_type='html', request=request))
        return response


class FirmPortfolioReportWebView(DetailView, LegalView):
    template_name = 'statements/firm_portfolio_report/index.html'
    model = LivePortfolio

    def get_queryset(self):
        return LivePortfolio.objects.all()

    def get(self, request, pk, ext=None):

        obj = LivePortfolioReport(live_portfolio_id=pk)

        response = HttpResponse(obj.render_template(self.template_name, configs=None, render_type='html', request=request))
        return response


def ChartConfigs(request, lp_pk):
    import json
    chartData = ChartData()
    configs = json.dumps({
            'portfolio_performance': chartData.portfolio_performance_config(),
            'investment_growth': chartData.investment_growth_config(),
            'asset_allocation': chartData.asset_allocation_config(),
            'portfolio_tilts': chartData.portfolio_tilts(),
            'portfolio_weight_risk': chartData.portfolio_weight_risk(),
            'portfolio_weight_return': chartData.portfolio_weight_return(),
            'geographic_exposure': chartData.geographic_exposure(),
            'gics_sector': chartData.gics_sector(),
            'us_economic_chart1': chartData.get_us_economic_chart1(),
            'us_economic_chart2': chartData.get_us_economic_chart2(),
            'eu_economic_chart1': chartData.get_eu_economic_chart1(),
            'eu_economic_chart2': chartData.get_eu_economic_chart2(),
            'jp_economic_chart1': chartData.get_jp_economic_chart1(),
            'jp_economic_chart2': chartData.get_jp_economic_chart2(),
            'au_economic_chart1': chartData.get_au_economic_chart1(),
            'au_economic_chart2': chartData.get_au_economic_chart2(),
            'cn_economic_chart1': chartData.get_cn_economic_chart1(),
            'cn_economic_chart2': chartData.get_cn_economic_chart2(),
            'hk_economic_chart1': chartData.get_hk_economic_chart1(),
            'hk_economic_chart2': chartData.get_hk_economic_chart2(),
            'equities': chartData.equities(),
            'fx': chartData.fx(),
            'fixed_income': chartData.fixed_income(),
            'asset_contributions_returns': chartData.asset_contributions_returns(),
            'asset_contributions_volatility': chartData.asset_contributions_volatility(),
            'portfolio_weight_risk1': chartData.portfolio_weight_risk1(),
            'portfolio_weight_contributions': chartData.portfolio_weight_contributions(),
            'fund_performance': chartData.fund_performance(),
            'fund_risk': chartData.fund_risk(),
            'asset_allocation1': chartData.asset_allocation1(),
            'daa_change': chartData.daa_change(),
            'daa_change1': chartData.daa_change1(),
            'daa_change2': chartData.daa_change2()
    })
    return HttpResponse(configs)
