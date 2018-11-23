import os

from main import constants

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
environment = os.environ.get("ENVIRONMENT")

from django.conf.global_settings import TEMPLATE_CONTEXT_PROCESSORS as TCP

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.7/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '&nus@l_#u6@6+ezkldb)xwiiha++9z1omzhamfbd%89@+esi!l'
DEVICE = 'ios'
VERSION = '3.00'
CONTENT_TYPE = 'application/json'
ETNA_X_API_ROUTING = 'demo'
ETNA_X_API_KEY = 'lOxygJOL4y8ZvKFmh6zb07tEHuWNbukI3AS4P4Ho'
ETNA_ENDPOINT_URL = 'https://api.etnatrader.com/v0/' + ETNA_X_API_ROUTING
ETNA_LOGIN = 'les'
ETNA_PASSWORD = 'B0ngyDung'
ETNA_ACCOUNT_ID = 2337
# Interactive brokers connection settings
IB_PORT = 7496
IB_HOST = 'localhost'
IB_CLIENT_ID = 0
IB_PROVIDER_CLIENT_ID = 1

IB_FTP_DOMAIN = 'ftp.interactivebrokers.com'
IB_FTP_USERNAME = os.environ.get('IB_FTP_USERNAME', '')
IB_FTP_PASSWORD = os.environ.get('IB_FTP_PASSWORD', '')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

TEMPLATE_DEBUG = False

ALLOWED_HOSTS = ['localhost']

# Application definition

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'django.contrib.humanize',
    'django.contrib.sites',
    'django_cron',
    'genericadmin',  # Allows nice selection of generic foreign keys in admin interface
    'nested_admin', # for nested inlines
    'django_extensions', # temp. to visualize models only
    'test_without_migrations',
    'tinymce_4',
    'import_export',
    'filebrowser',
    'suit',
    'compat',
    'pages',

    'user',

    'notifications', # move to django-notifications-hq>=1.0 after fixing
    'pinax.eventlog',  # For our activity tracking

    'rest_framework',
    'rest_framework_swagger',
    'bootstrap3',

    'multi_sites',
    'address',
    'portfolios',
    'firm',
    'advisor',
    'client',
    'goal',
    'activitylog',
    'main',
    'support',
    'swift',
    'anymail',
    'execution',
    'retiresmartz',
    'scheduler',
    'statements',
    'errorlog',
    'consumer_expenditure',
    'documents',
    'acquiresmartz',
    'brokers'
)

SITE_ID = 1

TEST_WITHOUT_MIGRATIONS_COMMAND = 'django_nose.management.commands.test.Command'

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'user.autologout.SessionExpireMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'user.log_ip.LogIPMiddleware',

)

REST_FRAMEWORK = {
    'PAGE_SIZE': 20,
    # JSON numbers don't suffer from precision loss, they are fixed point. Therefore we want to represent numeric data
    # as numeric data, not as string.
    'COERCE_DECIMAL_TO_STRING': False,
    'PAGE_SIZE_QUERY_PARAM': 'page_size',  # allow client to override, using `?page_size=xxx`.
    'MAX_PAGE_SIZE': 1000,  # maximum limit allowed when using `?page_size=xxx`.
    'DEFAULT_PERMISSION_CLASSES': (
        # RESERVED # 'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    ),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_FILTER_BACKENDS': (
        'rest_framework.filters.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ),
    'EXCEPTION_HANDLER': 'api.handlers.api_exception_handler',
    'TEST_REQUEST_DEFAULT_FORMAT': 'json',
}


ROOT_URLCONF = 'main.urls'

WSGI_APPLICATION = 'main.wsgi.application'

TEMPLATE_CONTEXT_PROCESSORS = TCP + (
    "pages.context_processors.media",
    'django.core.context_processors.request',
    'main.context_processors.site_contact',
    'user.autologout.session_expire_context_processor',
    'multi_sites.context_processors.with_theme',
)

# QUOVO INTEGRATION
QUOVO_API_BASE = 'https://api.quovo.com/v2/'
QUOVO_USERNAME = os.environ.get('QUOVO_USERNAME', '')
QUOVO_PASSWORD = os.environ.get('QUOVO_PASSWORD', '')

# PLAID INTEGRATION
PLAID_CLIENT_ID = "58360d0b46eb122e28401e66"
PLAID_PUBLIC_KEY = "319cc1520a3be212627b736e42831c"
PLAID_SECRET = "e2076f95025434a76b81bcfeb91c39"
PLAID_DEVELOPMENT_URL = "https://tartan.plaid.com"
PLAID_URL = PLAID_DEVELOPMENT_URL

# PLAID_ENVIRONMENT should be either sandbox, development, or production
PLAID_ENVIRONMENT = 'sandbox'  # change back to development
if environment in ['ip']:
    # use the production url below for real clients
    PLAID_PRODUCTION_URL = "https://api.plaid.com/"
    PLAID_URL = PLAID_PRODUCTION_URL
    PLAID_ENVIRONMENT = 'production'





# STRIPE INTEGRATION
STRIPE_API_TEST_KEY = "pk_test_i0a7Ot7uBC1bbH1txCZ7d8j7"
STRIPE_API_TEST_SECRET = "sk_test_nu0g8NYyF6tWeCq5tS0ZSSWU"
STRIPE_API_KEY = STRIPE_API_TEST_KEY
STRIPE_API_SECRET = STRIPE_API_TEST_SECRET
if environment in ['ip']:
    # use production settings for ip deployment
    STRIPE_API_KEY = "pk_live_dqJcT8708Xir7d3dhSL0DGYe"
    STRIPE_API_SECRET = "sk_live_3N2WQxGGCNS1fj7FIFAsVKGz"

# Internationalization
# https://docs.djangoproject.com/en/1.7/topics/i18n/

LANGUAGE_CODE = 'en-us'

USE_I18N = True

USE_L10N = True

USE_TZ = True

SESSION_EXPIRE_AT_BROWSER_CLOSE = True

PHONENUMBER_DB_FORMAT = 'INTERNATIONAL'
PHONENUMBER_DEFAULT_REGION = 'US'

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.7/howto/static-files/

STATIC_ROOT = os.path.join(os.path.dirname(BASE_DIR), 'static')
STATIC_URL = '/static/'

TEMPLATE_DIRS = (
    os.path.join(BASE_DIR, 'templates'),
)

STATICFILES_DIRS = (
    os.path.join(BASE_DIR, "static"),
)

MESSAGE_STORAGE = 'django.contrib.messages.storage.fallback.FallbackStorage'

AUTH_USER_MODEL = 'user.User'
SHOW_HIJACKUSER_IN_ADMIN = False

MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'


DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', "no-reply@mailgun.betasmartz.com")
SUPPORT_EMAIL = "support@mailgun.betasmartz.com"
SUPPORT_PHONE = "1888888888"
IS_DEMO = False
TIME_ZONE = "Australia/Sydney"
PAGE_DEFAULT_TEMPLATE = "support/base.html"
gettext_noop = lambda s: s
PAGE_LANGUAGES = (
    ('en-us', gettext_noop('US English')),
)

LOGIN_URL = '/login'
LOGIN_REDIRECT_URL = '/'
LOGOUT_URL = '/logout'

CMS_UNIHANDECODE_HOST = '/static/unihandecode/'
CMS_UNIHANDECODE_VERSION = '1.0.0'
CMS_UNIHANDECODE_DECODERS = ['ja', 'zh', 'vn', 'kr', 'diacritic']

REDIS_URI = os.environ.get('REDIS_URI', 'redis://localhost:6379/0')

# Django Suit configuration example
SUIT_CONFIG = {
    # header
    'ADMIN_NAME': 'Betasmartz Admin',
    # 'HEADER_DATE_FORMAT': 'l, j. F Y',
    # 'HEADER_TIME_FORMAT': 'H:i',

    # forms
    # 'SHOW_REQUIRED_ASTERISK': True,  # Default True
    # 'CONFIRM_UNSAVED_CHANGES': True, # Default True

    # menu
    # 'SEARCH_URL': '/admin/auth/user/',
    # 'MENU_ICONS': {
    #    'sites': 'icon-leaf',
    #    'auth': 'icon-lock',
    # },
    # 'MENU_OPEN_FIRST_CHILD': True, # Default True
    # 'MENU_EXCLUDE': ('auth.group',),
    # 'MENU': (
    #     'sites',
    #     {'app': 'auth', 'icon':'icon-lock', 'models': ('user', 'group')},
    #     {'label': 'Settings', 'icon':'icon-cog', 'models': ('auth.user', 'auth.group')},
    #     {'label': 'Support', 'icon':'icon-question-sign', 'url': '/support/'},
    # ),

    # misc
    # 'LIST_PER_PAGE': 15
}

BLOOMBERG_HOSTNAME = 'dlsftp.bloomberg.com'
BLOOMBERG_USERNAME = 'dl788259'
BLOOMBERG_PASSWORD = '+gT[zfV9Bu]Ms.4'

CRON_CLASSES = [
    # ...
]


# Email
ANYMAIL = {
    "MAILGUN_API_KEY": os.environ.get('MAILGUN_API_KEY', ''),
    'WEBHOOK_AUTHORIZATION': os.environ.get('WEBHOOK_AUTHORIZATION', 'random:random'),
}


ADMIN_EMAIL = SUPPORT_EMAIL

ADMINS = (
    ('Masao Kiba', 'masao.kiba426@gmail.com'),
)


# DOCUMENTATION
SWAGGER_SETTINGS = {
    'exclude_namespaces': [],
    'api_version': '2.0',
    'api_path': '/',
    'enabled_methods': [
        'get',
        'post',
        'put',
        #'patch',
        'delete'
    ],
    'api_key': '',
    'is_authenticated': False,
    'is_superuser': False,
    'permission_denied_handler': None,
    'resource_access_handler': None,
    #'base_path':'127.0.0.1:8000/docs/',
    'info': {
        #'contact': 'info@stratifi.com',
        'description': 'Reference',
        'title': 'BetaSmartz API',
    },
    'doc_expansion': 'list',
    'VALIDATOR_URL': None,  # Swagger online validator does not have access to our private instances
    #'resource_access_handler': 'api.views.resource_access_handler',
}


# The inflation rate
BETASMARTZ_CPI = 2

# From http://www.aihw.gov.au/deaths/life-expectancy/
MALE_LIFE_EXPECTANCY = 80
FEMALE_LIFE_EXPECTANCY = 84

# Do you want the security questions to be case sensitive?
#SECURITY_QUESTIONS_CASE_SENSITIVE = False

# What is the system currency?
SYSTEM_CURRENCY = 'USD'

SYSTEM_CURRENCY_SYMBOL = '$'

# all
AUTOCONFIRMED_ACCOUNTS = tuple(at for at, _ in constants.ACCOUNT_TYPES
                               if at not in [
                                   # make these not auto confirmed
                                   constants.ACCOUNT_TYPE_JOINT,
                               ])

# Create jira tickets with errors
JIRA_ENABLED = True
JIRA_SERVER = 'https://betasmartz.atlassian.net'
JIRA_USERNAME = 'errorbot@betasmartz.com'
JIRA_PASSWORD = '#$MKVzWj&fg6q'
JIRA_ERROR_PROJECT_ID = 10400
JIRA_ISSUE_TYPE = {'name': 'Bug'}

CLIENT_SESSION_TIMEOUT = 600  # 10 min
AUTHENTICATED_SESSION_TIMEOUT = 1800  # 30 min - advisor/firm accounts

HIGHCHARTS_EXPORT_SERVER_URI = 'https://highcharts.betasmartz.com'

FITBIT_SETTINGS = {
    'API_BASE': 'https://api.fitbit.com',
    'CLIENT_ID': os.environ.get('FITBIT_CLIENT_ID', ''),
    'CLIENT_SECRET': os.environ.get('FITBIT_CLIENT_SECRET', ''),
    'EXPIRES_IN': 604800,
}

GOOGLEFIT_SETTINGS = {
    'API_BASE': 'https://www.googleapis.com/fitness/v1/',
    'CLIENT_ID': os.environ.get('GOOGLEFIT_CLIENT_ID', ''),
    'CLIENT_SECRET': os.environ.get('GOOGLEFIT_CLIENT_SECRET', ''),
    'EXPIRES_IN': 604800,
}

MICROSOFTHEALTH_SETTINGS = {
    'API_BASE': 'https://api.microsofthealth.net/v1/me',
    'CLIENT_ID': os.environ.get('MICROSOFTHEALTH_CLIENT_ID', ''),
    'CLIENT_SECRET': os.environ.get('MICROSOFTHEALTH_CLIENT_SECRET', ''),
}

UNDERARMOUR_SETTINGS = {
    'API_BASE': 'https://api.ua.com/v7.1',
    'CLIENT_ID': os.environ.get('UNDERARMOUR_CLIENT_ID', ''),
    'CLIENT_SECRET': os.environ.get('UNDERARMOUR_CLIENT_SECRET', ''),
}

WITHINGS_SETTINGS = {
    'API_BASE': 'https://wbsapi.withings.net/v2',
    'CONSUMER_KEY': os.environ.get('WITHINGS_CONSUMER_KEY', ''),
    'CONSUMER_SECRET': os.environ.get('WITHINGS_CONSUMER_SECRET', ''),
}

JAWBONE_SETTINGS = {
    'API_BASE': 'https://jawbone.com/nudge/api/v.1.1',
    'CLIENT_ID': os.environ.get('JAWBONE_CLIENT_ID', ''),
    'CLIENT_SECRET': os.environ.get('JAWBONE_CLIENT_SECRET', ''),
}

TOMTOM_SETTINGS = {
    'API_BASE': 'https://api.tomtom.com/mysports',
    'API_KEY': os.environ.get('TOMTOM_API_KEY', ''),
    'CLIENT_ID': os.environ.get('TOMTOM_CLIENT_ID', ''),
    'CLIENT_SECRET': os.environ.get('TOMTOM_CLIENT_SECRET', ''),
}

from local_settings import *
