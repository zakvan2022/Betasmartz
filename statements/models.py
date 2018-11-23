import base64
import datetime
import json
import logging
import requests
from django.contrib.sites.shortcuts import get_current_site
from django.db import models
from django.db.models import Q, Max
from weasyprint import HTML, CSS
from django.conf import settings
from io import BytesIO
from django.core.files.base import ContentFile
from django.contrib.sites.models import Site
from main.settings import BASE_DIR
from functools import reduce
from main import constants
from statements import utils
from client.models import Client
from django.core.mail import EmailMessage
from django.core.urlresolvers import reverse
from django.template.loader import render_to_string
from main.tasks import send_roa_generated_email_task
from .chart_configs import ChartData
from .constants import *
from .utils import get_price_from_index
logger = logging.getLogger(__name__)


class PDFStatement(models.Model):
    create_date = models.DateTimeField(auto_now_add=True)
    pdf = models.FileField(null=True, blank=True)

    @property
    def date(self):
        return self.create_date.strftime('%Y-%m-%d_%H:%I:%S')

    def render_template(self, template_name=None, **kwargs):
        from django.template.loader import render_to_string
       
        template_name = template_name or self.default_template
        return render_to_string(template_name, {
            'object': self,
            'statement': self,
            'account': self.account,
            'client': self.client,
            'owner': self.client,
            'advisor': self.client.advisor,
            'firm': self.client.advisor.firm,
        })

    def render_pdf(self, template_name=None, **kwargs):
        html = self.render_template(template_name, **kwargs)
        # Have to source the images locally for WeasyPrint
        static_path = settings.STATICFILES_DIRS[0]
        html = html.replace('/static/', 'file://%s/' % static_path)
        html = html.replace('/media/', 'file://%s/media/' % BASE_DIR)
        pdf_builder = HTML(string=html)
        return pdf_builder.write_pdf()

    def save(self, *args, **kwargs):
        super(PDFStatement, self).save(*args, **kwargs)
        if not self.pdf:
            self.save_pdf()

    def save_pdf(self):
        bio = BytesIO(self.render_pdf())
        pdf_content = bio.getvalue()
        self.pdf.save('%s.pdf' % self.filename, ContentFile(pdf_content))
        return pdf_content

    @property
    def filename(self):
        return self.id

    @property
    def default_template(self):
        return None

    @property
    def client(self):
        return self.account.primary_owner

    class Meta:
        abstract = True
        ordering = ('-create_date', )


class StatementOfAdvice(PDFStatement):
    account = models.OneToOneField('client.ClientAccount', related_name='statement_of_advice')

    def __str__(self):
        return 'Statement of Advice for %s' % self.account

    @property
    def pdf_url(self):
        return reverse('statements:statement_of_advice', kwargs={'pk': self.id, 'ext': '.pdf'})

    @property
    def filename(self):
        return self.account

    @property
    def default_template(self):
        return "statements/statement_of_advice.html"


class RetirementStatementOfAdvice(PDFStatement):
    retirement_plan = models.OneToOneField('retiresmartz.RetirementPlan', related_name='statement_of_advice')
    
    def __str__(self):
        return 'Retirement Statement of Advice for %s' % self.retirement_plan

    @property
    def pdf_url(self):
        return reverse('statements:retirement_statement_of_advice', kwargs={'pk': self.id, 'ext': '.pdf'})

    @property
    def filename(self):
        return 'Retirment_SOA_{}'.format(self.retirement_plan.id)

    @property
    def client(self):
        return self.retirement_plan.client

    @property
    def default_template(self):
        return "statements/retirement_statement_of_advice/index.html"

    def render_template(self, template_name=None, **kwargs):
        from django.template.loader import render_to_string
        template_name = template_name or self.default_template
        plan = self.retirement_plan
        client_ip = plan.client.user.last_ip
        agreed_on = None
        if plan.agreed_on:
            tzinfo = utils.get_timezone(client_ip)
            agreed_on_tz = plan.agreed_on.astimezone(tzinfo)
            agreed_on = {
                'date': agreed_on_tz.strftime('%d-%b-%y'),
                'time': agreed_on_tz.strftime('%H:%M:%S %p %Z')
            }

        retirement_accounts = plan.retirement_accounts if plan.retirement_accounts else []

        retirement_income_graph = {
            'estimated': { 'y': 0, 'h': 100 },
            'target': { 'y': 30, 'h': 70 }
        }
        iraTypes = [
            constants.ACCOUNT_TYPE_IRA,
            constants.ACCOUNT_TYPE_ROTHIRA,
            constants.ACCOUNT_TYPE_SIMPLEIRA,
            constants.ACCOUNT_TYPE_SARSEPIRA,
        ]
        client_retirement_accounts = list(filter(lambda item: item['owner'] == 'self', retirement_accounts))
        partner_retirement_accounts = list(filter(lambda item: item['owner'] == 'partner', retirement_accounts))
        ira_retirement_accounts = filter(lambda item: item['acc_type'] in iraTypes, retirement_accounts)
        has_partner = self.client.is_married and plan.partner_data
        try:
            projection = plan.projection
        except:
            projection = {}

        return render_to_string(template_name, {
            'object': self,
            'statement': self,
            'client': self.client,
            'owner': self.client,
            'advisor': self.client.advisor,
            'firm': self.client.advisor.firm,
            'plan': plan,
            'client_ip': client_ip,
            'agreed_on': agreed_on,
            'has_partner': has_partner,
            'partner_name': plan.partner_data['name'] if has_partner else '',
            'lifestyle_stars': range(plan.lifestyle + 2),
            'retirement_income_graph': retirement_income_graph,
            'sum_of_retirement_accounts': reduce(lambda acc, item: acc + item['balance'], retirement_accounts, 0),
            'sum_of_retirement_accounts_ira': reduce(lambda acc, item: acc + item['balance'], ira_retirement_accounts, 0),
            'lifestyle_box': utils.get_lifestyle_box(self.client),
            'client_retirement_accounts': client_retirement_accounts,
            'partner_retirement_accounts': partner_retirement_accounts,
            'tax_situation': utils.get_tax_situation(plan),
            'pensions_annuities': utils.get_pensions_annuities(plan),
            'waterfall_chart': utils.get_waterfall_chart(plan, has_partner),
            'income_chart': utils.get_retirement_income_chart(plan, has_partner),
            'balance_chart': utils.get_account_balance_chart(plan, has_partner),
            'projection': projection
        })


class RecordOfAdvice(PDFStatement):
    goal = models.ForeignKey('goal.Goal', related_name='records_of_advice')
    circumstances = models.TextField(null=True, blank=True, verbose_name='Client circumstances')
    basis = models.TextField(null=True, blank=True, verbose_name='Basis of advice')
    details = models.TextField(verbose_name='Details of the advice')

    def __str__(self):
        return 'Record of Advice %s for %s' % (self.id, self.goal)

    @property
    def pdf_url(self):
        return reverse('statements:record_of_advice', kwargs={'pk': self.id, 'ext': '.pdf'})

    @property
    def account(self):
        return self.goal.account

    @property
    def owner(self):
        return self.goal.account.primary_owner

    @property
    def client(self):
        return self.owner

    @property
    def filename(self):
        return 'ROA_{}'.format(self.create_date.date().isoformat())

    @property
    def default_template(self):
        return "statements/record_of_advice.html"

    def send_roa_generated_email(self):
        try:
            send_roa_generated_email_task.delay(self.id)
        except:
            self._send_roa_generated_email(self.id)

    @staticmethod
    def _send_roa_generated_email(roa_id):
        roa = RecordOfAdvice.objects.get(pk=roa_id)
        pdf_content = roa.save_pdf()
        account = roa.goal.account
        # Send to clients
        clients = Client.objects.filter(Q(pk=account.primary_owner.id) |
                                        Q(id__in=list(account.signatories.all().values_list('id', flat=True))))
        subject = "Updated Goal - Record of Advice"
        for client in clients:
            context = {
                'site': Site.objects.get_current(),
                'client': client,
                'roa': roa,
                'advisor': client.advisor,
                'firm': client.firm
            }
            html_content = render_to_string('email/goal/roa_generated_client.html', context)
            email = EmailMessage(subject, html_content, None, [client.user.email])
            email.content_subtype = "html"
            email.attach('ROA.pdf', pdf_content, 'application/pdf')
            email.send()

        # Send to advisor
        context = {
            'site': Site.objects.get_current(),
            'clients': clients,
            'roa': roa,
            'advisor': client.advisor,
            'firm': client.firm
        }

        account_number_part = roa.goal.account.account_number
        account_number_part = ' - {}'.format(account_number_part) if account_number_part else ''
        subject = "Record of Advice " + ", ".join(["{}{}".format(client.name, account_number_part) for client in clients])
        html_content = render_to_string('email/goal/roa_generated_advisor.html', context)
        email = EmailMessage(subject, html_content, None, [client.advisor.user.email])
        email.content_subtype = "html"
        email.attach('ROA.pdf', pdf_content, 'application/pdf')
        email.send()


class LivePortfolioReport(PDFStatement):
    live_portfolio = models.ForeignKey('portfolios.LivePortfolio', related_name='reports')

    @property
    def default_template(self):
        return "statements/firm_portfolio_report/index.html"

    def render_pdf(self, template_name=None, request=None, **kwargs):
        chartData = ChartData()
        configs = {
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
                }

        charts = {}
        url = 'https://highcharts.betasmartz.com'
        headers = {'Content-Type': 'application/json'}

        for key,value in configs.items():
            data = json.dumps({ 'infile': value, 'type': 'jpeg' })
            res = requests.post(settings.HIGHCHARTS_EXPORT_SERVER_URI, data=data, headers=headers)
            chart_image = 'data:image/jpeg;base64,' + base64.b64encode(res.content).decode('utf-8')
            charts[key] = chart_image

        html = self.render_template(template_name=template_name, charts=charts, render_type='pdf', request=request, **kwargs)

        # Have to source the images locally for WeasyPrint
        static_path = settings.STATICFILES_DIRS[0]
        html = html.replace('/static/', 'file://%s/' % static_path)
        html = html.replace('/media/', 'file://%s/media/' % BASE_DIR)
        pdf_builder = HTML(string=html)
        return pdf_builder.write_pdf()

    def render_template(self, template_name=None, charts=None, render_type=None, request=None, **kwargs):
        from django.template.loader import render_to_string
        from django.template import RequestContext
        
        template_name = template_name or self.default_template
        commentary = self.get_commentary()
        tables = self.get_tables()
        
        
        if request is not None:
            if request.user.id == None:
                username = ''
            else:
                username = request.user.first_name
        else:
            username = ''
        
        return render_to_string(template_name, {
            'type': render_type,
            'charts': charts,
            'username': username,
            'object': self.live_portfolio,
            'statement': self,
            'firm': self.live_portfolio.firm,
            'theme': get_current_site(None).site_config.safe_theme,
            'live_portfolio': self.live_portfolio,
            'current_date': datetime.date.today(),
            'commentary': commentary,
            'tables': tables
        }, context_instance=RequestContext(request) if request is not None else None)

    def get_tables(self):
        tables = {}

        #US Economic table
        indices = ["", USURTOT_INDEX, USEMTOT_INDEX, "", CONCCONF_INDEX, RSTAYOY_INDEX]
        table = self.get_common_economic_table1(label_array=LABEL_ARRAY_FOR_COMMON_TABLE1, indices=indices)
        tables['us_economic_table1'] = table

        indices = ["", SPCS20Y_INDEX, ETSLYOY_INDEX, "", SBOITOTL_INDEX, NAPMPMI_INDEX]
        table = self.get_economic_table_from_raw_price(label_array=LABEL_ARRAY_FOR_US_TABLE2, indices=indices)
        tables['us_economic_table2'] = table

        #EU Economic table
        indices = ["", UMRT27_INDEX, EMPETTEU_INDEX, "", EUCCEU27_INDEX, F47GX7327_INDEX]
        table = self.get_common_economic_table1(label_array=LABEL_ARRAY_FOR_COMMON_TABLE1, indices=indices)
        tables['eu_economic_table1'] = table
        indices = ["", HOPIEUYY_INDEX, EUMG27_INDEX, "", GRZEEUEX_INDEX, MPMIEUMA_INDEX]
        table2 = self.get_eu_economic_table2(label_array=LABEL_ARRAY_FOR_EU_TABLE2, indices=indices)
        tables['eu_economic_table2'] = table

        #JP Economic table
        indices = ["", JNUE_INDEX, JNUEMPLY_INDEX, "", JCOMACF_INDEX, JNNETYOY_INDEX]
        table = self.get_common_economic_table1(label_array=LABEL_ARRAY_FOR_COMMON_TABLE1, indices=indices)
        tables['jp_economic_table1'] = table
        indices = ["", JLNDNALL_INDEX, JNHSYOY_INDEX, "", JNTSMFG_INDEX, MPMIJPMA_INDEX]
        table = self.get_economic_table_from_raw_price(label_array=LABEL_ARRAY_FOR_JP_TABLE2, indices=indices)
        tables['jp_economic_table2'] = table

        #AU Economic table
        indices = ["", AULFUNEM_INDEX, AULFEMPL_INDEX, "", WMCCCONS_INDEX, AURSTYSA_INDEX]
        table = self.get_common_economic_table1(label_array=LABEL_ARRAY_FOR_AU_TABLE1, indices=indices)
        tables['au_economic_table1'] = table
        indices = ["", AUSD_INDEX, AUBAY_INDEX, "", NABSCONF_INDEX, AIGPMI_INDEX]
        table = self.get_economic_table_from_raw_price(label_array=LABEL_ARRAY_FOR_AU_TABLE2, indices=indices)
        tables['au_economic_table2'] = table

        #CN Economic table
        indices = ["", CNUERATE_INDEX, CSTNLPOP_INDEX, "", CHCSCONF_INDEX, CNRSCYOY_INDEX]
        table = self.get_common_economic_table1(label_array=LABEL_ARRAY_FOR_COMMON_TABLE1, indices=indices)
        tables['cn_economic_table1'] = table
        indices = ["", CNHPHOUY_INDEX, CHRXUCON_INDEX, "", SCCNSMEI_INDEX, CPMINDX_INDEX]
        table = self.get_economic_table_from_raw_price(label_array=LABEL_ARRAY_FOR_CN_TABLE2, indices=indices)
        tables['cn_economic_table2'] = table

        # Economic table
        indices = ["", HKUERATE_INDEX, HKLFTLY_INDEX, "", CUHKCONF_INDEX, HKRSNYOY_INDEX]
        table = self.get_common_economic_table1(label_array=LABEL_ARRAY_FOR_HK_TABLE1, indices=indices)
        tables['hk_economic_table1'] = table
        indices = ["", CENLCCL_INDEX, HKHMVOV_INDEX, "", NABSCONF_INDEX, MPMIHKWA_INDEX]
        table = self.get_economic_table_from_raw_price(label_array=LABEL_ARRAY_FOR_HK_TABLE2, indices=indices)
        tables['hk_economic_table2'] = table

        return tables;

    #Construct common economic table1 contents
    def get_common_economic_table1(self, label_array=[], indices=[]):
        table_contents = []
        
        for i in range(len(label_array)):
            if i == 0 or i == 3:
                record = {
                    "label": label_array[i],
                    "latest": "",
                    "last_three": "",
                    "last_six": "",
                    "last_year": ""
                }
            else:
                record = {
                    "label": label_array[i],
                    "latest": self.get_employed_person_value_from_index(indices[i], 0) if i==2 else round(get_price_from_index(indices[i], 0), 2),
                    "last_three": self.get_employed_person_value_from_index(indices[i], 90) if i==2 else round(get_price_from_index(indices[i], 90), 2),
                    "last_six": self.get_employed_person_value_from_index(indices[i], 180) if i==2 else round(get_price_from_index(indices[i], 180), 2),
                    "last_year": self.get_employed_person_value_from_index(indices[i], 365) if i==2 else round(get_price_from_index(indices[i], 365), 2)
                }

            table_contents.append(record)

        return table_contents

    #Construct EU economic table2 contents
    def get_eu_economic_table2(self, label_array=[], indices=[]):
        table_contents = []
        
        for i in range(len(label_array)):
            if i == 0 or i == 3:
                record = {
                    "label": label_array[i],
                    "latest": "",
                    "last_three": "",
                    "last_six": "",
                    "last_year": ""
                }
            else:
                record = {
                    "label": label_array[i],
                    "latest": self.get_construnction_growth_value_from_index(indices[i], 0) if i==2 else round(get_price_from_index(indices[i], 0), 2),
                    "last_three": self.get_construnction_growth_value_from_index(indices[i], 90) if i==2 else round(get_price_from_index(indices[i], 90), 2),
                    "last_six": self.get_construnction_growth_value_from_index(indices[i], 180) if i==2 else round(get_price_from_index(indices[i], 180), 2),
                    "last_year": self.get_construnction_growth_value_from_index(indices[i], 365) if i==2 else round(get_price_from_index(indices[i], 365), 2)
                }

            table_contents.append(record)

        return table_contents

    #Construct economic table from raw price
    def get_economic_table_from_raw_price(self, label_array=[], indices=[]):
        table_contents = []
        
        for i in range(len(label_array)):
            if i == 0 or i == 3:
                record = {
                    "label": label_array[i],
                    "latest": "",
                    "last_three": "",
                    "last_six": "",
                    "last_year": ""
                }
            else:
                record = {
                    "label": label_array[i],
                    "latest": round(get_price_from_index(indices[i], 0), 2), 
                    "last_three": round(get_price_from_index(indices[i], 90), 2),
                    "last_six": round(get_price_from_index(indices[i], 180), 2),
                    "last_year": round(get_price_from_index(indices[i], 365), 2)
                }

            table_contents.append(record)

        return table_contents

    def get_employed_person_value_from_index(self, index, daydelta):
        last_date_price = get_price_from_index(index, daydelta)
        last_year_price = get_price_from_index(index, daydelta + 365)

        if last_date_price and last_year_price:
            return round((last_date_price / last_year_price - 1) * 100, 2)
        else:
            return 0

    def get_construnction_growth_value_from_index(self, index, daydelta):    
        value = 1
        for i in range(12):
            last_date_price = get_price_from_index(index, daydelta + i*30)
            middle_value = last_date_price / 100 + 1
            value *= middle_value

        value = (value - 1) * 100
        return round(value, 2)

    def get_commentary(self):
        from portfolios.models import Commentary
        from main.constants import COMMENTARY_PORTFOLIO_INFO, COMMENTARY_ECONOMIC_INFO, COMMENTARY_MARKET_INFO, COMMENTARY_RISK_MANAGEMENT
        
        portfolio_key_commentary = self.live_portfolio.commentaries.filter(Q(publish_at__lte=datetime.datetime.now()) & Q(category=COMMENTARY_PORTFOLIO_INFO)) \
                                                                    .order_by('-publish_at')[0] \
                                                                    .key_commentary
        portfolio_near_term_outlook = self.live_portfolio.commentaries.filter(Q(publish_at__lte=datetime.datetime.now()) & Q(category=COMMENTARY_PORTFOLIO_INFO)) \
                                                                        .order_by('-publish_at')[0] \
                                                                        .near_term_outlook
        economic_key_commentary = Commentary.objects.filter(Q(publish_at__lte=datetime.datetime.now()) & Q(category=COMMENTARY_ECONOMIC_INFO)) \
                                                    .order_by('-publish_at')[0] \
                                                    .key_commentary
        economic_near_term_outlook = Commentary.objects.filter(Q(publish_at__lte=datetime.datetime.now()) & Q(category=COMMENTARY_ECONOMIC_INFO)) \
                                                    .order_by('-publish_at')[0] \
                                                    .near_term_outlook
        market_key_commentary = Commentary.objects.filter(Q(publish_at__lte=datetime.datetime.now()) & Q(category=COMMENTARY_MARKET_INFO)) \
                                                    .order_by('-publish_at')[0] \
                                                    .key_commentary
        marekt_near_term_outlook = Commentary.objects.filter(Q(publish_at__lte=datetime.datetime.now()) & Q(category=COMMENTARY_MARKET_INFO)) \
                                                    .order_by('-publish_at')[0] \
                                                    .near_term_outlook
        risk_key_commentary = self.live_portfolio.commentaries.filter(Q(publish_at__lte=datetime.datetime.now()) & Q(category=COMMENTARY_RISK_MANAGEMENT)) \
                                                                .order_by('-publish_at')[0] \
                                                                .key_commentary
        risk_near_term_outlook = self.live_portfolio.commentaries.filter(Q(publish_at__lte=datetime.datetime.now()) & Q(category=COMMENTARY_RISK_MANAGEMENT)) \
                                                                .order_by('-publish_at')[0] \
                                                                .near_term_outlook
        commentary = {
            'portfolio_key_commentary' : portfolio_key_commentary,
            'portfolio_near_term_outlook' : portfolio_near_term_outlook,
            'economic_key_commentary' : economic_key_commentary,
            'economic_near_term_outlook' : economic_near_term_outlook,
            'market_key_commentary' : market_key_commentary,
            'market_near_term_outlook' : marekt_near_term_outlook,
            'risk_key_commentary' : risk_key_commentary,
            'risk_near_term_outlook' : risk_near_term_outlook
        }

        return commentary
