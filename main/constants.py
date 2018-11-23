SUCCESS_MESSAGE = "Your application has been submitted successfully, " \
                  "you will receive a confirmation email" \
                  " following a BetaSmartz approval."
INVITATION_PENDING = 0
INVITATION_SUBMITTED = 1
INVITATION_ACTIVE = 3
INVITATION_CLOSED = 4
EMAIL_INVITATION_STATUSES = (
    (INVITATION_PENDING, 'Pending'), (INVITATION_SUBMITTED, 'Submitted'),
    (INVITATION_ACTIVE, 'Active'), (INVITATION_CLOSED, 'Closed'))
EMPLOYMENT_STATUS_EMMPLOYED = 0
EMPLOYMENT_STATUS_UNEMPLOYED = 1
EMPLOYMENT_STATUS_SELF_EMPLOYED = 2
EMPLOYMENT_STATUS_RETIRED = 3
EMPLOYMENT_STATUS_NOT_LABORFORCE = 4
EMPLOYMENT_STATUSES = (
    (EMPLOYMENT_STATUS_EMMPLOYED, 'Employed'),
    (EMPLOYMENT_STATUS_UNEMPLOYED, 'Unemployed'),
    (EMPLOYMENT_STATUS_SELF_EMPLOYED, 'Self-employed'),
    (EMPLOYMENT_STATUS_RETIRED, 'Retired'),
    (EMPLOYMENT_STATUS_NOT_LABORFORCE, 'Not in labor force'),
)
INVITATION_ADVISOR = 0
AUTHORIZED_REPRESENTATIVE = 1
INVITATION_SUPERVISOR = 2
INVITATION_CLIENT = 3
INVITATION_TYPE_CHOICES = (
    (INVITATION_ADVISOR, "Advisor"),
    (AUTHORIZED_REPRESENTATIVE, 'Authorised representative'),
    (INVITATION_SUPERVISOR, 'Supervisor'),
    (INVITATION_CLIENT, 'Client'),
)
INVITATION_TYPE_DICT = {
    str(INVITATION_ADVISOR): "advisor",
    str(AUTHORIZED_REPRESENTATIVE): "authorised_representative",
    str(INVITATION_CLIENT): "client",
    str(INVITATION_SUPERVISOR): "supervisor"
}
TFN_YES = 0
TFN_NON_RESIDENT = 1
TFN_CLAIM = 2
TFN_DONT_WANT = 3
TFN_CHOICES = (
    (TFN_YES, "Yes"),
    (TFN_NON_RESIDENT, "I am a non-resident of Australia"),
    (TFN_CLAIM, "I want to claim an exemption"),
    (TFN_DONT_WANT, "I do not want to quote a Tax File Number or exemption"),)
PERSONAL_DATA_FIELDS = ('date_of_birth', 'gender', 'phone_num')
ASSET_FEE_EVENTS = ((0, 'Day End'),
                    (1, 'Complete Day'),
                    (2, 'Month End'),
                    (3, 'Complete Month'),
                    (4, 'Fiscal Month End'),
                    (5, 'Entry Order'),
                    (6, 'Entry Order Item'),
                    (7, 'Exit Order'),
                    (8, 'Exit Order Item'),
                    (9, 'Transaction'))
ASSET_FEE_UNITS = ((0, 'Asset Value'),  # total value of the asset
                   (1, 'Asset Qty'),  # how many units of an asset
                   (2, 'NAV Performance'))  # % positive change in the NAV
ASSET_FEE_LEVEL_TYPES = (
    (0, 'Add'),  # Once the next level is reached, the amount form that band is added to lower bands
    (1, 'Replace')  # Once the next level is reached, the value from that level is used for the entire amount
)
SUPER_ASSET_CLASSES = (
    # EQUITY
    ("EQUITY_AU", "EQUITY_AU"),
    ("EQUITY_US", "EQUITY_US"),
    ("EQUITY_EU", "EQUITY_EU"),
    ("EQUITY_EM", "EQUITY_EM"),
    ("EQUITY_INT", "EQUITY_INT"),
    ("EQUITY_UK", "EQUITY_UK"),
    ("EQUITY_JAPAN", "EQUITY_JAPAN"),
    ("EQUITY_AS", "EQUITY_AS"),
    ("EQUITY_CN", "EQUITY_CN"),
    # FIXED_INCOME
    ("FIXED_INCOME_AU", "FIXED_INCOME_AU"),
    ("FIXED_INCOME_US", "FIXED_INCOME_US"),
    ("FIXED_INCOME_EU", "FIXED_INCOME_EU"),
    ("FIXED_INCOME_EM", "FIXED_INCOME_EM"),
    ("FIXED_INCOME_INT", "FIXED_INCOME_INT"),
    ("FIXED_INCOME_UK", "FIXED_INCOME_UK"),
    ("FIXED_INCOME_JAPAN", "FIXED_INCOME_JAPAN"),
    ("FIXED_INCOME_AS", "FIXED_INCOME_AS"),
    ("FIXED_INCOME_CN", "FIXED_INCOME_CN"))
YES_NO = ((False, "No"), (True, "Yes"))
ACCOUNT_TYPE_PERSONAL = 0
ACCOUNT_TYPE_JOINT = 1
ACCOUNT_TYPE_TRUST = 2
ACCOUNT_TYPE_SMSF = 3
ACCOUNT_TYPE_CORPORATE = 4
ACCOUNT_TYPE_401K = 5
ACCOUNT_TYPE_ROTH401K = 6
ACCOUNT_TYPE_IRA = 7  # Traditional pre-tax IRA account
ACCOUNT_TYPE_ROTHIRA = 8  # Tax-paid IRA account
ACCOUNT_TYPE_SEPIRA = 9  # IRA account for self-employed
ACCOUNT_TYPE_403K = 10
ACCOUNT_TYPE_SIMPLEIRA = 11
ACCOUNT_TYPE_SARSEPIRA = 12
ACCOUNT_TYPE_PAYROLLDEDUCTIRA = 13
ACCOUNT_TYPE_PROFITSHARING = 14
ACCOUNT_TYPE_DEFINEDBENEFIT = 15
ACCOUNT_TYPE_MONEYPURCHASE = 16
ACCOUNT_TYPE_ESOP = 17
ACCOUNT_TYPE_GOVERMENTAL = 18
ACCOUNT_TYPE_457 = 19
ACCOUNT_TYPE_409A = 20
ACCOUNT_TYPE_403B = 21
ACCOUNT_TYPE_TRUSTTEST = 22
ACCOUNT_TYPE_TRUSTNONTEST = 23
ACCOUNT_TYPE_INVESTCLUBORGANIZATION = 24
ACCOUNT_TYPE_PARTNERSHIPORGANIZATION = 25
ACCOUNT_TYPE_SOLEPROPORGANIZATION = 26
ACCOUNT_TYPE_LLCORGANIZATION = 27
ACCOUNT_TYPE_ASSOCIATIONORGANIZATION = 28
ACCOUNT_TYPE_NONCORPORATIONORGANIZATION = 29
ACCOUNT_TYPE_PENSION = 30
ACCOUNT_TYPE_HSA = 31
ACCOUNT_TYPE_529 = 32
ACCOUNT_TYPE_ESA = 33
ACCOUNT_TYPE_UG = 34
ACCOUNT_TYPE_GUARDIANSHIP = 35
ACCOUNT_TYPE_CUSTODIAL = 36
ACCOUNT_TYPE_THRIFTSAVING = 37
ACCOUNT_TYPE_401A = 38
ACCOUNT_TYPE_QUALIFIEDANNUITY = 39
ACCOUNT_TYPE_TAXDEFERRED_ANNUITY = 40
ACCOUNT_TYPE_QUALIFIEDNPPLAN = 41
ACCOUNT_TYPE_QUALIFIEDNPROTHPLAN = 42
ACCOUNT_TYPE_QUALIFIEDPRIV457PLAN = 43
ACCOUNT_TYPE_INDIVDUAL401K = 44
ACCOUNT_TYPE_INDROTH401K = 45
ACCOUNT_TYPE_VARIABLEANNUITY = 46
ACCOUNT_TYPE_SINGLELIFEANNUITY = 47
ACCOUNT_TYPE_JOINTSURVIVORANNUITY = 48
ACCOUNT_TYPE_OTHER = 99

ACCOUNT_UNKNOWN = 'Other/Unknown'

ACCOUNT_TYPES = (
    (ACCOUNT_TYPE_PERSONAL, "Personal Account"),
    (ACCOUNT_TYPE_JOINT, "Joint Account"),
    (ACCOUNT_TYPE_TRUST, "Trust Account"),
    (ACCOUNT_TYPE_INVESTCLUBORGANIZATION, "Investment Club Account"),
    (ACCOUNT_TYPE_PARTNERSHIPORGANIZATION, "Partnership/Limited partnership Account"),
    (ACCOUNT_TYPE_SOLEPROPORGANIZATION, "Sole Proprietor Account"),
    (ACCOUNT_TYPE_LLCORGANIZATION, "Limited Liability Company Account"),
    (ACCOUNT_TYPE_ASSOCIATIONORGANIZATION, "Association Account"),
    (ACCOUNT_TYPE_NONCORPORATIONORGANIZATION, "Non-corporate organization Account"),
    (ACCOUNT_TYPE_PENSION, "Pension Account"),
    (ACCOUNT_TYPE_401K, "401K Account"),
    (ACCOUNT_TYPE_401A, "401A Account"),
    (ACCOUNT_TYPE_ROTH401K, "Roth 401K Account"),
    (ACCOUNT_TYPE_IRA, "Individual Retirement Account (IRA)"),
    (ACCOUNT_TYPE_ROTHIRA, "Roth IRA"),
    (ACCOUNT_TYPE_SEPIRA, "SEP IRA"),
    (ACCOUNT_TYPE_403K, "403K Account"),
    (ACCOUNT_TYPE_SIMPLEIRA, "SIMPLE IRA Account (Savings Incentive Match Plans for Employees)"),
    (ACCOUNT_TYPE_SARSEPIRA, "SARSEP Account (Salary Reduction Simplified Employee Pension)"),
    (ACCOUNT_TYPE_PAYROLLDEDUCTIRA, "Payroll Deduction IRA Account"),
    (ACCOUNT_TYPE_PROFITSHARING, "Profit-Sharing Account"),
    (ACCOUNT_TYPE_MONEYPURCHASE, "Money Purchase Account"),
    (ACCOUNT_TYPE_ESOP, "Employee Stock Ownership Account (ESOP)"),
    (ACCOUNT_TYPE_GOVERMENTAL, "Governmental Account"),
    (ACCOUNT_TYPE_457, "457 Account"),
    (ACCOUNT_TYPE_409A, "409A Nonqualified Deferred Compensation Account"),
    (ACCOUNT_TYPE_403B, "403B Account"),
    (ACCOUNT_TYPE_HSA, "Health Savings Account"),
    (ACCOUNT_TYPE_529, "529 college savings plans Account"),
    (ACCOUNT_TYPE_ESA, "Coverdell Educational Savings Account (ESA) Account"),
    (ACCOUNT_TYPE_UG, "UGMA/UTMA Account"),
    (ACCOUNT_TYPE_GUARDIANSHIP, "Guardianship of the Estate Account"),
    (ACCOUNT_TYPE_CUSTODIAL, "Custodial Account"),
    (ACCOUNT_TYPE_THRIFTSAVING, "Thrift Savings Account"),
    (ACCOUNT_TYPE_QUALIFIEDANNUITY, "Qualified Annuity Plan"),
    (ACCOUNT_TYPE_TAXDEFERRED_ANNUITY, "Tax Deferred Annuity Plan"),
    (ACCOUNT_TYPE_QUALIFIEDNPPLAN, "Qualified Nonprofit Plan"),
    (ACCOUNT_TYPE_QUALIFIEDNPROTHPLAN, "Qualified Nonprofit Roth Plan"),
    (ACCOUNT_TYPE_QUALIFIEDPRIV457PLAN, "Private 457 Plan"),
    (ACCOUNT_TYPE_INDIVDUAL401K, "Individual 401k Account"),
    (ACCOUNT_TYPE_INDROTH401K, "Individual 401k Roth Account"),
    (ACCOUNT_TYPE_VARIABLEANNUITY, "Variable Annuity"),
    (ACCOUNT_TYPE_SINGLELIFEANNUITY, "Single Life Annuity"),
    (ACCOUNT_TYPE_JOINTSURVIVORANNUITY, "Joint & Survivor Annuity"),
)
ACCOUNT_TYPES_COUNTRY = {
    'AU': [
        ACCOUNT_TYPE_PERSONAL,
        ACCOUNT_TYPE_JOINT,
        ACCOUNT_TYPE_TRUST,
        ACCOUNT_TYPE_SMSF,
        ACCOUNT_TYPE_CORPORATE,
    ],
    'US': [
        ACCOUNT_TYPE_PERSONAL,
        ACCOUNT_TYPE_JOINT,
        ACCOUNT_TYPE_TRUST,
        ACCOUNT_TYPE_INVESTCLUBORGANIZATION,
        ACCOUNT_TYPE_PARTNERSHIPORGANIZATION,
        ACCOUNT_TYPE_SOLEPROPORGANIZATION,
        ACCOUNT_TYPE_LLCORGANIZATION,
        ACCOUNT_TYPE_ASSOCIATIONORGANIZATION,
        ACCOUNT_TYPE_NONCORPORATIONORGANIZATION,
        ACCOUNT_TYPE_PENSION,
        ACCOUNT_TYPE_401K,
        ACCOUNT_TYPE_ROTH401K,
        ACCOUNT_TYPE_IRA,
        ACCOUNT_TYPE_ROTHIRA,
        ACCOUNT_TYPE_SEPIRA,
        ACCOUNT_TYPE_403K,
        ACCOUNT_TYPE_SIMPLEIRA,
        ACCOUNT_TYPE_SARSEPIRA,
        ACCOUNT_TYPE_PAYROLLDEDUCTIRA,
        ACCOUNT_TYPE_PROFITSHARING,
        ACCOUNT_TYPE_MONEYPURCHASE,
        ACCOUNT_TYPE_ESOP,
        ACCOUNT_TYPE_GOVERMENTAL,
        ACCOUNT_TYPE_457,
        ACCOUNT_TYPE_409A,
        ACCOUNT_TYPE_403B,
        ACCOUNT_TYPE_HSA,
        ACCOUNT_TYPE_529,
        ACCOUNT_TYPE_ESA,
        ACCOUNT_TYPE_UG,
        ACCOUNT_TYPE_GUARDIANSHIP,
        ACCOUNT_TYPE_CUSTODIAL,
        ACCOUNT_TYPE_THRIFTSAVING,
        ACCOUNT_TYPE_QUALIFIEDANNUITY,
        ACCOUNT_TYPE_TAXDEFERRED_ANNUITY,
        ACCOUNT_TYPE_QUALIFIEDNPPLAN,
        ACCOUNT_TYPE_QUALIFIEDNPROTHPLAN,
        ACCOUNT_TYPE_QUALIFIEDPRIV457PLAN,
        ACCOUNT_TYPE_INDIVDUAL401K,
        ACCOUNT_TYPE_INDROTH401K,
    ],
}
US_RETIREMENT_ACCOUNT_TYPES = [
    ACCOUNT_TYPE_401A,
    ACCOUNT_TYPE_401K,
    ACCOUNT_TYPE_403B,
    ACCOUNT_TYPE_403K,
    ACCOUNT_TYPE_409A,
    ACCOUNT_TYPE_457,
    ACCOUNT_TYPE_ESOP,
    ACCOUNT_TYPE_GOVERMENTAL,
    ACCOUNT_TYPE_INDIVDUAL401K,
    ACCOUNT_TYPE_INDROTH401K,
    ACCOUNT_TYPE_IRA,
    ACCOUNT_TYPE_MONEYPURCHASE,
    ACCOUNT_TYPE_PAYROLLDEDUCTIRA,
    ACCOUNT_TYPE_PROFITSHARING,
    ACCOUNT_TYPE_QUALIFIEDANNUITY,
    ACCOUNT_TYPE_QUALIFIEDNPPLAN,
    ACCOUNT_TYPE_QUALIFIEDNPROTHPLAN,
    ACCOUNT_TYPE_QUALIFIEDPRIV457PLAN,
    ACCOUNT_TYPE_ROTH401K,
    ACCOUNT_TYPE_ROTHIRA,
    ACCOUNT_TYPE_SARSEPIRA,
    ACCOUNT_TYPE_SEPIRA,
    ACCOUNT_TYPE_SIMPLEIRA,
    ACCOUNT_TYPE_TAXDEFERRED_ANNUITY,
]
JOINT_ACCOUNT_TYPE_COMMUNITY_PROPERTY = 1
JOINT_ACCOUNT_TYPE_JOINT_TENANTS = 2
JOINT_ACCOUNT_TYPE_TENANTS_BY_ENTIRETY = 3
JOINT_ACCOUNT_TYPE_TENANTS_IN_COMMON = 4
JOINT_ACCOUNT_TYPES = (
    (JOINT_ACCOUNT_TYPE_COMMUNITY_PROPERTY, 'Community Property'),
    (JOINT_ACCOUNT_TYPE_JOINT_TENANTS, 'Joint Tenants'),
    (JOINT_ACCOUNT_TYPE_TENANTS_BY_ENTIRETY, 'Tenants by Entirety'),
    (JOINT_ACCOUNT_TYPE_TENANTS_IN_COMMON, 'Tenants in Common'),
)
YAHOO_API = "YAHOO"
GOOGLE_API = "GOOGLE"
API_CHOICES = ((YAHOO_API, "YAHOO"), (GOOGLE_API, 'GOOGLE'))
_asset_fee_ht = "List of level transition points and the new values after that transition. Eg. '0: 0.001, 10000: 0.0'"
PERFORMER_GROUP_STRATEGY = "PERFORMER_GROUP_STRATEGY"
PERFORMER_GROUP_BENCHMARK = "PERFORMER_GROUP_BENCHMARK"
PERFORMER_GROUP_BOND = "PERFORMER_GROUP_BOND"
PERFORMER_GROUP_STOCK = "PERFORMER_GROUP_STOCK"
PERFORMER_GROUP_CHOICE = (
    (PERFORMER_GROUP_STRATEGY, "PERFORMER_GROUP_STRATEGY"),
    (PERFORMER_GROUP_BENCHMARK, "PERFORMER_GROUP_BENCHMARK"),
    (PERFORMER_GROUP_BOND, "PERFORMER_GROUP_BOND"),
    (PERFORMER_GROUP_STOCK, "PERFORMER_GROUP_STOCK")
)

CLIENT_FULL_ACCESS = 1
CLIENT_READONLY_ACCESS = 2
CLIENT_NO_ACCESS = 3

CLIENT_ACCESS_LEVEL_CHOICES = (
    (CLIENT_FULL_ACCESS, 'Client Full Access'),
    (CLIENT_READONLY_ACCESS, 'Client Read Only Access'),
    (CLIENT_NO_ACCESS, 'No Client Access'),
)

GENDER_MALE = "Male"
GENDER_FEMALE = "Female"
GENDERS = ((GENDER_MALE, "Male"), (GENDER_FEMALE, "Female"))

OCCUPATION_TYPES = (
    ('11-0000', 'Management'),
    ('13-0000', 'Business and Financial Operations'),
    ('15-0000', 'Computer and Mathematical'),
    ('17-0000', 'Architecture and Engineering'),
    ('19-0000', 'Life, Physical, and Social Science'),
    ('21-0000', 'Community and Social Services'),
    ('23-0000', 'Legal'),
    ('25-0000', 'Education, Training, and Library'),
    ('27-0000', 'Arts, Design, Entertainment, Sports, and Media'),
    ('29-0000', 'Healthcare Practitioners and Technical'),
    ('31-0000', 'Healthcare Support'),
    ('33-0000', 'Protective Service'),
    ('35-0000', 'Food Preparation and Serving Related'),
    ('37-0000', 'Building and Grounds Cleaning and Maintenance'),
    ('39-0000', 'Personal Care and Service'),
    ('41-0000', 'Sales and Related'),
    ('43-0000', 'Office and Administrative Support'),
    ('45-0000', 'Farming, Fishing, and Forestry'),
    ('47-0000', 'Construction and Extraction'),
    ('49-0000', 'Installation, Maintenance, and Repair'),
    ('51-0000', 'Production'),
    ('53-0000', 'Transportation and Material Moving'),
    ('55-0000', 'Military Specific')
)

INDUSTRY_TYPES = (
    ('NAICS 11',    'Agriculture, Forestry, Fishing and Hunting'),
    ('NAICS 21',    'Mining, Quarrying, and Oil and Gas Extraction'),
    ('NAICS 23',    'Construction'),
    ('NAICS 31-33', 'Manufacturing'),
    ('NAICS 42',    'Wholesale Trade'),
    ('NAICS 44-45', 'Retail Trade '),
    ('NAICS 48-49', 'Transportation and Warehousing'),
    ('NAICS 22',    'Utilities'),
    ('NAICS 51',    'Information'),
    ('NAICS 52',    'Finance and Insurance '),
    ('NAICS 53',    'Real Estate and Rental and Leasing '),
    ('NAICS 531',   'Real Estate '),
    ('NAICS 54',    'Professional, Scientific, and Technical Services '),
    ('NAICS 55',    'Management of Companies and Enterprises '),
    ('NAICS 56',    'Administrative and Support and Waste Management and Remediation Services'),
    ('NAICS 61',    'Educational Services'),
    ('NAICS 62',    'Health Care and Social Assistance'),
    ('NAICS 71',    'Arts, Entertainment, and Recreation'),
    ('NAICS 72',    'Accommodation and Food Services '),
    ('NAICS 81',    'Other Services')
)

EMPLOYER_OVER_100 = 0
EMPLOYER_UNDER_100 = 1
EMPLOYER_OWNER_OR_SPOUSE = 2
EMPLOYER_PRIVATE_NPO = 3
EMPLOYER_PUBLIC_NPO = 4
EMPLOYER_GOVERNMENT = 5

EMPLOYER_TYPES = (
    (EMPLOYER_OVER_100, 'For-profit business (100+ employees)'),
    (EMPLOYER_UNDER_100, 'For-profit business (up to 100 employees)'),
    (EMPLOYER_OWNER_OR_SPOUSE, 'For-profit business (only business owner and spouse)'),
    (EMPLOYER_PRIVATE_NPO, 'Non-profit private organization'),
    (EMPLOYER_PUBLIC_NPO, 'Non-profit public organization'),
    (EMPLOYER_GOVERNMENT, 'Government (Local, State, Federal)'),
)

LIFESTYLE_DOING_OK_MULTIPLIER = 0.66
LIFESTYLE_COMFORTABLE_MULTIPLIER = 0.81
LIFESTYLE_DOING_WELL_MULTIPLIER = 1.0
LIFESTYLE_LUXURY_MULTIPLIER = 1.5


PORTFOLIO_PROVIDER_TYPE_BETASMARTZ = 0
PORTFOLIO_PROVIDER_TYPE_AON = 1
PORTFOLIO_PROVIDER_TYPE_KRANE = 2
PORTFOLIO_PROVIDER_TYPE_LEE = 3

PORTFOLIO_PROVIDER_TYPE_CHOICES = (
    (PORTFOLIO_PROVIDER_TYPE_BETASMARTZ, 'BetaSmartz'),
    (PORTFOLIO_PROVIDER_TYPE_AON, 'Aon'),
    (PORTFOLIO_PROVIDER_TYPE_KRANE, 'Krane'),
    (PORTFOLIO_PROVIDER_TYPE_LEE, 'Lee'),
)


PORTFOLIO_SET_TYPE_BETASMARTZ = 0
PORTFOLIO_SET_TYPE_AON = 1
PORTFOLIO_SET_TYPE_KRANE = 2
PORTFOLIO_SET_TYPE_LEE = 3
PORTFOLIO_SET_TYPE_AON_ST = 4
PORTFOLIO_SET_TYPE_KRANE_FI = 5
PORTFOLIO_SET_TYPE_KRANE_EQ = 6

PORTFOLIO_SET_TYPE_CHOICES = (
    (PORTFOLIO_SET_TYPE_BETASMARTZ, 'BetaSmartz'),
    (PORTFOLIO_SET_TYPE_AON, 'Aon goals based'),
    (PORTFOLIO_SET_TYPE_AON_ST, 'Aon strategic'),
    (PORTFOLIO_SET_TYPE_KRANE, 'Krane multi-asset'),
    (PORTFOLIO_SET_TYPE_KRANE_FI, 'Krane single-asset (fixed income)'),
    (PORTFOLIO_SET_TYPE_KRANE_EQ, 'Krane single-asset (equity)'),
    (PORTFOLIO_SET_TYPE_LEE, 'Lee multi-asset'),
)


THEME_BETASMARTZ = 'betasmartz'
THEME_OREANA = 'oreana'

THEME_CHOICES = (
    (THEME_BETASMARTZ, 'BetaSmartz'),
    (THEME_OREANA, 'Oreana'),
)

COMMENTARY_PORTFOLIO_INFO = 1
COMMENTARY_ECONOMIC_INFO = 2
COMMENTARY_MARKET_INFO = 3
COMMENTARY_RISK_MANAGEMENT = 4

COMMENTARY_CATEGORY_CHOICES = (
    (COMMENTARY_PORTFOLIO_INFO, 'Portfolio Information'),
    (COMMENTARY_ECONOMIC_INFO, 'Economic Information'),
    (COMMENTARY_MARKET_INFO, 'Market Information'),
    (COMMENTARY_RISK_MANAGEMENT, 'Risk Management'),
)
