from datetime import datetime
from django.db.models import Max
from .constants import *
from common.utils import Month
from portfolios.models import MarketIndex
from .utils import get_price_from_index
class ChartData:
    def portfolio_performance_config(self):
        config = { 
            "exporting": { "enabled": False },
            "credits": {
                "enabled": False
            },
            "chart": {
                "type": "column"
            },
            "title": {
                "text": ""
            },
            "series": [{
              "name": "OPW Moderato",
              "data": [-1, 14, 18, 5, 6, 5]
          },{
              "name": "Reference Portfolio Benchmark",
              "data": [-4, 2, 3, 4, 5, 6]
          }],
          "xAxis": {
            "categories": ["July 2018", "6 months", "1 year", "3 years", "5 years", "Since inception"]
          },
            "yAxis": {
                "allowDecimals": "False",
                "title": {
                    "text": ""
                },
                "gridLineWidth": 0,
                "tickLength": 5,
                "tickWidth": 1,
                "tickPosition": "outside",
                "labels": {
                    "align": "right",
                    "x":-10
                },
                "lineWidth":1
            },
            "plotOptions": {
                "series": {
                    "borderWidth": 0,
                    "dataLabels": {
                        "enabled": "True",
                        "format": "{point.y:.1f}%"
                    }
                }
            },
            "colors": ["#93979b", "#fda934"]
        }
        return config

    def investment_growth_config(self):
        config = {
            "exporting": { "enabled": False },
            "credits": {
                "enabled": False
            },
            "chart": {
                "type": "spline",
                "scrollablePlotArea": {
                    "scrollPositionX": 1
                }
            },
            "title": {
                "text": ""
            },
            "xAxis": {
                "type": "datetime",
                "labels": {
                    "overflow": "justify"
                }
            },
            "yAxis": {
                "title": "",
                "gridLineWidth": 0,
                "tickLength": 5,
                "tickWidth": 1,
                "tickPosition": "outside",
                "labels": {
                    "align": "right",
                    "x":-10,
                    "y":5
                },
                "lineWidth":1
            },
            "tooltip": {
                "valueSuffix": "m/s",
                "crosshairs": [True]
            },
            "plotOptions": {
                "spline": {
                    "lineWidth": 4,
                    "states": {
                        "hover": {
                            "lineWidth": 5
                        }
                    },
                    "marker": {
                        "enabled": False
                    },
                    "pointInterval": 3600000,
                    "pointStart": 1517529600000
                }
            },
            "colors": ["#93979b", "#fda934"],
            "series": [{
                "data": [
                        3.7, 3.3, 3.9, 5.1, 3.5, 3.8, 4.0, 5.0, 6.1, 3.7, 3.3, 6.4,
                        6.9, 6.0, 6.8, 4.4, 4.0, 3.8, 5.0, 4.9, 9.2, 9.6, 9.5, 6.3,
                        9.5, 10.8, 14.0, 11.5, 10.0, 10.2, 10.3, 9.4, 8.9, 10.6, 10.5, 11.1,
                        10.4, 10.7, 11.3, 10.2, 9.6, 10.2, 11.1, 10.8, 13.0, 12.5, 12.5, 11.3,
                        10.1
                ]
            }, {
                "data": [
                    0.2, 0.1, 0.1, 0.1, 0.3, 0.2, 0.3, 0.1, 0.7, 0.3, 0.2, 0.2,
                    0.3, 0.1, 0.3, 0.4, 0.3, 0.2, 0.3, 0.2, 0.4, 0.0, 0.9, 0.3,
                    0.7, 1.1, 1.8, 1.2, 1.4, 1.2, 0.9, 0.8, 0.9, 0.2, 0.4, 1.2,
                    0.3, 2.3, 1.0, 0.7, 1.0, 0.8, 2.0, 1.2, 1.4, 3.7, 2.1, 2.0,
                    1.5
                ]
            }],
            "navigation": {
                "menuItemStyle": {
                    "fontSize": "10px"
                }
            }
        }
        return config

    def asset_allocation_config(self):
        config = {
          "exporting": { "enabled": False },

          "credits": {
            "enabled": False
          },

          "chart": {
            "height":400,
            "plotBackgroundColor": None,
            "plotBorderWidth": 0,
            "plotShadow": False
          },

          "title": {
            "text": "",
            "align": "center",
            "verticalAlign": "middle"
          },

          "tooltip": {
            "pointFormat": "<b>{point.percentage:.1f}%</b>"
          },

          "plotOptions": {
            "pie": {
              "dataLabels": {
                "distance": -40,
                "style": {
                  "fontWeight": "bold",
                  "color": "white"
                },
                "format": "{y} %"
              },
              "size":300,
              "startAngle": 0,
              "endAngle": 360,
              "center": ["50%", "50%"],
              "showInLegend": True
            }
          },

          "series": [{
            "type": "pie",
            "innerSize": "50%",
            "data": [
              ["Traditional Equity", 7.5],
              ["Non-traditional Equity", 17.5],
              ["Investment grade bonds", 10.5],
              ["Non-traditional fixed income", 17.5],
              ["Alternatives", 10.5],
              ["Cash", 5.5]
            ]
          }]
        }
        return config

    def portfolio_tilts(self):
        config = {
          "exporting": { "enabled": False },

          "chart": {
            "type": "column"
          },

          "title": {
            "text": ""
          },

          "subtitle": {
            "text": ""
          },

          "xAxis": {
            "type": "category",
            "labels": {
              "rotation": 90
            }
          },

          "yAxis": {
            "title": {
              "text": ""
            },
            "gridLineWidth": 0,
            "tickLength": 5,
            "tickWidth": 1,
            "tickPosition": "outside",
            "labels": {
                "align": "right",
                "x":-10,
                "y":5
            },
            "lineWidth":1,
            "plotBands": [{ 
            "from": 70,
            "to": 80,
            "label": {
                "text": "Overweight",
                "style": {
                    "color": "#606060"
                }            
            }
        },{ 
            "from": -20,
            "to": -10,
            "label": {
                "text": "Underweight",
                "style": {
                    "color": "#606060"
                }            
            }
        }]
          },

          "legend": {
            "enabled": False
          },

          "credits": {
            "enabled": False
          },

          "plotOptions": {
            "series": {
              "borderWidth": 0,
              "color": "#93979b"
            }
          },

          "tooltip": {
            "headerFormat": "<span style=font-size:11px>{series.name}</span><br>",
            "pointFormat": "<span style=color:{point.color}>{point.name}</span>: <b>{point.y:.2f}%</b> of total<br/>"
          },

          "series": [
            {
              "name": "Browsers",
              "data": [
                {
                  "name": "Traditional Equity",
                  "y": 62.74
                },
                {
                  "name": "Non-traditional Equity",
                  "y": -10.57
                },
                {
                  "name": "Investment grade bonds",
                  "y": 7.23
                },
                {
                  "name": "Non-traditional fixed income",
                  "y": 5.58
                },
                {
                  "name": "Alternatives",
                  "y": 4.02
                },
                {
                  "name": "Cash",
                  "y": 1.92
                }
              ]
            }
          ]
        }
        return config

    def portfolio_weight_risk(self):
        config = {
          "legend": {
            "verticalAlign": "top"
          },

          "exporting": { "enabled": False },

          "credits": {
            "enabled": False
          },

          "chart": {
            "type": "column"
          },

          "title": {
            "text": ""
          },
          "series": [{
              "name": "Portfolio weight",
              "data": [-1, 14, 18, 5, 6, 5]
          },{
              "name": "Risk contribution",
              "data": [-4, 2, 3, 4, 5, 6]
          }],
          "xAxis": {
            "categories": ["Traditional Equity", 
                                        "Non-traditional Equity", 
                                        "Investment grade bonds", 
                                        "Non-traditional fixed income", 
                                        "Alternatives",
                                        "Cash"],
            "labels": {
              "rotation": -90
            }
          },
          "yAxis": {
            "allowDecimals": False,
            "title": {
              "text": ""
            },
            "gridLineWidth": 0,
            "tickLength": 5,
            "tickWidth": 1,
            "tickPosition": "outside",
            "labels": {
              "align": "right",
              "x":-10
            },
            "lineWidth":1
          },

          "colors": ["#93979b", "#fda934"]
        }
        return config

    def portfolio_weight_return(self):
        config = {
          "legend": {
            "verticalAlign": "top"
          },

          "exporting": { "enabled": False },

          "credits": {
            "enabled": False
          },

          "chart": {
            "type": "column"
          },

          "title": {
            "text": ""
          },
          "series": [{
              "name": "Portfolio weight",
              "data": [-1, 14, 18, 5, 6, 5]
          },{
              "name": "Risk contribution",
              "data": [-4, 2, 3, 4, 5, 6]
          }],
          "xAxis": {
            "categories": ["Traditional Equity", 
                                        "Non-traditional Equity", 
                                        "Investment grade bonds", 
                                        "Non-traditional fixed income", 
                                        "Alternatives",
                                        "Cash"],
            "labels": {
              "rotation": -90
            }
          },
          "yAxis": {
            "allowDecimals": False,
            "title": {
              "text": ""
            },
            "gridLineWidth": 0,
            "tickLength": 5,
            "tickWidth": 1,
            "tickPosition": "outside",
            "labels": {
              "align": "right",
              "x":-10
            },
            "lineWidth":1
          },

          "colors": ["#93979b", "#fda934"]
        }
        return config

    def geographic_exposure(self):
        config = {
          "legend": {
            "verticalAlign": "top"
          },

          "exporting": { "enabled": False },

          "credits": {
            "enabled": False
          },

          "chart": {
            "type": "column"
          },

          "title": {
            "text": ""
          },

          "series": [{
              "name": "Portfolio",
              "data": [4, 14, 18, 5, 6, 5, 14, 15, 18]
          },{
              "name": "Benchmark",
              "data": [1,2,3,4,5,6,7,8,9]
          }],

          "xAxis": {
            "categories": [{
                "name": "Americas",
                "categories": ["Nth America", "Last Am"]
            }, {
                "name": "Greater Europe",
                "categories": ["UK", "Europe", "EM Europe", "Africa/Middle<br> East"]
            }, {
                "name": "Greater Asia",
                "categories": ["Australia", "Asia", "Japan"]
            }],
            "labels": {
              "rotation": 0
            }
          },

          "yAxis": {
            "allowDecimals": False,
            "title": {
              "text": ""
            },
            "gridLineWidth": 0,
            "tickLength": 5,
            "tickWidth": 1,
            "tickPosition": "outside",
            "labels": {
              "align": "right",
              "x":-10
            },
            "lineWidth":1
          },

          "colors": ["#93979b", "#fda934"]
        }
        return config

    def gics_sector(self):
        config = {
          "legend": {
            "verticalAlign": "top"
          },

          "exporting": { "enabled": False },

          "credits": {
            "enabled": False
          },

          "chart": {
            "type": "column"
          },

          "title": {
            "text": ""
          },

          "series": [{
              "name": "Portfolio",
              "data": [4, 14, 18, 5, 6, 5, 14, 15, 18, 5]
          },{
              "name": "Benchmark",
              "data": [1,2,3,4,5,6,7,8,9,10]
          }],

          "xAxis": {
            "categories": ["Comcrtable bilogy", "Comcrtable", "Energy", "Financials", "Indonesia", "Iiko bich", "Hero bich", "Musume", "Teldom", "Ulente"],
            "labels": {
              "rotation": 90
            }
          },

          "yAxis": {
            "allowDecimals": False,
            "title": {
              "text": ""
            },
            "gridLineWidth": 0,
            "tickLength": 5,
            "tickWidth": 1,
            "tickPosition": "outside",
            "labels": {
              "align": "right",
              "x":-10
            },
            "lineWidth":1
          },

          "colors": ["#93979b", "#fda934"]
        }
        return config

    def get_data_from_index(self, index):
        daily_prices_array = MarketIndex.objects.get(data_api_param__iexact=index) \
                                                .daily_prices \
                                                .all() \
                                                .annotate(last_date=Max('date'), month=Month('date')) \
                                                .values('price', 'last_date') \
                                                .order_by('last_date') \

        daily_prices_data = []
        for daily_price in daily_prices_array:
            daily_prices_data.append([int(daily_price['last_date'].strftime("%s")) * 1000, daily_price['price']])
        return daily_prices_data
        
    def get_us_economic_chart1(self):
        return self.get_economic_chart_config([
            {
                "name": "GDP (yoy%, lhs)",
                "index": GDP_API_PARAM_INDEX
            },
            {
                "name": "GS Current Activity Indicator(rhs)",
                "index": GSUSCAI_API_PARAM_INDEX
            }
        ])

    def get_us_economic_chart2(self):
        return self.get_economic_chart_config([
            {
                "name": "Headline CPI inflation(%yoy, lhs)",
                "index": CPI_YOY_INDEX
            },
            {
                "name": "US Fed Policy rate(%, rhs)",
                "index": FDTR_INDEX
            }
        ])

    def get_eu_economic_chart1(self):
        return self.get_economic_chart_config([
            {
                "name": "GDP (yoy%, lhs)",
                "index": EUGNEMUY_INDEX
            },
            {
                "name": "GS Current Activity Indicator(rhs)",
                "index": GSEACAI_INDEX
            }
        ])

    def get_eu_economic_chart2(self):
        return self.get_economic_chart_config([
            {
                "name": "Headline CPI inflation(%yoy, lhs)",
                "index": ECCPEUY_INDEX
            },
            {
                "name": "US Fed Policy rate(%, rhs)",
                "index": EUORDEPO_INDEX
            }
        ])

    def get_jp_economic_chart1(self):
        return self.get_economic_chart_config([
            {
                "name": "GDP (yoy%, lhs)",
                "index": JGDPNSAQ_INDEX
            },
            {
                "name": "GS Current Activity Indicator(rhs)",
                "index": GSJPCAI_INDEX
            }
        ])

    def get_jp_economic_chart2(self):
        return self.get_economic_chart_config([
            {
                "name": "Headline CPI inflation(%yoy, lhs)",
                "index": JNCPIYOY_INDEX
            },
            {
                "name": "US Fed Policy rate(%, rhs)",
                "index": BOJDPBAL_INDEX
            }
        ])

    def get_au_economic_chart1(self):
        return self.get_economic_chart_config([
            {
                "name": "GDP (yoy%, lhs)",
                "index": AUNAGDPY_INDEX
            },
            {
                "name": "GS Current Activity Indicator(rhs)",
                "index": GSAUCAI_INDEX
            }
        ])

    def get_au_economic_chart2(self):
        return self.get_economic_chart_config([
            {
                "name": "Headline CPI inflation(%yoy, lhs)",
                "index": AUCPIYOY_INDEX
            },
            {
                "name": "US Fed Policy rate(%, rhs)",
                "index": RBACTRD_INDEX
            }
        ])

    def get_cn_economic_chart1(self):
        return self.get_economic_chart_config([
            {
                "name": "GDP (yoy%, lhs)",
                "index": CNGDPYOY_INDEX
            },
            {
                "name": "GS Current Activity Indicator(rhs)",
                "index": GSCNCAI_INDEX
            }
        ])

    def get_cn_economic_chart2(self):
        return self.get_economic_chart_config([
            {
                "name": "Headline CPI inflation(%yoy, lhs)",
                "index": CNCPIYOY_INDEX
            },
            {
                "name": "US Fed Policy rate(%, rhs)",
                "index": CHBM7D_INDEX
            }
        ])

    def get_hk_economic_chart1(self):
        return self.get_economic_chart_config([
            {
                "name": "GDP (yoy%, lhs)",
                "index": HKGDYOY_INDEX
            },
            {
                "name": "GS Current Activity Indicator(rhs)",
                "index": GSHKCAI_INDEX
            }
        ])

    def get_hk_economic_chart2(self):
        return self.get_economic_chart_config([
            {
                "name": "Headline CPI inflation(%yoy, lhs)",
                "index": HKCPIY_INDEX
            },
            {
                "name": "US Fed Policy rate(%, rhs)",
                "index": HKBASE_INDEX
            }
        ])

    def get_economic_chart_config(self, options):
        series = [{
            "name": option['name'],
            "data": self.get_data_from_index(option['index'])
        } for option in options]

        config = {
            "legend": {
                "verticalAlign": "top",
                "align": "right"
            },

            "exporting": { "enabled": False },

            "credits": {
                "enabled": False
            },

            "chart": {
                "type": "line",
                "scrollablePlotArea": {
                  "scrollPositionX": 1
                }
            },

            "title": {
                "text": ""
            },

            "xAxis": {
                "type": "datetime",
                "labels": {
                  "overflow": "justify"
                }
            },

            "yAxis": {
                "title": "",
                "gridLineWidth": 0,
                "tickLength": 5,
                "tickWidth": 1,
                "tickPosition": "outside",
                "labels": {
                  "align": "right",
                  "x":-10,
                  "y":5
                },
                "lineWidth":1
            },

            "tooltip": {
                "crosshairs": [True]
            },

            "plotOptions": {
                "line": {
                    "lineWidth": 1,
                    "states": {
                        "hover": {
                            "lineWidth": 1
                        }
                    },
                    "marker": {
                        "enabled": False
                    }
                }
            },

            "colors": ["#93979b", "#fda934"],

            "series": series,
            "navigation": {
                "menuItemStyle": {
                    "fontSize": "10px"
                }
            },
            "navigation": {
                "menuItemStyle": {
                  "fontSize": "10px"
                }
            }
        }
        return config

    def equities(self):
        indices = [AS51_INDEX, SPX_INDEX, NKY_INDEX, HSI_INDEX, SHSZ300_INDEX, UKX_INDEX, DAX_INDEX]
        categories = [
            SPASX_200 + "<br>" + AUSTRALIA,
            SP500 +"<br>" + US,
            NIKKEI225 + "<br>" + JAPAN,
            HANG_SENG + "<br>" + HONGKONG,
            CSI300 + "<br>" + CHINA,
            FTSE100 + "<br>" + UK,
            DAX_30 + "<br>" + GERMANY
        ]

        return self.get_market_chart_config(options=[
            {
                "name": "1 month",
                "daydelta": 30
            },
            {
                "name": "Year to Date",
                "daydelta": 180
            },
            {
                "name": "12 months",
                "daydelta": 365
            }
        ], indices=indices, categories=categories, chart_index=1)


    def get_market_data_from_index(self, indices=[], daydelta=0, chart_index=1):
        values = []
        for index in indices:
            latest_price = get_price_from_index(index, 0)
            last_month_price = get_price_from_index(index, daydelta)
            
            if latest_price and last_month_price:
                if chart_index == 1:
                    values.append(round(latest_price / last_month_price - 1, 2))
                else:
                    values.append(round(latest_price - last_month_price/100, 2))
            else:
                values.append(0)

        return values
            

    def get_market_chart_config(self, options=[], indices=[], categories=[], chart_index=1):
        series = [{
            "name": option['name'],
            "data": self.get_market_data_from_index(indices=indices, daydelta=option['daydelta'], chart_index=chart_index)
        } for option in options]

        config = {
            "legend": {
                "verticalAlign": "bottom",
                "align": "left"
            },

            "exporting": { "enabled": False },

            "credits": {
                "enabled": False
            },

            "title": {
                "text": ""
            },

            "chart": {
                "type": "column"
            },

            "series": series,

            "yAxis": {
                "title": "",
                "gridLineWidth": 0,
                "tickLength": 5,
                "tickWidth": 1,
                "tickPosition": "outside",
                "labels": {
                    "align": "right",
                    "x":-10
                },
                "lineWidth":1
            },

            "colors": ["#93979b", "#fda934", "#ff0000"],

            "plotOptions": {
                "series": {
                    "borderWidth": 0,
                    "dataLabels": {
                        "enabled": True,
                        "format": "{point.y:.1f}%"
                    }
                }
            },

            "xAxis": {
                "categories": categories
            }
        }
        return config

    def fx(self):
        indices = [AUD_CURNCY, AUDGBP_CURNCY, AUDEUR_CURNCY, AUDJPY_CURNCY, AUD_TWI_INDEX]
        categories = [
            AUD_USD + "<br>" + US_DOLLAR,
            AUD_GBP +"<br>" + BRITISH_POUND,
            AUD_EUR + "<br>" + EURO,
            AUD_YEN + "<br>" + JAPANESE_YEN,
            AUD_TWI + "<br>" + AUD_TRADE_WEIGHTED_INDEX
        ]

        return self.get_market_chart_config(options=[
            {
                "name": "1 month",
                "daydelta": 30
            },
            {
                "name": "Year to Date",
                "daydelta": 180
            },
            {
                "name": "12 months",
                "daydelta": 365
            }
        ], indices=indices, categories=categories, chart_index=1)

    def fixed_income(self):
        indices = [FFA_COMDTY, USGG2YR_INDEX, USGG10YR_INDEX, RBACTRD_INDEX,\
            GACGB3_INDEX, GACGB10_INDEX, JGAGHYSP_INDEX, JGAGCTP1_INDEX]

        categories = [
            {
                "name": "United States",
                "categories": [FED_FUNDS_RATE, US_2_YEAR, US_10_YEAR]
            }, {
                "name": "Australia",
                "categories": [RBA_CASH, AUD_3_YEAR, AUD_10_YEAR]
            }, {
                "name": "Credit Spreads",
                "categories": [JP_IG, JP_HY]
            }
        ]

        return self.get_market_chart_config(options=[
            {
                "name": "1 month",
                "daydelta": 30
            },
            {
                "name": "Year to Date",
                "daydelta": 180
            },
            {
                "name": "12 months",
                "daydelta": 365
            }
        ], indices=indices, categories=categories, chart_index=2)

    def asset_contributions_returns(self):
        config = {
          "exporting": { "enabled": False },

          "credits": {
            "enabled": False
          },

          "title": {
            "text": ""
          },

          "xAxis": {
            "categories": ["Mar-17", "Jan-17", "Sep-17", "Dec-17", "Mar-18"]
          },

          "yAxis": {
            "title": {
              "text": ""
            },
            "stackLa1bels": {
              "enab1led": True,
              "style": {
                "fontWeight": "bold",
                "color": "gray"
              }
            },
            "gridLineWidth": 0,
            "tickLength": 5,
            "tickWidth": 1,
            "tickPosition": "outside",
            "labels": {
              "align": "right",
              "x":-10
            },
            "lineWidth":1
          },

          "legend": {
            "align": "right",
            "x": -30,
            "verticalAlign": "top",
            "y": 25,
            "floating": True,
            "backgroundColor": "white",
            "borderColor": "#CCC",
            "borderWidth": 1,
            "shadow": False
          },

          "tooltip": {
            "headerFormat": "<b>{point.x}</b><br/>",
            "pointFormat": "{series.name}: {point.y}<br/>Total: {point.stackTotal}"
          },

          "plotOptions": {
            "column": {
              "stacking": "normal",
              "dataLabels": {
                "color": "white"
              }
            }
          },

          "series": [{
            "name": "Traditional Equity",
            "type": "column",
            "data": [5, -3, 4, 7, 2]
          }, {
            "name": "Non-traditional Equity",
            "type": "column",
            "data": [2, 2, -3, 2, -1]
          }, {
            "name": "Investment grade bonds",
            "type": "column",
            "data": [-3, 4, 4, 2, 5]
          }, {
            "name": "Non-traditional fixed income",
            "type": "column",
            "data": [3, -1, 2, 2, -4]
          }, {
            "name": "Alternatives",
            "type": "column",
            "data": [4, -2, -6, -3, 2]
          }, {
            "name": "Cash",
            "type": "column",
            "data": [4, -2, -6, -3, 2]
          }, {
            "name": "Transfers",
            "data": [3, 2.67, 3, 6.33, 3.33],
            "marker": {
              "lineWidth": 2,
              "lineColor": "blue",
              "fillColor": "white"
            }
          }]
        }
        return config

    def asset_contributions_volatility(self):
        config = {
          "exporting": { "enabled": False },

          "credits": {
            "enabled": False
          },

          "title": {
            "text": ""
          },

          "xAxis": {
            "categories": ["Mar-17", "Jan-17", "Sep-17", "Dec-17", "Mar-18"]
          },

          "yAxis": {
            "title": {
              "text": ""
            },
            "stackLa1bels": {
              "enab1led": True,
              "style": {
                "fontWeight": "bold",
                "color": "gray"
              }
            },
            "gridLineWidth": 0,
            "tickLength": 5,
            "tickWidth": 1,
            "tickPosition": "outside",
            "labels": {
              "align": "right",
              "x":-10
            },
            "lineWidth":1
          },

          "legend": {
            "align": "right",
            "x": -30,
            "verticalAlign": "top",
            "y": 25,
            "floating": True,
            "backgroundColor": "white",
            "borderColor": "#CCC",
            "borderWidth": 1,
            "shadow": False
          },

          "tooltip": {
            "headerFormat": "<b>{point.x}</b><br/>",
            "pointFormat": "{series.name}: {point.y}<br/>Total: {point.stackTotal}"
          },

          "plotOptions": {
            "column": {
              "stacking": "normal",
              "dataLabels": {
                "color": "white"
              }
            }
          },

          "series": [{
            "name": "Traditional Equity",
            "type": "column",
            "data": [5, -3, 4, 7, 2]
          }, {
            "name": "Non-traditional Equity",
            "type": "column",
            "data": [2, 2, -3, 2, -1]
          }, {
            "name": "Investment grade bonds",
            "type": "column",
            "data": [-3, 4, 4, 2, 5]
          }, {
            "name": "Non-traditional fixed income",
            "type": "column",
            "data": [3, -1, 2, 2, -4]
          }, {
            "name": "Alternatives",
            "type": "column",
            "data": [4, -2, -6, -3, 2]
          }, {
            "name": "Cash",
            "type": "column",
            "data": [4, -2, -6, -3, 2]
          }, {
            "name": "Transfers",
            "data": [3, 2.67, 3, 6.33, 3.33],
            "marker": {
              "lineWidth": 2,
              "lineColor": "blue",
              "fillColor": "white"
            }
          }]
        }
        return config

    def portfolio_weight_risk1(self):
        config = {
          "legend": {
            "verticalAlign": "top"
          },

          "exporting": { "enabled": False },

          "credits": {
            "enabled": False
          },

          "title": {
            "text": ""
          },

          "chart": {
            "type": "column"
          },

          "series": [{
              "name": "Portfolio",
              "data": [4, 14, 18, 5, 6, 5]
          },{
              "name": "Benchmark",
              "data": [1, 2, 3, 4, 5, 6]
          }],

          "xAxis": {
            "categories": ["Traditional Equity", "Non-traditional Equity", "Investment grade bonds", "Non-traditional fixed income", "Alternatives", "Cash"],
            "labels": {
              "rotation": -90
            }
          },

          "yAxis": {
            "allowDecimals": False,
            "title": "",
            "gridLineWidth": 0,
            "tickLength": 5,
            "tickWidth": 1,
            "tickPosition": "outside",
            "labels": {
              "align": "right",
              "x":-10
            },
            "lineWidth":1
          },
          "colors": ["#93979b", "#fda934"]
        }
        return config

    def portfolio_weight_contributions(self):
        config = {
          "legend": {
            "verticalAlign": "top"
          },

          "exporting": { "enabled": False },

          "credits": {
            "enabled": False
          },

          "title": {
            "text": ""
          },

          "chart": {
            "type": "column"
          },

          "series": [{
              "name": "Portfolio",
              "data": [4, 14, 18, 5, 6, 5, 14, 15, 18]
          },{
              "name": "Benchmark",
              "data": [1,2,3,4,5,6,7,8,9]
          }],

          "xAxis": {
            "categories": ["1", "2", "3", "4", "5", "6", "7", "8", "9"],
            "labels": {
              "rotation": -90
            }
          },

          "yAxis": {
            "allowDecimals": False,
            "title": "",
            "gridLineWidth": 0,
            "tickLength": 5,
            "tickWidth": 1,
            "tickPosition": "outside",
            "labels": {
              "align": "right",
              "x":-10
            },
            "lineWidth":1
          },

          "colors": ["#93979b", "#fda934"]
        }

        return config

    def fund_performance(self):
        config = {
          "exporting": { "enabled": False },
          
          "title": {
            "text": ""
          },

          "xAxis": {
            "categories": ["Mar-17", "Jan-17", "Sep-17", "Dec-17", "Mar-18"]
          },

          "yAxis": {
            "title": "",
            "stackLa1bels": {
              "enab1led": True,
              "style": {
                "fontWeight": "bold",
                "color": "gray"
              }
            },
            "gridLineWidth": 0,
            "tickLength": 5,
            "tickWidth": 1,
            "tickPosition": "outside",
            "labels": {
              "align": "right",
              "x":-10
            },
            "lineWidth":1
          },

          "legend": {
            "align": "right",
            "x": -30,
            "verticalAlign": "top",
            "y": 25,
            "floating": True,
            "backgroundColor": "white",
            "borderColor": "#CCC",
            "borderWidth": 1,
            "shadow": False
          },

          "tooltip": {
            "headerFormat": "<b>{point.x}</b><br/>",
            "pointFormat": "{series.name}: {point.y}<br/>Total: {point.stackTotal}"
          },

          "plotOptions": {
            "column": {
              "stacking": "normal",
              "dataLabels": {
                "color": "white"
              }
            }
          },

          "series": [{
            "name": "Traditional Equity",
            "type": "column",
            "data": [5, -3, 4, 7, 2]
          }, {
            "name": "Non-traditional Equity",
            "type": "column",
            "data": [2, 2, -3, 2, -1]
          }, {
            "name": "Investment grade bonds",
            "type": "column",
            "data": [-3, 4, 4, 2, 5]
          }, {
            "name": "Non-traditional fixed income",
            "type": "column",
            "data": [3, -1, 2, 2, -4]
          }, {
            "name": "Alternatives",
            "type": "column",
            "data": [4, -2, -6, -3, 2]
          }, {
            "name": "Cash",
            "type": "column",
            "data": [4, -2, -6, -3, 2]
          }]
        }
        return config

    def fund_risk(self):
        config = {
            "legend": {
            "verticalAlign": "bottom",
            "align": "left"
          },

          "exporting": { "enabled": False },

          "credits": {
            "enabled": False
          },

          "title": {
            "text": ""
          },

          "chart": {
            "type": "spline",
            "scrollablePlotArea": {
              "scrollPositionX": 1
            }
          },

          "xAxis": {
            "type": "datetime",
            "labels": {
              "overflow": "justify"
            }
          },

          "yAxis": {
            "title": "",
            "gridLineWidth": 0,
            "tickLength": 5,
            "tickWidth": 1,
            "tickPosition": "outside",
            "labels": {
              "align": "right",
              "x":-10,
              "y":5
            },
            "lineWidth":1
          },

          "tooltip": {
            "valueSuffix": "m/s",
            "crosshairs": [True]
          },

          "plotOptions": {
            "spline": {
              "lineWidth": 1,
              "states": {
                "hover": {
                  "lineWidth": 1
                }
              },
              "marker": {
                "enabled": False
              },
              "pointInterval": 3600000,
              "pointStart": 1517529600000
            }
          },
          "colors": ["#93979b", "#fda934"],
          "series": [{
              "data": [
                3.7, 3.3, 3.9, 5.1, 3.5, 3.8, 4.0, 5.0, 6.1, 3.7, 3.3, 6.4,
                6.9, 6.0, 6.8, 4.4, 4.0, 3.8, 5.0, 4.9, 9.2, 9.6, 9.5, 6.3,
                9.5, 10.8, 14.0, 11.5, 10.0, 10.2, 10.3, 9.4, 8.9, 10.6, 10.5, 11.1,
                10.4, 10.7, 11.3, 10.2, 9.6, 10.2, 11.1, 10.8, 13.0, 12.5, 12.5, 11.3,
                10.1, 3.7, 3.3, 3.9, 5.1, 3.5, 3.8, 4.0, 5.0, 6.1, 3.7, 3.3, 6.4,
                6.9, 6.0, 6.8, 4.4, 4.0, 3.8, 5.0, 4.9, 9.2, 9.6, 9.5, 6.3,
                9.5, 10.8, 14.0, 11.5, 10.0, 10.2, 10.3, 9.4, 8.9, 10.6, 10.5, 11.1,
                10.4, 10.7, 11.3, 10.2, 9.6, 10.2, 11.1, 10.8, 13.0, 12.5, 12.5, 11.3,
                10.1
              ]
            }, {
              "data": [
                  0.2, 0.1, 0.1, 0.1, 0.3, 0.2, 0.3, 0.1, 0.7, 0.3, 0.2, 0.2,
                  0.3, 0.1, 0.3, 0.4, 0.3, 0.2, 0.3, 0.2, 0.4, 0.0, 0.9, 0.3,
                  0.7, 1.1, 1.8, 1.2, 1.4, 1.2, 0.9, 0.8, 0.9, 0.2, 0.4, 1.2,
                  0.3, 2.3, 1.0, 0.7, 1.0, 0.8, 2.0, 1.2, 1.4, 3.7, 2.1, 2.0,
                  1.5, 0.2, 0.1, 0.1, 0.1, 0.3, 0.2, 0.3, 0.1, 0.7, 0.3, 0.2, 0.2,
                  0.3, 0.1, 0.3, 0.4, 0.3, 0.2, 0.3, 0.2, 0.4, 0.0, 0.9, 0.3,
                  0.7, 1.1, 1.8, 1.2, 1.4, 1.2, 0.9, 0.8, 0.9, 0.2, 0.4, 1.2,
                  0.3, 2.3, 1.0, 0.7, 1.0, 0.8, 2.0, 1.2, 1.4, 3.7, 2.1, 2.0,
                  1.5
              ]
          }],
          "navigation": {
            "menuItemStyle": {
              "fontSize": "10px"
            }
          }
        }
        return config

    def asset_allocation1(self):
        config = {
          "exporting": { "enabled": False },

          "credits": {
            "enabled": False
          },

          "chart": {
            "type": "area"
          },

          "title": {
            "text": ""
          },

          "subtitle": {
            "text": ""
          },

          "xAxis": {
            "type": "datetime"
          },

          "yAxis": {
            "title": {
              "text": ""
            }
          },

          "tooltip": {
            "pointFormat": "<span style=color:{series.color}>{series.name}</span>: <b>{point.percentage:.1f}%</b> ({point.y:,.0f} millions)<br/>",
            "split": True
          },

          "plotOptions": {
            "area": {
              "stacking": "percent",
              "lineColor": "#ffffff",
              "lineWidth": 0,
              "marker": {
                "enabled": False,
                "lineWidth": 1,
                "lineColor": "#ffffff"
              },
              "pointInterval": 3600000,
              "pointStart": 1517529600000
            }
          },

          "series": [{
            "name": "Traditional Equity",
            "data": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 5268, 5268]
          },{
            "name": "Non-traditional Equity",
            "data": [502, 635, 809, 947, 1402, 3634, 5268,502, 635, 809, 947, 1402, 3634, 5268]
          }, {
            "name": "Investment grade bonds",
            "data": [106, 107, 111, 133, 221, 767, 1766, 106, 107, 111, 133, 221, 767, 1766]
          }, {
            "name": "Non-traditional fixed income",
            "data": [163, 203, 276, 408, 547, 729, 628, 163, 203, 276, 408, 547, 729, 628]
          }, {
            "name": "Alternatives",
            "data": [18, 31, 54, 156, 339, 818, 1201, 18, 31, 54, 156, 339, 818, 1201]
          }, {
            "name": "Cash",
            "data": [2, 2, 2, 6, 13, 30, 46, 2, 2, 2, 6, 13, 30, 46]
          }]
        }
        return config

    def daa_change(self):
        config = {
            "legend": {
            "verticalAlign": "bottom",
            "align": "left"
          },

          "exporting": { "enabled": False },

          "credits": {
            "enabled": False
          },

          "chart": {
            "type": "spline",
            "scrollablePlotArea": {
              "scrollPositionX": 1
            }
          },

          "title": {
            "text": ""
          },

          "xAxis": {
            "type": "datetime",
            "labels": {
              "overflow": "justify"
            }
          },

          "yAxis": {
            "title": "",
            "gridLineWidth": 0,
            "tickLength": 5,
            "tickWidth": 1,
            "tickPosition": "outside",
            "labels": {
              "align": "right",
              "x":-10,
              "y":5
            },
            "lineWidth":1
          },

          "tooltip": {
            "valueSuffix": "m/s",
            "crosshairs": [True]
          },

          "plotOptions": {
            "spline": {
              "lineWidth": 1,
              "states": {
                "hover": {
                  "lineWidth": 1
                }
              },
              "marker": {
                "enabled": False
              },
              "pointInterval": 3600000,
              "pointStart": 1517529600000
            }
          },

          "colors": ["#93979b", "#fda934"],

          "series": [{
              "data": [
                3.7, 3.3, 3.9, 5.1, 3.5, 3.8, 4.0, 5.0, 6.1, 3.7, 3.3, 6.4,
                6.9, 6.0, 6.8, 4.4, 4.0, 3.8, 5.0, 4.9, 9.2, 9.6, 9.5, 6.3,
                9.5, 10.8, 14.0, 11.5, 10.0, 10.2, 10.3, 9.4, 8.9, 10.6, 10.5, 11.1,
                10.4, 10.7, 11.3, 10.2, 9.6, 10.2, 11.1, 10.8, 13.0, 12.5, 12.5, 11.3,
                10.1, 3.7, 3.3, 3.9, 5.1, 3.5, 3.8, 4.0, 5.0, 6.1, 3.7, 3.3, 6.4,
                6.9, 6.0, 6.8, 4.4, 4.0, 3.8, 5.0, 4.9, 9.2, 9.6, 9.5, 6.3,
                9.5, 10.8, 14.0, 11.5, 10.0, 10.2, 10.3, 9.4, 8.9, 10.6, 10.5, 11.1,
                10.4, 10.7, 11.3, 10.2, 9.6, 10.2, 11.1, 10.8, 13.0, 12.5, 12.5, 11.3,
                10.1
              ]
            }, {
              "data": [
                  0.2, 0.1, 0.1, 0.1, 0.3, 0.2, 0.3, 0.1, 0.7, 0.3, 0.2, 0.2,
                  0.3, 0.1, 0.3, 0.4, 0.3, 0.2, 0.3, 0.2, 0.4, 0.0, 0.9, 0.3,
                  0.7, 1.1, 1.8, 1.2, 1.4, 1.2, 0.9, 0.8, 0.9, 0.2, 0.4, 1.2,
                  0.3, 2.3, 1.0, 0.7, 1.0, 0.8, 2.0, 1.2, 1.4, 3.7, 2.1, 2.0,
                  1.5, 0.2, 0.1, 0.1, 0.1, 0.3, 0.2, 0.3, 0.1, 0.7, 0.3, 0.2, 0.2,
                  0.3, 0.1, 0.3, 0.4, 0.3, 0.2, 0.3, 0.2, 0.4, 0.0, 0.9, 0.3,
                  0.7, 1.1, 1.8, 1.2, 1.4, 1.2, 0.9, 0.8, 0.9, 0.2, 0.4, 1.2,
                  0.3, 2.3, 1.0, 0.7, 1.0, 0.8, 2.0, 1.2, 1.4, 3.7, 2.1, 2.0,
                  1.5
              ]
          }],
          "navigation": {
            "menuItemStyle": {
              "fontSize": "10px"
            }
          }
        }
        return config

    def daa_change1(self):
        config = {
          "legend": {
            "verticalAlign": "top"
          },

          "exporting": { "enabled": False },

          "credits": {
            "enabled": False
          },

          "chart": {
            "type": "column"
          },

          "title": {
            "text": ""
          },

          "series": [{
              "name": "Portfolio",
              "data": [4, 14, 18, 5, 6, 5, 14, 15, 18]
          },{
              "name": "Benchmark",
              "data": [1,2,3,4,5,6,7,8,9]
          }],

          "xAxis": {
            "categories": ["Aug 17", "Sep", "Oct", "Nov", "Dec", "Jan 18", "Feb", "Mar", "Apr"],
            "gridLineWidth": 1,
            "gridLineDashStyle" : "dot"
          },

          "yAxis": {
            "allowDecimals": False,
            "title": "",
            "gridLineWidth": 1,
            "tickLength": 5,
            "tickWidth": 1,
            "tickPosition": "outside",
            "labels": {
              "align": "right",
              "x":-10
            },
            "lineWidth":1
          },
          "colors": ["#93979b", "#fda934"]
        }
        return config

    def daa_change2(self):
        config = {
          "legend": {
            "verticalAlign": "top"
          },

          "exporting": { "enabled": False },

          "credits": {
            "enabled": False
          },

          "chart": {
            "type": "column"
          },

          "title": {
            "text": ""
          },

          "series": [{
              "name": "Portfolio",
              "data": [4, 14, 18, 5, 6, 5, 14, 15, 18]
          },{
              "name": "Benchmark",
              "data": [1,2,3,4,5,6,7,8,9]
          }],

          "xAxis": {
            "categories": ["Aug 17", "Sep", "Oct", "Nov", "Dec", "Jan 18", "Feb", "Mar", "Apr"],
            "gridLineWidth": 1,
            "gridLineDashStyle" : "dot"
          },

          "yAxis": {
            "allowDecimals": False,
            "title": "",
            "gridLineWidth": 1,
            "tickLength": 5,
            "tickWidth": 1,
            "tickPosition": "outside",
            "labels": {
              "align": "right",
              "x":-10
            },
            "lineWidth":1
          },
          "colors": ["#93979b", "#fda934"]
        }
        return config