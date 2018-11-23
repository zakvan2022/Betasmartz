#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
required packages to install
linux: apt-get install tesseract
python3: pip-install pyPdf2
"""

import argparse
import os
import shutil
import sys
import json
import subprocess
import logging
import random
import string

logger = logging.getLogger('pdf_parsers.tax_return')


def id_generator(size=6, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))


def get_pdf_content_lines(pdf_file_path):
    with open(pdf_file_path, 'rb') as f:
        tmp_file_id = id_generator()
        subprocess.run(['pdftotext', pdf_file_path, '/tmp/' + tmp_file_id], stdout=subprocess.PIPE)
        with open('/tmp/' + tmp_file_id, 'rb') as f:
            return f.read()


# for each item to extract its string, the value is found between
# the pairs in the list e.g. SSN is found between "SSN:", "SPOUSE SSN:"
keywords = {
    'IntroChunk': ['SHOWN ON RETURN:\n', '\n\nADDRESS:\n'],
    "filing_status": ["\n\nFILING STATUS:\n", "\nFORM NUMBER:\n"],
    'name': ['\nNAME(S) SHOWN ON RETURN:', '\nADDRESS:\n'],
    'SSN': ['\nSSN:', '\nSPOUSE SSN:'],
    'SSN_spouse': ['\nSPOUSE SSN:', '\nNAME(S) SHOWN ON RETURN:'],
    'address': ['\nADDRESS:\n\n', '\n\nFILING STATUS:'],
    'TotalIncomeColumn': ['TOTAL INCOME PER COMPUTER:\n\nPage 3 of 8\n\n', '\n\nAdjustments to Income'],
    'PaymentsColumn': ['AMOUNT PAID WITH FORM 4868:\n\n', 'Tax Return Transcript'],
    'PaymentsColumn2': ['TOTAL PAYMENTS PER COMPUTER:\n\n', '\n\nRefund or Amount Owed'],
    'RefundColumn': ['BAL DUE/OVER PYMT USING COMPUTER FIGURES:\n\n', '\n\nThird Party Designee'],
    'TaxAndCreditsColumn': ['GENERAL BUSINESS CREDITS:\n\n', 'Tax Return Transcript'],
    'exemptions': ['EXEMPTION NUMBER:\n', '\nDEPENDENT 1 NAME CTRL:'],
    'adjusted_column': ['ADJUSTED GROSS INCOME PER COMPUTER:', 'Tax and Credits'],
    'tax_and_credits_column': ['FORM 3800 GENERAL BUSINESS CREDITS:', 'Tax Return Transcript'],
    'tax_period': ['Tax Period Ending:', 'The following items reflect the amount as shown on the return'],
    'other_taxes_column': ['TOTAL TAX LIABILITY TP FIGURES PER COMPUTER:', 'Payments'],
    'tax_and_credits_column2': ['INCOME TAX AFTER CREDITS PER COMPUTER:', 'Other Taxes'],
}

output = {
    "sections": [
        {
            "name": "Introduction",
            "fields": {
                'IntroChunk': '',
                "SSN": "",
                "SSN_spouse": "",
                "name": "",
                "name_spouse": "",
                "address": "",
                "filing_status": "",
                'TaxAndCreditsColumn': '',
                'blind': '',
                'blind_spouse': '',
                'exemptions': '',
                'tax_period': '',
                # not finding below in 2006 sample
                # 'residency_status': '',
                # 'spouse_residency_status': '',
                # 'date_of_birth': '',
                # 'date_of_birth_spouse': '',
            }
        },
        {
            "name": "Income",
            "fields": {
                'adjusted_column': '',
                'adjusted_gross_income': '',
                'total_adjustments': '',
                'PaymentsColumn': '',
                'PaymentsColumn2': '',
                'TotalIncomeColumn': '',
                "total_income": "",
                'earned_income_credit': '',
                'combat_credit': '',
                'excess_ss_credit': '',
                'add_child_tax_credit': '',

                'RefundColumn': '',
                'refundable_credit': '',
                'premium_tax_credit': '',
                'total_payments': '',

                'tax_and_credits_column': '',
                'taxable_income': '',
                'exemption_amount': '',
                'tentative_tax': '',
                'std_deduction': '',

                'other_taxes_column': '',
                'se_tax': '',
                'total_tax': '',

                'tax_and_credits_column2': '',
                'total_credits': '',
            }
        }
    ]
}


def find_between(s, first, last):
    try:
        start = s.index(first) + len(first)
        end = s.index(last, start)
        return s[start:end]
    except ValueError:
        return ""


def parse_item(key, s):
    sub_str = keywords[key]
    start = sub_str[0]
    end = sub_str[1]
    result = find_between(s, start, end)

    return result.lstrip().rstrip().lstrip('.').rstrip('.').rstrip('\n')


def parse_text(string):
    i = 0
    for section in output["sections"]:
        for k, v in list(section["fields"].items()):
            if k in list(keywords.keys()):
                res = parse_item(k, string)
                if k == 'name':
                    if '&' in res:
                        csplit = res.split('&')
                        output["sections"][i]["fields"]['name'] = csplit[0] + csplit[1].split(' ')[-1]
                        output["sections"][i]["fields"]['name_spouse'] = csplit[1].strip(' ')
                elif k == "TotalIncomeColumn":
                    chunks = res.split('\n')
                    if len(chunks) > 2:
                        output["sections"][i]["fields"]['total_income'] = chunks[-2]
                elif k == 'PaymentsColumn':
                    chunks = [s for s in res.split('\n') if s != '$']
                    if len(chunks) > 11:
                        output["sections"][i]["fields"]['earned_income_credit'] = chunks[2]
                        output["sections"][i]["fields"]['combat_credit'] = chunks[7]
                        output["sections"][i]["fields"]['excess_ss_credit'] = chunks[9]
                        output["sections"][i]["fields"]['add_child_tax_credit'] = chunks[11]

                elif k == 'PaymentsColumn2':
                    chunks = res.split('\n')
                    if len(chunks) > 6:
                        output["sections"][i]["fields"]['total_payments'] = chunks[6]

                elif k == 'RefundColumn':
                    chunks = res.split('\n')
                    if len(chunks) > 5:
                        output["sections"][i]["fields"]['refundable_credit'] = chunks[5]

                elif k == 'adjusted_column':
                    chunks = res.split('\n')
                    if len(chunks) > 5:
                        output["sections"][i]["fields"]['total_adjustments'] = chunks[4]
                        output["sections"][i]["fields"]['adjusted_gross_income'] = chunks[6]

                elif k == 'tax_and_credits_column':
                    chunks = res.split('\n')
                    if len(chunks) > 5:
                        output["sections"][i]["fields"]['std_deduction'] = chunks[4]
                        output["sections"][i]["fields"]['exemption_amount'] = chunks[7]
                        output["sections"][i]["fields"]['taxable_income'] = chunks[8]
                        output["sections"][i]["fields"]['tentative_tax'] = chunks[11]

                elif k == 'tax_and_credits_column2':
                    chunks = res.split('\n')
                    if len(chunks) > 5:
                        output["sections"][i]["fields"]['total_credits'] = chunks[9]

                elif k == 'other_taxes_column':
                    chunks = res.split('\n')
                    if len(chunks) > 25:
                        output["sections"][i]["fields"]['se_tax'] = chunks[0]
                        output["sections"][i]["fields"]['total_tax'] = chunks[24]

                elif k == 'TaxAndCreditsColumn':
                    chunks = res.split('\n')
                    if len(chunks) > 5:
                        output["sections"][i]["fields"]['blind'] = chunks[1]
                        output["sections"][i]["fields"]['blind_spouse'] = chunks[3]

                if output["sections"][i]["fields"][k] == "":
                    output["sections"][i]["fields"][k] = res
        i += 1
    return output


def parse_vector_pdf(fl):
    # logger.error(get_pdf_content_lines(fl))
    res = get_pdf_content_lines(fl).decode("utf-8")
    return parse_text(res)


def parse_scanned_pdf(fl):
    tmp_pdfs = "tmp"
    if not os.path.exists(tmp_pdfs):
        os.makedirs(tmp_pdfs)

    os.system("convert -density 300 -alpha Off {0} {1}/img.tiff".format(fl, tmp_pdfs))
    os.system("tesseract {0}/img.tiff {0}/out".format(tmp_pdfs))
    cmd = "touch {0}/out.txt && sed -i -e 's/—/-/g' {0}/out.txt".format(tmp_pdfs)
    os.system(cmd)
    with open("{0}/out.txt".format(tmp_pdfs), 'r') as f:
        txt = f.read()

    shutil.rmtree(tmp_pdfs)
    txt = ''.join(txt)
    return parse_text(txt)


def parse_address(addr_str):
    # addr_str format:
    # 200 SAMPLE RD\nHOT SPRINGS, AR 33XXX
    address = {
        "address1": '',
        "address2": '',
        "city": '',
        "state": '',
        "post_code": ''
    }
    addr_list1 = addr_str.split('\n')
    address['address1'] = addr_list1[0].strip(' ,')
    if len(addr_list1) > 2:
        address['address2'] = addr_list1[1].strip(' ,')
    if len(addr_list1) == 2:
        address['city'] = addr_list1[1].split(',')[0]
        address['state'] = addr_list1[1].strip(' ').split(',')[1].split(' ')[1]
        address['post_code'] = addr_list1[1].split(' ')[-1]
    return address


def clean_results(results):
    clean_output = {}
    clean_output['SSN'] = results['sections'][0]['fields']['SSN']
    clean_output['SSN_spouse'] = results['sections'][0]['fields']['SSN_spouse']
    clean_output['name'] = results['sections'][0]['fields']['name']
    clean_output['name_spouse'] = results['sections'][0]['fields']['name_spouse']
    clean_output['address'] = parse_address(results['sections'][0]['fields']['address'])
    clean_output['filing_status'] = results['sections'][0]['fields']['filing_status']
    clean_output['blind'] = results['sections'][0]['fields']['blind']
    clean_output['blind_spouse'] = results['sections'][0]['fields']['blind_spouse']
    clean_output['exemptions'] = results['sections'][0]['fields']['exemptions']
    clean_output['tax_period'] = results['sections'][0]['fields']['tax_period'].replace('\n', '').strip(' ')

    clean_output['total_income'] = results['sections'][1]['fields']['total_income'].strip('$ ')
    clean_output['total_payments'] = results['sections'][1]['fields']['total_payments'].strip('$ ')

    clean_output['earned_income_credit'] = results['sections'][1]['fields']['earned_income_credit'].strip('$ ')
    clean_output['combat_credit'] = results['sections'][1]['fields']['combat_credit'].strip('$ ')
    clean_output['excess_ss_credit'] = results['sections'][1]['fields']['excess_ss_credit'].strip('$ ')
    clean_output['add_child_tax_credit'] = results['sections'][1]['fields']['add_child_tax_credit'].strip('$ ')
    clean_output['refundable_credit'] = results['sections'][1]['fields']['refundable_credit'].strip('$ ')
    clean_output['premium_tax_credit'] = results['sections'][1]['fields']['premium_tax_credit'].strip('$ ')

    clean_output['adjusted_gross_income'] = results['sections'][1]['fields']['adjusted_gross_income'].strip('$ ')
    clean_output['total_adjustments'] = results['sections'][1]['fields']['total_adjustments'].strip('$ ')
    clean_output['taxable_income'] = results['sections'][1]['fields']['taxable_income'].strip('$ ')
    clean_output['exemption_amount'] = results['sections'][1]['fields']['exemption_amount'].strip('$ ')
    clean_output['tentative_tax'] = results['sections'][1]['fields']['tentative_tax'].strip('$ ')
    clean_output['std_deduction'] = results['sections'][1]['fields']['std_deduction'].strip('$ ')
    clean_output['se_tax'] = results['sections'][1]['fields']['se_tax'].strip('$ ')
    clean_output['total_tax'] = results['sections'][1]['fields']['total_tax'].strip('$ ')
    clean_output['total_credits'] = results['sections'][1]['fields']['total_credits'].strip('$ ')

    return clean_output


def parse_pdf(filename):
    try:
        # check if pdf is searchable, pdffonts lists fonts used in pdf, if scanned (image), list is empty
        cmd_out = subprocess.getstatusoutput("pdffonts {} | wc -l".format(filename))
        if int(cmd_out[1]) > 2:
            result = parse_vector_pdf(filename)
        else:
            result = parse_scanned_pdf(filename)

        logger.info('Tax Return PDF parsed OK')
        return clean_results(result)
    except Exception as e:
        logger.error(e)
        return


def main():
    try:
        parser = argparse.ArgumentParser()
        parser.add_argument('-f', '--file', type=str, help='Input pdf file', required=True)

        args = parser.parse_args()

        # check if pdf is searchable, pdffonts lists fonts used in pdf, if scanned (image), list is empty
        cmd_out = subprocess.getstatusoutput("pdffonts {} | wc -l".format(args.file))
        if int(cmd_out[1]) > 2:
            result = parse_vector_pdf(args.file)
        else:
            result = parse_scanned_pdf(args.file)

        print(json.dumps(clean_results(result), sort_keys=True, indent=4, separators=(',', ': ')))
        return result
    except KeyboardInterrupt:
        print('Keyboard interrupt!')
        return 0
    except Exception as e:
        print(e)
        raise e


if __name__ == "__main__":
    sys.exit(main())
