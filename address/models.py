from django.db import models
from django.utils.translation import ugettext as _
from django.utils.functional import cached_property
from common.structures import ChoiceEnum

"""
After looking through the addressing options available (django-postal, django-address) Neither worked well with
addresses that have a apartment number, and chinese addresses, and had a DRF backend, so I had to roll my own :(
"""


class Region(models.Model):
    """
    A model of the first-level administrative regions in countries. Examples can be states, cantons, even towns for
    small countries.
    """
    name = models.CharField(max_length=128)
    code = models.CharField(max_length=16, db_index=True, null=True, blank=True)
    country = models.CharField(max_length=2)

    class Meta:
        unique_together = (
            ('country', 'name'),
            ('country', 'code')
        )
        verbose_name = _('region')
        verbose_name_plural = _('regions')

    def __str__(self):
        return '%s %s' % (self.name, self.country)


class Address(models.Model):
    """
    Because the whole world does addressing wildly differently, the only thing generally in common is country,
    top-level region and some postal code identifier. As such, the best way to do addressing for our
    purpose (which is to send mail and identify) is to simply keep the address lines as a resident would write them.
    This works for PO boxes, houses and lots of other things.
    """
    # An address is always somewhere within a region. Hence one line of addressing is required.
    # format: [address1 \n address 2 \n city | address1 \n city (some countries don't need address 2)]
    address = models.TextField(help_text='The full address excluding country, first level administrative region '
                                         '(state/province etc) and postcode')
    post_code = models.CharField(max_length=16, blank=True, null=True)  # Some countries don't have post codes.
    global_id = models.CharField(max_length=64,
                                 blank=True,  # Doesn't really matter, as since it's unique, blank is a valid value.
                                 null=True,
                                 unique=True,
                                 help_text='Global identifier of the address in whatever API we are using (if any)')
    region = models.ForeignKey(Region, related_name='+')

    @cached_property
    def full_address(self):
        ads = [x for x in self.address.split('\n') if x != '']
        ads_str = ', '.join(ads)
        return '{}, {}, {}, {}'.format(ads_str, self.region.name, self.post_code, self.country)

    @cached_property
    def address1(self):
        ads = self.address.split('\n')
        return ads[0] if len(ads) > 0 else None

    @cached_property
    def address2(self):
        ads = self.address.split('\n')
        return ads[1] if len(ads) > 1 else None

    @cached_property
    def city(self):
        ads = self.address.split('\n')
        if len(ads) > 1:
            return ads[-1]
        else:
            return None

    @cached_property
    def state_code(self):
        return self.region.code

    @cached_property
    def country(self):
        return self.region.country

    def copy_from_address(self, address):
        """
        Accepts the Address instance as parameter and copies all the values in the address.
        PURPOSE: Re-use the address object assigned and prevent address being orphaned as much as possible.
        """
        self.address = address.address
        self.city = address.city
        self.post_code = address.post_code
        self.region = address.region
        self.global_id = address.global_id
        self.save()

    def update_address(self, *args, **kwargs):
        """
        Accepts address1, address2, city, post_code, state_code, country as parameters and update the self object
        PURPOSE: Re-use the address object assigned and prevent address being orphaned as much as possible.
        """
        # get parameters
        address1 = kwargs.get('address1', None)
        address2 = kwargs.get('address2', None)
        city = kwargs.get('city', None)
        post_code = kwargs.get('post_code', None)
        state_code = kwargs.get('state_code', None)
        country = kwargs.get('country', None)

        address_list = [
            address1 or self.address1,
            address2 or self.address2,
            city or self.city,
        ]
        self.address = '\n'.join([item for item in address_list if item is not None and item != ''])
        self.post_code = post_code
        region_params = {
            'code': state_code or self.region.code,
            'country': country or self.region.country,
        }
        new_region, created = Region.objects.get_or_create(**region_params)
        if created:
            new_region.name = region_params['code']
            new_region.save()
        self.region = new_region
        self.save()

    def __str__(self):
        return self.full_address

    class Meta:
        verbose_name = _('address')
        verbose_name_plural = _('addresses')


class USState(models.Model):
    class RegionEnum(ChoiceEnum):
        NORTHEAST = 1, 'Northeast'
        SOUTH = 2, 'South'
        MIDWEST = 3, 'Midwest'
        WEST = 4, 'West'

    code = models.CharField(max_length=2, unique=True, help_text='State code')
    name = models.CharField(max_length=32, help_text='State name')
    region = models.IntegerField(choices=RegionEnum.choices())

    def __str__(self):
        return '{} ({})'.format(self.name, self.code)


class USFips(models.Model):
    class RUCC(ChoiceEnum):
        METRO_1 = 1, 'Metro - Counties in metro areas of 1 million population or more'
        METRO_2	= 2, 'Metro - Counties in metro areas of 250,000 to 1 million population'
        METRO_3 = 3, 'Metro - Counties in metro areas of fewer than 250,000 population'
        URBAN_4 = 4, 'Nonmetro - Urban population of 20,000 or more, adjacent to a metro area'
        URBAN_5 = 5, 'Nonmetro - Urban population of 20,000 or more, not adjacent to a metro area'
        URBAN_6 = 6, 'Nonmetro - Urban population of 2,500 to 19,999, adjacent to a metro area'
        URBAN_7 = 7, 'Nonmetro - Urban population of 2,500 to 19,999, not adjacent to a metro area'
        RURAL_8 = 8, 'Nonmetro - Completely rural or less than 2,500 urban population, adjacent to a metro area'
        RURAL_9 = 9, 'Nonmetro - Completely rural or less than 2,500 urban population, not adjacent to a metro area'

    fips = models.CharField(max_length=5, db_index=True, unique=True, help_text='FIPS (County Code)')
    county_name = models.CharField(max_length=255, help_text='County Name')
    rucc = models.IntegerField(choices=RUCC.choices())
    state = models.ForeignKey('USState')

    def __str__(self):
        return self.fips


class USZipcode(models.Model):
    zip_code = models.CharField(max_length=10, db_index=True, help_text='Zip code')
    zip_name = models.CharField(max_length=255, help_text='Zip name')
    fips = models.ForeignKey('USFips')
    phone_area_code = models.CharField(max_length=3, help_text='Phone area code')

    class Meta:
        unique_together = ('zip_code', 'zip_name')

    def __str__(self):
        return self.zip_code
