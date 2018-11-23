from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

class MultiSitesConfig(AppConfig):
    name = 'multi_sites'
    verbose_name = _("MultiSites")
    def ready(self):
        from django.contrib.sites.models import Site
        from .models import site_config
        Site.config = site_config