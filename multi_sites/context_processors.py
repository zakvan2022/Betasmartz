from django.contrib.sites.shortcuts import get_current_site



def with_theme(request):
    """
    Return the value you want as a dictionary.
    You may add multiple values in there.
    """
    site = get_current_site(request)

    return {
        'theme': site.site_config.safe_theme,
    }
