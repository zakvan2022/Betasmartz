import json
 
'''
The following rates, brackets, deductions and exemptions are taken from on Andrew's
Excel tax sheet (Retirement Modelling v4.xlsx).
'''

STATE_AL = """{"state": "AL",
                "Single":
                    [{"rate": 0.02, "bracket": 0.0},
                    {"rate": 0.04, "bracket": 500.0},
                    {"rate": 0.05, "bracket": 3000.0}]
                ,
                "Married Filing Jointly":
                    [{"rate": 0.02, "bracket": 0.0},
                    {"rate": 0.04, "bracket": 1000.0},
                    {"rate": 0.05, "bracket": 6000.0}]
                    ,
                 "standard_deduction": [{"single": 2500.0}, {"couple": 7500.0}],
                 "personal_exemption": [{"single": 1500.0}, {"couple": 3000.0},{"dependent": 1000.0} ]
                }"""

STATE_AK = """{"state": "AK",
                "Single":
                    {"rate": 0.0, "bracket": 0.0}
                ,
                "Married Filing Jointly":
                    {"rate": 0.0, "bracket": 0.0}
                ,
                 "standard_deduction": [{"single": 0.0}, {"couple": 0.0}],
                 "personal_exemption": [{"single": 0.0}, {"couple": 0.0},{"dependent": 0.0} ]
                }"""

STATE_AZ = """{"state": "AZ",
                "Single":
                    [{"rate": 0.0259, "bracket": 0.0},
                    {"rate": 0.0288, "bracket": 10000.0},
                    {"rate": 0.0336, "bracket": 25000.0},
                    {"rate": 0.0424, "bracket": 50000.0},
                    {"rate": 0.0454, "bracket": 150000.0}]
                ,
                "Married Filing Jointly":
                    [{"rate": 0.0259, "bracket": 0.0},
                    {"rate": 0.0288, "bracket": 20000.0},
                    {"rate": 0.0336, "bracket": 50000.0},
                    {"rate": 0.0424, "bracket": 100000.0},
                    {"rate": 0.0454, "bracket": 300000.0}]
                ,
                 "standard_deduction": [{"single": 5091.0}, {"couple": 10173.0}],
                 "personal_exemption": [{"single": 2100.0}, {"couple": 4200.0},{"dependent": 2100.0} ]
                }"""

STATE_AR = """{"state": "AR",
                "Single":
                    [{"rate": 0.009, "bracket": 0.0},
                    {"rate": 0.025, "bracket": 4299.0},
                    {"rate": 0.035, "bracket": 8399.0},
                    {"rate": 0.045, "bracket": 12599.0},
                    {"rate": 0.06, "bracket": 20999.0},
                    {"rate": 0.069, "bracket": 35099.0}]
                ,
                "Married Filing Jointly":
                    [{"rate": 0.009, "bracket": 0.0},
                    {"rate": 0.025, "bracket": 4299.0},
                    {"rate": 0.035, "bracket": 8399.0},
                    {"rate": 0.045, "bracket": 12599.0},
                    {"rate": 0.06, "bracket": 20999.0},
                    {"rate": 0.069, "bracket": 35099.0}]
                ,
                 "standard_deduction": [{"single": 2200.0}, {"couple": 4400.0}],
                 "personal_exemption": [{"single": 26.0}, {"couple": 52.0},{"dependent": 26.0} ]
                }"""

STATE_CA = """{"state": "CA",
                "Single":
                    [{"rate": 0.01, "bracket": 0.0},
                    {"rate": 0.02, "bracket": 7850.0},
                    {"rate": 0.04, "bracket": 18610.0},
                    {"rate": 0.06, "bracket": 29372.0},
                    {"rate": 0.08, "bracket": 40773.0},
                    {"rate": 0.093, "bracket": 51530.0},
                    {"rate": 0.103, "bracket": 263222.0},
                    {"rate": 0.113, "bracket": 315866.0},
                    {"rate": 0.123, "bracket": 526443.0},
                    {"rate": 0.133, "bracket": 1000000.0}]
                ,
                "Married Filing Jointly":
                    [{"rate": 0.01, "bracket": 0.0},
                    {"rate": 0.02, "bracket": 15700.0},
                    {"rate": 0.04, "bracket": 37220.0},
                    {"rate": 0.06, "bracket": 58744.0},
                    {"rate": 0.08, "bracket": 81546.0},
                    {"rate": 0.093, "bracket": 103060.0},
                    {"rate": 0.103, "bracket": 526444.0},
                    {"rate": 0.113, "bracket": 631732.0},
                    {"rate": 0.123, "bracket": 1000000.0},
                    {"rate": 0.133, "bracket": 1052886.0}]
                ,
                 "standard_deduction": [{"single": 4044.0}, {"couple": 8088.0}],
                 "personal_exemption": [{"single": 109.0}, {"couple": 218.0},{"dependent": 337.0} ]
                }"""

STATE_CO = """{"state": "CO",
                "Single":
                    {"rate": 0.0463, "bracket": 0.0}
                ,
                "Married Filing Jointly":
                    {"rate": 0.0463, "bracket": 0.0}
                ,
                 "standard_deduction": [{"single": 0.0}, {"couple": 0.0}],
                 "personal_exemption": [{"single": 0.0}, {"couple": 0.0},{"dependent": 0.0} ]
                }"""

STATE_CT = """{"state": "CT",
                "Single":
                    [{"rate": 0.03, "bracket": 0.0},
                    {"rate": 0.05, "bracket": 10000.0},
                    {"rate": 0.055, "bracket": 50000.0},
                    {"rate": 0.06, "bracket": 100000.0},
                    {"rate": 0.065, "bracket": 200000.0},
                    {"rate": 0.069, "bracket": 250000.0},
                    {"rate": 0.0699, "bracket": 500000.0}]
                ,
                "Married Filing Jointly":
                    [{"rate": 0.03, "bracket": 0.0},
                    {"rate": 0.05, "bracket": 20000.0},
                    {"rate": 0.055, "bracket": 100000.0},
                    {"rate": 0.06, "bracket": 200000.0},
                    {"rate": 0.065, "bracket": 400000.0},
                    {"rate": 0.069, "bracket": 500000.0},
                    {"rate": 0.0699, "bracket": 1000000.0}]
                ,
                 "standard_deduction": [{"single": 0.0}, {"couple": 0.0}],
                 "personal_exemption": [{"single": 15000.0}, {"couple": 24000.0},{"dependent": 0.0} ]
                }"""

STATE_DE = """{"state": "DE",
                "Single":
                    [{"rate": 0.022, "bracket": 2000.0},
                    {"rate": 0.039, "bracket": 5000.0},
                    {"rate": 0.048, "bracket": 10000.0},
                    {"rate": 0.052, "bracket": 20000.0},
                    {"rate": 0.0555, "bracket": 25000.0},
                    {"rate": 0.066, "bracket": 60000.0}]
                ,
                "Married Filing Jointly":
                    [{"rate": 0.022, "bracket": 2000.0},
                    {"rate": 0.039, "bracket": 5000.0},
                    {"rate": 0.048, "bracket": 10000.0},
                    {"rate": 0.052, "bracket": 20000.0},
                    {"rate": 0.0555, "bracket": 25000.0},
                    {"rate": 0.066, "bracket": 60000.0}]
                ,
                 "standard_deduction": [{"single": 3250.0}, {"couple": 6500.0}],
                 "personal_exemption": [{"single": 110.0}, {"couple": 220.0},{"dependent": 110.0} ]
                }"""

STATE_FL = """{"state": "FL",
                "Single":
                    {"rate": 0.0463, "bracket": 0.0}
                ,
                "Married Filing Jointly":
                    {"rate": 0.0463, "bracket": 0.0}
                ,
                 "standard_deduction": [{"single": 0.0}, {"couple": 0.0}],
                 "personal_exemption": [{"single": 0.0}, {"couple": 0.0},{"dependent": 0.0} ]
                }"""

STATE_GA = """{"state": "GA",
                "Single":
                    [{"rate": 0.01, "bracket": 0.0},
                    {"rate": 0.02, "bracket": 750.0},
                    {"rate": 0.03, "bracket": 2250.0},
                    {"rate": 0.04, "bracket": 3750.0},
                    {"rate": 0.05, "bracket": 5250.0},
                    {"rate": 0.06, "bracket": 7000.0}]
                ,
                "Married Filing Jointly":
                    [{"rate": 0.01, "bracket": 0.0},
                    {"rate": 0.02, "bracket": 1000.0},
                    {"rate": 0.03, "bracket": 3000.0},
                    {"rate": 0.04, "bracket": 5000.0},
                    {"rate": 0.05, "bracket": 7000.0},
                    {"rate": 0.06, "bracket": 10000.0}]
                ,
                 "standard_deduction": [{"single": 2300.0}, {"couple": 3000.0}],
                 "personal_exemption": [{"single": 2700.0}, {"couple": 7400.0},{"dependent": 3000.0} ]
                }"""

STATE_HI = """{"state": "HI",
                "Single":
                    [{"rate": 0.014, "bracket": 0.0},
                    {"rate": 0.032, "bracket": 2400.0},
                    {"rate": 0.055, "bracket": 4800.0},
                    {"rate": 0.064, "bracket": 9600.0},
                    {"rate": 0.068, "bracket": 14400.0},
                    {"rate": 0.072, "bracket": 19200.0},
                    {"rate": 0.076, "bracket": 24000.0},
                    {"rate": 0.079, "bracket": 36000.0},
                    {"rate": 0.0825, "bracket": 48000.0}]
                ,
                "Married Filing Jointly":
                    [{"rate": 0.014, "bracket": 0.0},
                    {"rate": 0.032, "bracket": 4800.0},
                    {"rate": 0.055, "bracket": 9600.0},
                    {"rate": 0.064, "bracket": 19200.0},
                    {"rate": 0.068, "bracket": 28800.0},
                    {"rate": 0.072, "bracket": 38400.0},
                    {"rate": 0.076, "bracket": 48000.0},
                    {"rate": 0.079, "bracket": 72000.0},
                    {"rate": 0.0825, "bracket": 96000.0}]
                ,
                 "standard_deduction": [{"single": 2200.0}, {"couple": 4400.0}],
                 "personal_exemption": [{"single": 1144.0}, {"couple": 2288.0},{"dependent": 1144.0} ]
                }"""

STATE_ID = """{"state": "ID",
                "Single":
                    [{"rate": 0.016, "bracket": 0.0},
                    {"rate": 0.036, "bracket": 1452.0},
                    {"rate": 0.041, "bracket": 2940.0},
                    {"rate": 0.051, "bracket": 4356.0},
                    {"rate": 0.061, "bracket": 5808.0},
                    {"rate": 0.071, "bracket": 7260.0},
                    {"rate": 0.074, "bracket": 10890.0}]
                ,
                "Married Filing Jointly":
                    [{"rate": 0.016, "bracket": 0.0},
                    {"rate": 0.036, "bracket": 2904.0},
                    {"rate": 0.041, "bracket": 5808.0},
                    {"rate": 0.051, "bracket": 8712.0},
                    {"rate": 0.061, "bracket": 11616.0},
                    {"rate": 0.071, "bracket": 14520.0},
                    {"rate": 0.074, "bracket": 21780.0}]
                ,
                 "standard_deduction": [{"single": 6300.0}, {"couple": 12600.0}],
                 "personal_exemption": [{"single": 4000.0}, {"couple": 8000.0},{"dependent": 4000.0} ]
                }"""

STATE_IL = """{"state": "IL",
                "Single":
                    {"rate": 0.0375, "bracket": 0.0}
                ,
                "Married Filing Jointly":
                    {"rate": 0.0375, "bracket": 0.0}
                ,
                 "standard_deduction": [{"single": 0.0}, {"couple": 0.0}],
                 "personal_exemption": [{"single": 2125.0}, {"couple": 4250.0},{"dependent": 2125.0} ]
                }"""

STATE_IN = """{"state": "IN",
                "Single":
                    {"rate": 0.033, "bracket": 0.0}
                ,
                "Married Filing Jointly":
                    {"rate": 0.033, "bracket": 0.0}
                ,
                 "standard_deduction": [{"single": 0.0}, {"couple": 0.0}],
                 "personal_exemption": [{"single": 1000.0}, {"couple": 2000.0},{"dependent": 1500.0} ]
                }"""

STATE_IO = """{"state": "IO",
                "Single":
                    [{"rate": 0.0036, "bracket": 0.0},
                    {"rate": 0.0072, "bracket": 1554.0},
                    {"rate": 0.0243, "bracket": 3108.0},
                    {"rate": 0.045, "bracket": 6216.0},
                    {"rate": 0.0612, "bracket": 13896.0},
                    {"rate": 0.0648, "bracket": 23310.0},
                    {"rate": 0.068, "bracket": 31080.0},
                    {"rate": 0.0792, "bracket": 46620.0},
                    {"rate": 0.0898, "bracket": 69930.0}]
                ,
                "Married Filing Jointly":
                    [{"rate": 0.0036, "bracket": 0.0},
                    {"rate": 0.0072, "bracket": 1554.0},
                    {"rate": 0.0243, "bracket": 3108.0},
                    {"rate": 0.045, "bracket": 6216.0},
                    {"rate": 0.0612, "bracket": 13896.0},
                    {"rate": 0.0648, "bracket": 23310.0},
                    {"rate": 0.068, "bracket": 31080.0},
                    {"rate": 0.0792, "bracket": 46620.0},
                    {"rate": 0.0898, "bracket": 69930.0}]
                ,
             "standard_deduction": [{"single": 1970.0}, {"couple": 4860.0}],
                 "personal_exemption": [{"single": 40.0}, {"couple": 40.0},{"dependent": 40.0} ]
                }"""

STATE_KS = """{"state": "KS",
                "Single":
                    [{"rate": 0.027, "bracket": 0.0},
                    {"rate": 0.046, "bracket": 15000.0}]
                ,
                "Married Filing Jointly":
                    [{"rate": 0.027, "bracket": 0.0},
                    {"rate": 0.046, "bracket": 30000.0}]
                ,
                 "standard_deduction": [{"single": 3000.0}, {"couple": 7500.0}],
                 "personal_exemption": [{"single": 2250.0}, {"couple": 4500.0},{"dependent": 2250.0} ]
                }"""

STATE_KY = """{"state": "KY",
                "Single":
                    [{"rate": 0.02, "bracket": 0.0},
                    {"rate": 0.03, "bracket": 3000.0},
                    {"rate": 0.04, "bracket": 4000.0},
                    {"rate": 0.05, "bracket": 5000.0},
                    {"rate": 0.058, "bracket": 8000.0},
                    {"rate": 0.06, "bracket": 75000.0}]
                ,
                "Married Filing Jointly":
                    [{"rate": 0.02, "bracket": 0.0},
                    {"rate": 0.03, "bracket": 3000.0},
                    {"rate": 0.04, "bracket": 4000.0},
                    {"rate": 0.05, "bracket": 5000.0},
                    {"rate": 0.058, "bracket": 8000.0},
                    {"rate": 0.06, "bracket": 75000.0}]
                ,
                 "standard_deduction": [{"single": 2460.0}, {"couple": 2460.0}],
                 "personal_exemption": [{"single": 10.0}, {"couple": 10.0},{"dependent": 10.0} ]
                }"""

STATE_LA = """{"state": "LA",
                "Single":
                    [{"rate": 0.02, "bracket": 0.0},
                    {"rate": 0.04, "bracket": 12500.0},
                    {"rate": 0.06, "bracket": 50000.0}]
                ,
                "Married Filing Jointly":
                    [{"rate": 0.02, "bracket": 0.0},
                    {"rate": 0.04, "bracket": 25000.0},
                    {"rate": 0.06, "bracket": 100000.0}]
                ,
                 "standard_deduction": [{"single": 0.0}, {"couple": 0.0}],
                 "personal_exemption": [{"single": 4500.0}, {"couple": 9000.0},{"dependent": 1000.0} ]
                }"""

STATE_ME = """{"state": "ME",
                "Single":
                    [{"rate": 0.058, "bracket": 0.0},
                    {"rate": 0.0675, "bracket": 21049.0},
                    {"rate": 0.0715, "bracket": 37499.0}]
                ,
                "Married Filing Jointly":
                    [{"rate": 0.058, "bracket": 0.0},
                    {"rate": 0.0675, "bracket": 42099.0},
                    {"rate": 0.0715, "bracket": 74999.0}]
                ,
                 "standard_deduction": [{"single": 11600.0}, {"couple": 23200.0}],
                 "personal_exemption": [{"single": 4050.0}, {"couple": 8100.0},{"dependent": 4050.0} ]
                }"""

STATE_MD = """{"state": "MD",
                "Single":
                    [{"rate": 0.02, "bracket": 0.0},
                    {"rate": 0.03, "bracket": 1000.0},
                    {"rate": 0.04, "bracket": 2000.0},
                    {"rate": 0.0475, "bracket": 3000.0},
                    {"rate": 0.05, "bracket": 100000.0},
                    {"rate": 0.0525, "bracket": 125000.0},
                    {"rate": 0.055, "bracket": 150000.0},
                    {"rate": 0.0575, "bracket": 250000.0}]
                ,
                "Married Filing Jointly":
                    [{"rate": 0.02, "bracket": 0.0},
                    {"rate": 0.03, "bracket": 1000.0},
                    {"rate": 0.04, "bracket": 2000.0},
                    {"rate": 0.0475, "bracket": 3000.0},
                    {"rate": 0.05, "bracket": 150000.0},
                    {"rate": 0.0525, "bracket": 175000.0},
                    {"rate": 0.055, "bracket": 225000.0},
                    {"rate": 0.0575, "bracket": 300000.0}]
                ,
                 "standard_deduction": [{"single": 2000.0}, {"couple": 4000.0}],
                 "personal_exemption": [{"single": 3200.0}, {"couple": 6400.0},{"dependent": 3200.0} ]
                }"""

STATE_MA = """{"state": "MA",
                "Single":
                    {"rate": 0.051, "bracket": 0.0}
                ,
                "Married Filing Jointly":
                    {"rate": 0.051, "bracket": 0.0}
                ,
                 "standard_deduction": [{"single": 0.0}, {"couple": 0.0}],
                 "personal_exemption": [{"single": 4400.0}, {"couple": 8800.0},{"dependent": 1000.0} ]
                }"""

STATE_MI = """{"state": "MI",
                "Single":
                    {"rate": 0.0425, "bracket": 0.0}
                ,
                "Married Filing Jointly":
                    {"rate": 0.0425, "bracket": 0.0}
                ,
                 "standard_deduction": [{"single": 0.0}, {"couple": 0.0}],
                 "personal_exemption": [{"single": 4000.0}, {"couple": 4000.0},{"dependent": 0.0} ]
                }"""

STATE_MN = """{"state": "MN",
                "Single":
                    [{"rate": 0.0535, "bracket": 0.0},
                    {"rate": 0.0705, "bracket": 25180.0},
                    {"rate": 0.0785, "bracket": 82740.0},
                    {"rate": 0.0985, "bracket": 155650.0}]
                ,
                "Married Filing Jointly":
                    [{"rate": 0.0535, "bracket": 0.0},
                    {"rate": 0.0705, "bracket": 36820.0},
                    {"rate": 0.0785, "bracket": 146270.0},
                    {"rate": 0.0985, "bracket": 259420.0}]
                ,
                 "standard_deduction": [{"single": 6300.0}, {"couple": 12600.0}],
                 "personal_exemption": [{"single": 4000.0}, {"couple": 8000.0},{"dependent": 4000.0} ]
                }"""

STATE_MS = """{"state": "MS",
                "Single":
                    [{"rate": 0.03, "bracket": 0.0},
                    {"rate": 0.04, "bracket": 5000.0},
                    {"rate": 0.05, "bracket": 100000.0}]
                ,
                "Married Filing Jointly":
                    [{"rate": 0.03, "bracket": 0.0},
                    {"rate": 0.04, "bracket": 5000.0},
                    {"rate": 0.05, "bracket": 100000.0}]
                ,
                 "standard_deduction": [{"single": 2300.0}, {"couple": 4600.0}],
                 "personal_exemption": [{"single": 6000.0}, {"couple": 12000.0},{"dependent": 1500.0} ]
                }"""

STATE_MO = """{"state": "MO",
                "Single":
                    [{"rate": 0.015, "bracket": 0.0},
                    {"rate": 0.02, "bracket": 1000.0},
                    {"rate": 0.025, "bracket": 2000.0},
                    {"rate": 0.03, "bracket": 3000.0},
                    {"rate": 0.035, "bracket": 4000.0},
                    {"rate": 0.04, "bracket": 5000.0},
                    {"rate": 0.045, "bracket": 6000.0},
                    {"rate": 0.05, "bracket": 7000.0},
                    {"rate": 0.055, "bracket": 8000.0},
                    {"rate": 0.06, "bracket": 9000.0}]
                ,
                "Married Filing Jointly":
                    [{"rate": 0.015, "bracket": 0.0},
                    {"rate": 0.02, "bracket": 1000.0},
                    {"rate": 0.025, "bracket": 2000.0},
                    {"rate": 0.03, "bracket": 3000.0},
                    {"rate": 0.035, "bracket": 4000.0},
                    {"rate": 0.04, "bracket": 5000.0},
                    {"rate": 0.045, "bracket": 6000.0},
                    {"rate": 0.05, "bracket": 7000.0},
                    {"rate": 0.055, "bracket": 8000.0},
                    {"rate": 0.06, "bracket": 9000.0}]
                ,
                 "standard_deduction": [{"single": 6300.0}, {"couple": 12600.0}],
                 "personal_exemption": [{"single": 2100.0}, {"couple": 4200.0},{"dependent": 1200.0} ]
                }"""

STATE_MT = """{"state": "MT",
                "Single":
                    [{"rate": 0.01, "bracket": 0.0},
                    {"rate": 0.02, "bracket": 2900.0},
                    {"rate": 0.03, "bracket": 5100.0},
                    {"rate": 0.04, "bracket": 7800.0},
                    {"rate": 0.05, "bracket": 10500.0},
                    {"rate": 0.06, "bracket": 13500.0},
                    {"rate": 0.069, "bracket": 17400.0}]
                ,
                "Married Filing Jointly":
                    [{"rate": 0.01, "bracket": 0.0},
                    {"rate": 0.02, "bracket": 2900.0},
                    {"rate": 0.03, "bracket": 5100.0},
                    {"rate": 0.04, "bracket": 7800.0},
                    {"rate": 0.05, "bracket": 10500.0},
                    {"rate": 0.06, "bracket": 13500.0},
                    {"rate": 0.069, "bracket": 17400.0}]
                ,
                 "standard_deduction": [{"single": 4370.0}, {"couple": 8740.0}],
                 "personal_exemption": [{"single": 2330.0}, {"couple": 4660.0},{"dependent": 2300.0} ]
                }"""

STATE_NE = """{"state": "NE",
                "Single":
                    [{"rate": 0.0246, "bracket": 0.0},
                    {"rate": 0.0351, "bracket": 3060.0},
                    {"rate": 0.0501, "bracket": 18370.0},
                    {"rate": 0.0684, "bracket": 29590.0}]
                ,
                "Married Filing Jointly":
                    [{"rate": 0.0246, "bracket": 0.0},
                    {"rate": 0.0351, "bracket": 6120.0},
                    {"rate": 0.0501, "bracket": 36730.0},
                    {"rate": 0.0684, "bracket": 59180.0}]
                ,
                 "standard_deduction": [{"single": 6300.0}, {"couple": 12600.0}],
                 "personal_exemption": [{"single": 131.0}, {"couple": 262.0},{"dependent": 131.0} ]
                }"""

STATE_NV = """{"state": "NV",
                "Single":
                    {"rate": 0.0, "bracket": 0.0}
                ,
                "Married Filing Jointly":
                    {"rate": 0.0, "bracket": 0.0}
                ,
                 "standard_deduction": [{"single": 0.0}, {"couple": 0.0}],
                 "personal_exemption": [{"single": 0.0}, {"couple": 0.0},{"dependent": 0.0} ]
                }"""

STATE_NH = """{"state": "NH",
                "Single":
                    {"rate": 0.05, "bracket": 0.0}
                ,
                "Married Filing Jointly":
                    {"rate": 0.05, "bracket": 0.0}
                ,
                 "standard_deduction": [{"single": 0.0}, {"couple": 0.0}],
                 "personal_exemption": [{"single": 2400.0}, {"couple": 4800.0},{"dependent": 0.0} ]
                }"""

STATE_NJ = """{"state": "NJ",
                "Single":
                    [{"rate": 0.014, "bracket": 0.0},
                    {"rate": 0.0175, "bracket": 20000.0},
                    {"rate": 0.035, "bracket": 35000.0},
                    {"rate": 0.05525, "bracket": 40000.0},
                    {"rate": 0.0637, "bracket": 75000.0},
                    {"rate": 0.0897, "bracket": 500000.0}]
                ,
                "Married Filing Jointly":
                    [{"rate": 0.014, "bracket": 0.0},
                    {"rate": 0.0175, "bracket": 20000.0},
                    {"rate": 0.0245, "bracket": 50000.0},
                    {"rate": 0.035, "bracket": 70000.0},
                    {"rate": 0.05525, "bracket": 80000.0},
                    {"rate": 0.0637, "bracket": 150000.0},
                    {"rate": 0.0897, "bracket": 500000.0}]
                ,
                 "standard_deduction": [{"single": 0.0}, {"couple": 0.0}],
                 "personal_exemption": [{"single": 1000.0}, {"couple": 2000.0},{"dependent": 1500.0} ]
                }"""

STATE_NM = """{"state": "NM",
                "Single":
                    [{"rate": 0.017, "bracket": 0.0},
                    {"rate": 0.032, "bracket": 5500.0},
                    {"rate": 0.047, "bracket": 11000.0},
                    {"rate": 0.049, "bracket": 16000.0}]
                ,
                "Married Filing Jointly":
                    [{"rate": 0.017, "bracket": 0.0},
                    {"rate": 0.032, "bracket": 8000.0},
                    {"rate": 0.047, "bracket": 16000.0},
                    {"rate": 0.049, "bracket": 24000.0}]
                ,
                 "standard_deduction": [{"single": 6300.0}, {"couple": 12600.0}],
                 "personal_exemption": [{"single": 4000.0}, {"couple": 8000.0},{"dependent": 4000.0} ]
                }"""

STATE_NY = """{"state": "NY",
                "Single":
                    [{"rate": 0.04, "bracket": 0.0},
                    {"rate": 0.045, "bracket": 8450.0},
                    {"rate": 0.0525, "bracket": 11650.0},
                    {"rate": 0.059, "bracket": 13850.0},
                    {"rate": 0.0645, "bracket": 21300.0},
                    {"rate": 0.0665, "bracket": 80150.0},
                    {"rate": 0.0685, "bracket": 214000.0},
                    {"rate": 0.0882, "bracket": 1070350.0}]
                ,
                "Married Filing Jointly":
                    [{"rate": 0.04, "bracket": 0.0},
                    {"rate": 0.045, "bracket": 17050.0},
                    {"rate": 0.0525, "bracket": 23450.0},
                    {"rate": 0.059, "bracket": 27750.0},
                    {"rate": 0.0645, "bracket": 42750.0},
                    {"rate": 0.0665, "bracket": 160500.0},
                    {"rate": 0.0685, "bracket": 321050.0},
                    {"rate": 0.0882, "bracket": 2140900.0}]
                ,
                 "standard_deduction": [{"single": 7950.0}, {"couple": 15950.0}],
                 "personal_exemption": [{"single": 0.0}, {"couple": 0.0},{"dependent": 1000.0} ]
                }"""

STATE_NC = """{"state": "NC",
                "Single":
                    {"rate": 0.0575, "bracket": 0.0}
                ,
                "Married Filing Jointly":
                    {"rate": 0.0575, "bracket": 0.0}
                ,
                 "standard_deduction": [{"single": 7500.0}, {"couple": 15000.0}],
                 "personal_exemption": [{"single": 0.0}, {"couple": 0.0},{"dependent": 0.0} ]
                }"""

STATE_ND = """{"state": "ND",
                "Single":
                    [{"rate": 0.011, "bracket": 0.0},
                    {"rate": 0.0204, "bracket": 37450.0},
                    {"rate": 0.0227, "bracket": 90750.0},
                    {"rate": 0.0264, "bracket": 189300.0},
                    {"rate": 0.029, "bracket": 411500.0}]
                ,
                "Married Filing Jointly":
                    [{"rate": 0.011, "bracket": 0.0},
                    {"rate": 0.0204, "bracket": 62600.0},
                    {"rate": 0.0227, "bracket": 151200.0},
                    {"rate": 0.0264, "bracket": 230450.0},
                    {"rate": 0.029, "bracket": 411500.0}]
                ,
                 "standard_deduction": [{"single": 6300.0}, {"couple": 12600.0}],
                 "personal_exemption": [{"single": 4050.0}, {"couple": 8100.0},{"dependent": 4050.0} ]
                }"""

STATE_OH = """{"state": "OH",
                "Single":
                    [{"rate": 0.00495, "bracket": 0.0},
                    {"rate": 0.0099, "bracket": 5200.0},
                    {"rate": 0.01980, "bracket": 10400.0},
                    {"rate": 0.02476, "bracket": 15650.0},
                    {"rate": 0.02969, "bracket": 20900.0},
                    {"rate": 0.03465, "bracket": 41700.0},
                    {"rate": 0.03960, "bracket": 83350.0},
                    {"rate": 0.04597, "bracket": 104250.0},
                    {"rate": 0.04997, "bracket": 208500.0}]
                ,
                "Married Filing Jointly":
                    [{"rate": 0.00495, "bracket": 0.0},
                    {"rate": 0.0099, "bracket": 5200.0},
                    {"rate": 0.01980, "bracket": 10400.0},
                    {"rate": 0.02476, "bracket": 15650.0},
                    {"rate": 0.02969, "bracket": 20900.0},
                    {"rate": 0.03465, "bracket": 41700.0},
                    {"rate": 0.03960, "bracket": 83350.0},
                    {"rate": 0.04597, "bracket": 104250.0},
                    {"rate": 0.04997, "bracket": 208500.0}]
                    ,
                 "standard_deduction": [{"single": 0.0}, {"couple": 0.0}],
                 "personal_exemption": [{"single": 2200.0}, {"couple": 4400.0},{"dependent": 2200.0} ]
                }"""

STATE_OK = """{"state": "OK",
                "Single":
                    [{"rate": 0.005, "bracket": 0.0},
                    {"rate": 0.01, "bracket": 1000.0},
                    {"rate": 0.02, "bracket": 2500.0},
                    {"rate": 0.03, "bracket": 3750.0},
                    {"rate": 0.04, "bracket": 4900.0},
                    {"rate": 0.05, "bracket": 7200.0}]
                ,
                "Married Filing Jointly":
                    [{"rate": 0.005, "bracket": 0.0},
                    {"rate": 0.01, "bracket": 2000.0},
                    {"rate": 0.02, "bracket": 5000.0},
                    {"rate": 0.03, "bracket": 7500.0},
                    {"rate": 0.04, "bracket": 9800.0},
                    {"rate": 0.05, "bracket": 12200.0}]
                ,
                 "standard_deduction": [{"single": 6300.0}, {"couple": 12600.0}],
                 "personal_exemption": [{"single": 1000.0}, {"couple": 2000.0},{"dependent": 1000.0} ]
                }"""

STATE_OR = """{"state": "OR",
                "Single":
                    [{"rate": 0.05, "bracket": 0.0},
                    {"rate": 0.07, "bracket": 3350.0},
                    {"rate": 0.09, "bracket": 8400.0},
                    {"rate": 0.099, "bracket": 125000.0}]
                ,
                "Married Filing Jointly":
                    [{"rate": 0.05, "bracket": 0.0},
                    {"rate": 0.07, "bracket": 6500.0},
                    {"rate": 0.09, "bracket": 16300.0},
                    {"rate": 0.099, "bracket": 250000.0}]
                ,
                 "standard_deduction": [{"single": 2145.0}, {"couple": 4295.0}],
                 "personal_exemption": [{"single": 195.0}, {"couple": 390.0},{"dependent": 195.0} ]
                }"""

STATE_PA = """{"state": "PA",
                "Single":
                    {"rate": 0.0307, "bracket": 0.0}
                ,
                "Married Filing Jointly":
                    {"rate": 0.0307, "bracket": 0.0}
                ,
                 "standard_deduction": [{"single": 0.0}, {"couple": 0.0}],
                 "personal_exemption": [{"single": 0.0}, {"couple": 0.0},{"dependent": 0.0} ]
                }"""

STATE_RI = """{"state": "RI",
                "Single":
                    [{"rate": 0.0375, "bracket": 0.0},
                    {"rate": 0.0475, "bracket": 60850.0},
                    {"rate": 0.0599, "bracket": 138300.0}]
                ,
                "Married Filing Jointly":
                    [{"rate": 0.0375, "bracket": 0.0},
                    {"rate": 0.0475, "bracket": 60850.0},
                    {"rate": 0.0599, "bracket": 138300.0}]
                ,
                 "standard_deduction": [{"single": 8300.0}, {"couple": 16600.0}],
                 "personal_exemption": [{"single": 3900.0}, {"couple": 7800.0},{"dependent": 3900.0} ]
                }"""

STATE_SC = """{"state": "SC",
                "Single":
                    [{"rate": 0.00, "bracket": 0.0},
                    {"rate": 0.03, "bracket": 2920.0},
                    {"rate": 0.04, "bracket": 5840.0},
                    {"rate": 0.05, "bracket": 8760.0},
                    {"rate": 0.06, "bracket": 11680.0},
                    {"rate": 0.07, "bracket": 14600.0}]
                ,
                "Married Filing Jointly":
                    [{"rate": 0.00, "bracket": 0.0},
                    {"rate": 0.03, "bracket": 2920.0},
                    {"rate": 0.04, "bracket": 5840.0},
                    {"rate": 0.05, "bracket": 8760.0},
                    {"rate": 0.06, "bracket": 11680.0},
                    {"rate": 0.07, "bracket": 14600.0}]
                ,
                 "standard_deduction": [{"single": 6300.0}, {"couple": 12600.0}],
                 "personal_exemption": [{"single": 4000.0}, {"couple": 8000.0},{"dependent": 4000.0} ]
                }"""

STATE_SD = """{"state": "SD",
                "Single":
                    {"rate": 0.0, "bracket": 0.0}
                ,
                "Married Filing Jointly":
                    {"rate": 0.0, "bracket": 0.0}
                ,
                 "standard_deduction": [{"single": 0.0}, {"couple": 0.0}],
                 "personal_exemption": [{"single": 0.0}, {"couple": 0.0},{"dependent": 0.0} ]
                }"""

STATE_TN = """{"state": "TN",
                "Single":
                    {"rate": 0.06, "bracket": 0.0}
                ,
                "Married Filing Jointly":
                    {"rate": 0.06, "bracket": 0.0}
                ,
                 "standard_deduction": [{"single": 0.0}, {"couple": 0.0}],
                 "personal_exemption": [{"single": 1250.0}, {"couple": 2500.0},{"dependent": 0.0} ]
                }"""

STATE_TX = """{"state": "TX",
                "Single":
                    {"rate": 0.0, "bracket": 0.0}
                ,
                "Married Filing Jointly":
                    {"rate": 0.0, "bracket": 0.0}
                ,
                 "standard_deduction": [{"single": 0.0}, {"couple": 0.0}],
                 "personal_exemption": [{"single": 0.0}, {"couple": 0.0},{"dependent": 0.0} ]
                }"""

STATE_UT = """{"state": "UT",
                "Single":
                    {"rate": 0.05, "bracket": 0.0}
                ,
                "Married Filing Jointly":
                    {"rate": 0.05, "bracket": 0.0}
                ,
                 "standard_deduction": [{"single": 0.0}, {"couple": 0.0}],
                 "personal_exemption": [{"single": 3000.0}, {"couple": 6000.0},{"dependent": 3000.0} ]
                }"""

STATE_VT = """{"state": "VT",
                "Single":
                    [{"rate": 0.0355, "bracket": 0.0},
                    {"rate": 0.068, "bracket": 39900.0},
                    {"rate": 0.078, "bracket": 93400.0},
                    {"rate": 0.088, "bracket": 192400.0},
                    {"rate": 0.0895, "bracket": 415600.0}]
                ,
                "Married Filing Jointly":
                    [{"rate": 0.0355, "bracket": 0.0},
                    {"rate": 0.068, "bracket": 69900.0},
                    {"rate": 0.078, "bracket": 160450.0},
                    {"rate": 0.088, "bracket": 240000.0},
                    {"rate": 0.0895, "bracket": 421900.0}]
                ,
                 "standard_deduction": [{"single": 6300.0}, {"couple": 12600.0}],
                 "personal_exemption": [{"single": 4050.0}, {"couple": 8100.0},{"dependent": 4050.0} ]
                }"""

STATE_VA = """{"state": "VA",
                "Single":
                    [{"rate": 0.02, "bracket": 0.0},
                    {"rate": 0.03, "bracket": 3000.0},
                    {"rate": 0.05, "bracket": 5000.0},
                    {"rate": 0.0575, "bracket": 17000.0}]
                ,
                "Married Filing Jointly":
                    [{"rate": 0.02, "bracket": 0.0},
                    {"rate": 0.03, "bracket": 3000.0},
                    {"rate": 0.05, "bracket": 5000.0},
                    {"rate": 0.0575, "bracket": 17000.0}]
                ,
                 "standard_deduction": [{"single": 3000.0}, {"couple": 6000.0}],
                 "personal_exemption": [{"single": 930.0}, {"couple": 1860.0},{"dependent": 930.0} ]
                }"""

STATE_WA = """{"state": "WA",
                "Single":
                    {"rate": 0.0, "bracket": 0.0}
                ,
                "Married Filing Jointly":
                    {"rate": 0.0, "bracket": 0.0}
                ,
                 "standard_deduction": [{"single": 0.0}, {"couple": 0.0}],
                 "personal_exemption": [{"single": 0.0}, {"couple": 0.0},{"dependent": 0.0} ]
                }"""

STATE_WV = """{"state": "WV",
                "Single":
                    [{"rate": 0.03, "bracket": 0.0},
                    {"rate": 0.04, "bracket": 10000.0},
                    {"rate": 0.045, "bracket": 25000.0},
                    {"rate": 0.045, "bracket": 40000.0},
                    {"rate": 0.065, "bracket": 60000.0}]
                ,
                "Married Filing Jointly":
                    [{"rate": 0.03, "bracket": 0.0},
                    {"rate": 0.04, "bracket": 10000.0},
                    {"rate": 0.045, "bracket": 25000.0},
                    {"rate": 0.045, "bracket": 40000.0},
                    {"rate": 0.065, "bracket": 60000.0}]
                ,
                 "standard_deduction": [{"single": 0.0}, {"couple": 0.0}],
                 "personal_exemption": [{"single": 2000.0}, {"couple": 4000.0},{"dependent": 2000.0} ]
                }"""

STATE_WI = """{"state": "WI",
                "Single":
                    [{"rate": 0.04, "bracket": 0.0},
                    {"rate": 0.0584, "bracket": 11150.0},
                    {"rate": 0.0627, "bracket": 22230.0},
                    {"rate": 0.0765, "bracket": 244750.0}]
                ,
                "Married Filing Jointly":
                    [{"rate": 0.04, "bracket": 0.0},
                    {"rate": 0.0584, "bracket": 14820.0},
                    {"rate": 0.0627, "bracket": 29640.0},
                    {"rate": 0.0765, "bracket": 326330.0}]
                ,
                 "standard_deduction": [{"single": 10270.0}, {"couple": 19010.0}],
                 "personal_exemption": [{"single": 700.0}, {"couple": 1400.0},{"dependent": 700.0} ]
                }"""

STATE_WY = """{"state": "WY",
                "Single":
                    {"rate": 0.0, "bracket": 0.0}
                ,
                "Married Filing Jointly":
                    {"rate": 0.0, "bracket": 0.0}
                ,
                 "standard_deduction": [{"single": 0.0}, {"couple": 0.0}],
                 "personal_exemption": [{"single": 0.0}, {"couple": 0.0},{"dependent": 0.0} ]
                }"""

STATE_DC = """{"state": "DC",
                "Single":
                    [{"rate": 0.04, "bracket": 0.0},
                    {"rate": 0.06, "bracket": 10000.0},
                    {"rate": 0.065, "bracket": 40000.0},
                    {"rate": 0.085, "bracket": 60000.0},
                    {"rate": 0.0875, "bracket": 350000.0},
                    {"rate": 0.0895, "bracket": 1000000.0}]
                ,
                "Married Filing Jointly":
                    [{"rate": 0.04, "bracket": 0.0},
                    {"rate": 0.06, "bracket": 10000.0},
                    {"rate": 0.065, "bracket": 40000.0},
                    {"rate": 0.085, "bracket": 60000.0},
                    {"rate": 0.0875, "bracket": 350000.0},
                    {"rate": 0.0895, "bracket": 1000000.0}]
                ,
                 "standard_deduction": [{"single": 5200.0}, {"couple": 8350.0}],
                 "personal_exemption": [{"single": 1775.0}, {"couple": 3550.0},{"dependent": 1775.0} ]
                }"""


tax_engine = [  STATE_AL,
                STATE_AK,
                STATE_AZ,
                STATE_AR,
                STATE_CA,
                STATE_CO,
                STATE_CT,
                STATE_DE,
                STATE_FL,
                STATE_GA,
                STATE_HI,
                STATE_ID,
                STATE_IL,
                STATE_IN,
                STATE_IO,
                STATE_KS,
                STATE_KY,
                STATE_LA,
                STATE_ME,
                STATE_MD,
                STATE_MA,
                STATE_MI,
                STATE_MN,
                STATE_MS,
                STATE_MO,
                STATE_MT,
                STATE_NE,
                STATE_NV,
                STATE_NH,
                STATE_NJ,
                STATE_NM,
                STATE_NY,
                STATE_NC,
                STATE_ND,
                STATE_OH,
                STATE_OK,
                STATE_OR,
                STATE_PA,
                STATE_RI,
                STATE_SC,
                STATE_SD,
                STATE_TN,
                STATE_TX,
                STATE_UT,
                STATE_VT,
                STATE_VA,
                STATE_WA,
                STATE_WV,
                STATE_WI,
                STATE_WY,
                STATE_DC]
            

if __name__ == "__main__":

    tst = json.loads(STATE_AL)
    tst = json.loads(STATE_AK)
    tst = json.loads(STATE_AZ)
    tst = json.loads(STATE_AR)
    tst = json.loads(STATE_CA)
    tst = json.loads(STATE_CO)
    tst = json.loads(STATE_CT)
    tst = json.loads(STATE_DE)
    tst = json.loads(STATE_FL)
    tst = json.loads(STATE_GA)
    tst = json.loads(STATE_HI)
    tst = json.loads(STATE_ID)
    tst = json.loads(STATE_IL)
    tst = json.loads(STATE_IN)
    tst = json.loads(STATE_IO)
    tst = json.loads(STATE_KS)
    tst = json.loads(STATE_KY)
    tst = json.loads(STATE_LA)
    tst = json.loads(STATE_ME)
    tst = json.loads(STATE_MD)
    tst = json.loads(STATE_MA)
    tst = json.loads(STATE_MI)
    tst = json.loads(STATE_MN)
    tst = json.loads(STATE_MS)
    tst = json.loads(STATE_MO)
    tst = json.loads(STATE_MT)
    tst = json.loads(STATE_NE)
    tst = json.loads(STATE_NV)
    tst = json.loads(STATE_NH)
    tst = json.loads(STATE_NJ)
    tst = json.loads(STATE_NM)
    tst = json.loads(STATE_NY)
    tst = json.loads(STATE_NC)
    tst = json.loads(STATE_ND)
    tst = json.loads(STATE_OH)
    tst = json.loads(STATE_OK)
    tst = json.loads(STATE_OR)
    tst = json.loads(STATE_PA)
    tst = json.loads(STATE_RI)
    tst = json.loads(STATE_SC)
    tst = json.loads(STATE_SD)
    tst = json.loads(STATE_TN)
    tst = json.loads(STATE_TX)
    tst = json.loads(STATE_UT)
    tst = json.loads(STATE_VT)
    tst = json.loads(STATE_VA)
    tst = json.loads(STATE_WA)
    tst = json.loads(STATE_WV)
    tst = json.loads(STATE_WI)
    tst = json.loads(STATE_WY)
    tst = json.loads(STATE_DC)
