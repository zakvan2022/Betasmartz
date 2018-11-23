from django.core.management.base import NoArgsCommand
from main import tax_helpers as helpers
import pdb

class Command(NoArgsCommand):
    def handle_noargs(self, **options):

        from main import tax_sheet as tax
        from main import test_tax_sheet as tst_tx
        tst_cls = tax.TaxUser(tst_tx.plan,
                              tst_tx.life_exp,
                              tst_tx.is_partner,
                              tst_tx.plans)
    
        tst_cls.create_maindf()
        test_ss_fra_retirement = helpers.get_ss_benefit_future_dollars(tst_tx.plan.client.ss_fra_todays,
                                                                       tst_tx.plan.client.date_of_birth,
                                                                       tst_tx.plan.retirement_age)
