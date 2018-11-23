from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator
from retiresmartz.models import RetirementPlan

class AreaQuotient(models.Model):
    id = models.IntegerField(
        choices=RetirementPlan.ExpenseCategory.choices(),
        primary_key=True,
        help_text='Expense Category')

    quot_city = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        help_text='Quotient for City')

    quot_suburb = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        help_text='Quotient for Suburb')

    quot_rural = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        help_text='Quotient for Rural area')

    def __str__(self):
        return '%s' % (self.id)


class PeerGroupData(models.Model):
    AGE_GROUPS = (
        (0, 'Under 25'),
        (1, '25 - 34'),
        (2, '35 - 44'),
        (3, '45 - 54'),
        (4, '55 - 64'),
        (5, '65 +')
    )

    age_group = models.IntegerField(
        choices=AGE_GROUPS,
        help_text='Age Group')

    expense_cat = models.ForeignKey(
        'AreaQuotient',
        help_text='Expense Category')

    pc_1 = models.FloatField(
        validators=[MinValueValidator(-1.0), MaxValueValidator(1.0)],
        help_text='Rate value (0 - 1) for income $0 - $19,999')

    pc_2 = models.FloatField(
        validators=[MinValueValidator(-1.0), MaxValueValidator(1.0)],
        help_text='Rate value (0 - 1) for income $20,000 - $29,999')

    pc_3 = models.FloatField(
        validators=[MinValueValidator(-1.0), MaxValueValidator(1.0)],
        help_text='Rate value (0 - 1) for income $30,000 - $39,999')

    pc_4 = models.FloatField(
        validators=[MinValueValidator(-1.0), MaxValueValidator(1.0)],
        help_text='Rate value (0 - 1) for income $40,000 - $49,999')

    pc_5 = models.FloatField(
        validators=[MinValueValidator(-1.0), MaxValueValidator(1.0)],
        help_text='Rate value (0 - 1) for income $50,000 - $69,999')

    pc_7 = models.FloatField(
        validators=[MinValueValidator(-1.0), MaxValueValidator(1.0)],
        help_text='Rate value (0 - 1) for income $70,000 +')

    northeast = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        help_text='Northeast')

    midwest = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        help_text='Midwest')

    south = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        help_text='South')

    west = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        help_text='West')
