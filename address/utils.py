from .constants import COUNTRY_CHOICES
def get_country_code_from_name(country_name):
	for country in COUNTRY_CHOICES:
		if country[1] == country_name:
			return country[0]
	return None
