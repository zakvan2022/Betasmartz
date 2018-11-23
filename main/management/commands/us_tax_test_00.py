from django.core.management.base import NoArgsCommand
 
class Command(NoArgsCommand):
    def handle_noargs(self, **options):
        from main import us_tax
        from main import tax_sheet
        from main import test_tax_sheet as tst_tx

        '''
        tax_sheet
        '''

        tst_tx_cls = tax_sheet.TaxUser(tst_tx.name,
                                      tst_tx.ssn,
                                      tst_tx.dob,
                                      tst_tx.desired_retirement_age,
                                      tst_tx.life_exp,
                                      tst_tx.retirement_lifestyle,
                                      tst_tx.reverse_mort,
                                      tst_tx.house_value,
                                      tst_tx.filing_status,
                                      tst_tx.retire_earn_at_fra,
                                      tst_tx.retire_earn_under_fra,
                                      tst_tx.total_income,
                                      tst_tx.adj_gross,
                                      tst_tx.federal_taxable_income,
                                      tst_tx.federal_regular_tax,
                                      tst_tx.after_tax_income,
                                      tst_tx.other_income,
                                      tst_tx.ss_fra_retirement,
                                      tst_tx.paid_days,
                                      tst_tx.ira_rmd_factor,
                                      tst_tx.initial_401k_balance,
                                      tst_tx.inflation_level,
                                      tst_tx.risk_profile_over_cpi,
                                      tst_tx.projected_income_growth,
                                      tst_tx.contrib_rate_employee_401k,
                                      tst_tx.contrib_rate_employer_401k,
                                      tst_tx.state,
                                      tst_tx.employment_status)

        tst_tx_cls.create_maindf()

        '''
        fed tax
        '''
        tst_fed = us_tax.FederalTax(tst_tx_cls.years, tst_tx_cls.annual_inflation, tst_tx_cls.annual_taxable_income)
        tst_fed.create_tax_engine()
        tst_fed.create_tax_projected()

        '''
        state tax
        '''
        tst_state_cls = us_tax.StateTax(tst_tx.state,
                                         tst_tx.filing_status,
                                         tst_tx.total_income)
        
        state = tst_state_cls.set_tax_engine()

        '''
        fica
        '''
        tst_fica = us_tax.Fica(tst_tx.filing_status,
                                tst_tx.total_income)
        fica = tst_fica.get_fica()
    
        
        
