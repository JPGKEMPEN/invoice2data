# -*- coding: utf-8 -*-
# Run: python -m unittest tests.test_cli

# Or: python -m unittest discover

# 1. You define your own class derived from unittest.TestCase.
# 2. Then you fill it with functions that start with 'test_'
# 3. You run the tests by placing unittest.main() in your file,
#    usually at the bottom.

# https://docs.python.org/3.10/library/unittest.html#test-cases

import datetime
import os
import json
import shutil
import csv
from xml.dom import minidom

try:
    from io import StringIO  # noqa: F401
except ImportError:
    from io import StringIO  # noqa: F401
import unittest

import pkg_resources
from invoice2data.main_original import create_parser, main
from invoice2data.extract.loader import read_templates

from .common import get_sample_files, exclude_template, inputparser_specific


def have_ocrmypdf():
    try:
        import ocrmypdf  # noqa: F401
    except ImportError:
        return False
    return True


needs_ocrmypdf = unittest.skipIf(not have_ocrmypdf(), reason="requires ocrmypdf")


class TestCLI(unittest.TestCase):
    def setUp(self):
        self.templates = read_templates()
        self.parser = create_parser()

    def compare_json_content(self, test_file, json_file):
        with open(test_file) as json_test_file, open(json_file) as json_json_file:
            jdatatest = json.load(json_test_file)
            jdatajson = json.load(json_json_file)
            return jdatajson == jdatatest

    def test_input(self):
        args = self.parser.parse_args(['--input-reader', 'pdftotext'] + get_sample_files('.pdf'))
        main(args)

    def test_output_name(self):
        test_file = 'inv_test_8asd89f78a9df.csv'
        exclude_list = ['AzureInterior.pdf']
        test_list = exclude_template(get_sample_files('.pdf'), exclude_list)
        args = self.parser.parse_args(
            ['--output-name', test_file, '--output-format', 'csv'] + test_list
        )
        main(args)
        self.assertTrue(os.path.exists(test_file))
        os.remove(test_file)

    def test_debug(self):
        args = self.parser.parse_args(['--debug'] + get_sample_files('.pdf'))
        main(args)

    # TODO: move result comparison to own test module.
    # TODO: parse output files instaed of comparing them byte-by-byte.

    def test_content_json(self):
        input_files = get_sample_files(('.pdf', '.txt'))
        json_files = get_sample_files('.json')
        test_files = 'test_compare.json'
        for ifile in input_files:
            for jfile in json_files:
                if ifile[:-4] == jfile[:-5]:
                    args = self.parser.parse_args(
                        ['--output-name', test_files, '--output-format', 'json', ifile]
                    )
                    main(args)
                    compare_verified = self.compare_json_content(test_files, jfile)
                    print(compare_verified)
                    if not compare_verified:
                        self.assertTrue(False, 'Failed to verify parsing result for ' + jfile)
                    os.remove(test_files)

    def test_output_format_date_json(self):
        pdf_files = get_sample_files('free_fiber.pdf')
        test_file = 'test_compare.json'
        for pfile in pdf_files:
            args = self.parser.parse_args(
                ['--output-name', test_file, '--output-format', 'json', '--output-date-format', "%d/%m/%Y", pfile]
            )
            main(args)
            with open(test_file) as json_test_file:
                jdatatest = json.load(json_test_file)
            compare_verified = (jdatatest[0]['date'] == '02/07/2015') and (jdatatest[0]['date_due'] == '05/07/2015')
            print(compare_verified)
            if not compare_verified:
                self.assertTrue(False, 'Unexpected date format')
            os.remove(test_file)

    def test_output_format_date_csv(self):
        pdf_files = get_sample_files('free_fiber.pdf')
        test_file = 'test_compare.csv'
        for pfile in pdf_files:
            args = self.parser.parse_args(
                ['--output-name', test_file, '--output-format', 'csv', '--output-date-format', '%d/%m/%Y', pfile]
            )
            main(args)
            with open(test_file) as csv_test_file:
                csvdatatest = csv.DictReader(csv_test_file, delimiter=',')
                for row in csvdatatest:
                    compare_verified = (row['date'] == '02/07/2015') and (row['date_due'] == '05/07/2015')
                    print(compare_verified)
                    if not compare_verified:
                        self.assertTrue(False, 'Unexpected date format')
            os.remove(test_file)

    def test_output_format_date_xml(self):
        pdf_files = get_sample_files('free_fiber.pdf')
        test_file = 'test_compare.xml'
        for pfile in pdf_files:
            args = self.parser.parse_args(
                ['--output-name', test_file, '--output-format', 'xml', '--output-date-format', '%d/%m/%Y', pfile]
            )
            main(args)
            with open(test_file) as xml_test_file:
                xmldatatest = minidom.parse(xml_test_file)
            dates = xmldatatest.getElementsByTagName('date')
            compare_verified = (dates[0].firstChild.data == '02/07/2015')
            print(compare_verified)
            if not compare_verified:
                self.assertTrue(False, 'Unexpected date format')
            os.remove(test_file)

    def test_copy(self):
        # folder = pkg_resources.resource_filename(__name__, 'pdfs')
        directory = os.path.dirname("tests/copy_test/pdf/")
        # make sure directory is deleted
        shutil.rmtree("tests/copy_test/", ignore_errors=True)
        os.makedirs(directory)

        exclude_list = ["AzureInterior.pdf"]
        test_list = exclude_template(get_sample_files(".pdf"), exclude_list)
        args = self.parser.parse_args(["--copy", "tests/copy_test/pdf"] + test_list)
        main(args)
        qty_copied_files = sum(
            len(files)
            for _, _, files in os.walk(
                pkg_resources.resource_filename(__name__, "copy_test/pdf")
            )
        )
        print("test_copy - Amount of copied files %s" % qty_copied_files)
        print("test_copy - test_list length", len(test_list))
        shutil.rmtree("tests/copy_test/", ignore_errors=True)
        self.assertEqual(qty_copied_files, len(test_list))

    # def test_template(self):
    #     directory = os.path.dirname("invoice2data/test/temp_test/")
    #     os.makedirs(directory)
    #     args = self.parser.parse_args(['--template-folder', 'ACME-templates', self._get_test_file_path()])
    #     main(args)
    #     shutil.rmtree('invoice2data/test/temp_test/', ignore_errors=True)
    #     self.assertTrue(args.template_folder)

    def test_exclude_template(self):
        for path, subdirs, files in os.walk(pkg_resources.resource_filename(__name__, 'compare')):
            for file in files:
                if file.endswith("oyo.pdf"):
                    my_file = os.path.join(path, file)
        directory = os.path.dirname("tests/temp_test/")
        os.makedirs(directory)
        shutil.copy(
            'src/invoice2data/extract/templates/com/com.oyo.invoice.yml', 'tests/temp_test/'
        )
        args = self.parser.parse_args(
            ['--exclude-built-in-templates', '--template-folder', directory, my_file]
        )
        main(args)
        shutil.rmtree('tests/temp_test/')

    def get_filename_format_test_data(self, filename_format):
        # Generate test input and expected output by walking the compare dir
        data = {}
        for path, subdirs, files in os.walk(pkg_resources.resource_filename(__name__, 'compare')):
            for file in files:
                root, ext = os.path.splitext(file)
                if "AzureInterior" in file:
                    continue
                if inputparser_specific(file):
                    print("input parser specific file found!!!")
                    continue
                if root not in data:
                    data[root] = {}
                if file.endswith(('.pdf', '.txt')):
                    data[root]['input_fpath'] = os.path.join(path, file)
                if file.endswith('.json'):
                    with open(os.path.join(path, file), 'r') as f:
                        res = json.load(f)[0]
                        date = datetime.datetime.strptime(res['date'], '%Y-%m-%d')
                        data[root]['output_fname'] = filename_format.format(
                            date=date.strftime('%Y-%m-%d'),
                            invoice_number=res['invoice_number'],
                            desc=res['desc'],
                        )
        return data

    def test_copy_with_default_filename_format(self):
        copy_dir = os.path.join('tests', 'copy_test', 'pdf')
        # make sure directory is deleted
        shutil.rmtree(os.path.dirname(copy_dir), ignore_errors=True)
        filename_format = "{date} {invoice_number} {desc}.pdf"

        data = self.get_filename_format_test_data(filename_format)

        os.makedirs(copy_dir)

        sample_files = [v['input_fpath'] for k, v in data.items()]

        args = self.parser.parse_args(['--copy', copy_dir] + sample_files)
        main(args)

        self.assertTrue(
            all(os.path.exists(os.path.join(copy_dir, v['output_fname'])) for k, v in data.items())
        )

        shutil.rmtree(os.path.dirname(copy_dir), ignore_errors=True)

    def test_copy_with_custom_filename_format(self):
        copy_dir = os.path.join('tests', 'copy_test', 'pdf')
        filename_format = "Custom Prefix {date} {invoice_number}.pdf"

        data = self.get_filename_format_test_data(filename_format)

        os.makedirs(copy_dir)

        sample_files = [v['input_fpath'] for k, v in data.items()]

        args = self.parser.parse_args(
            ['--copy', copy_dir, '--filename-format', filename_format] + sample_files
        )
        main(args)

        self.assertTrue(
            all(os.path.exists(os.path.join(copy_dir, v['output_fname'])) for k, v in data.items())
        )

        shutil.rmtree(os.path.dirname(copy_dir), ignore_errors=True)

    def test_area(self):
        pdf_files = get_sample_files('NetpresseInvoice.pdf')
        test_file = 'test_area.json'
        for pfile in pdf_files:
            args = self.parser.parse_args(
                ['--output-name', test_file, '--output-format', 'json', '--output-date-format', "%Y-%m-%d", pfile]
            )
            main(args)
            with open(test_file) as json_test_file:
                jdatatest = json.load(json_test_file)
            compare_verified = jdatatest[0]['date'] == '2022-11-28'
            if not compare_verified:
                self.assertTrue(False, 'Failure in area rule')
            os.remove(test_file)

    # advanced test case (saeco)
    # Where the pdf has to be ocr'd first
    # before any keywords can be matched

    @needs_ocrmypdf
    def test_ocrmypdf(self):
        pdf_files = get_sample_files("saeco.pdf", exclude_input_specific=False)
        test_file = "test_ocrmypdf.json"
        for pfile in pdf_files:
            args = self.parser.parse_args(
                [
                    "--output-name",
                    test_file,
                    "--input-reader",
                    "ocrmypdf",
                    "--output-format",
                    "json",
                    "--output-date-format",
                    "%Y-%m-%d",
                    pfile,
                ]
            )
            main(args)
            with open(test_file) as json_test_file:
                jdatatest = json.load(json_test_file)
            compare_verified = jdatatest[0]["date"] == "2022-09-08"
            if not compare_verified:
                self.assertTrue(False, "Failure in ocrmypdf test")
            os.remove(test_file)

    # Test the fallback from pdf to text to ocrmypdf.
    # with ocrmypdf installed

    @needs_ocrmypdf
    def test_fallback_with_ocrmypdf(self):
        pdf_files = get_sample_files("saeco.pdf", exclude_input_specific=False)
        test_file = "test_fallback_ocrmypdf.json"
        for pfile in pdf_files:
            args = self.parser.parse_args(
                [
                    "--output-name",
                    test_file,
                    "--input-reader",
                    "pdftotext",
                    "--output-format",
                    "json",
                    "--output-date-format",
                    "%Y-%m-%d",
                    pfile,
                ]
            )
            main(args)
            with open(test_file) as json_test_file:
                jdatatest = json.load(json_test_file)
            compare_verified = jdatatest[0]["date"] == "2022-09-08"
            if not compare_verified:
                self.assertTrue(False, "Failure in fallback to ocrmypdf test with ocrmypdf installed")
            os.remove(test_file)


if __name__ == '__main__':
    unittest.main()
