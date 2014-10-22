"""
Test suite for date parser
"""

import unittest

from ttt.date import read_date

# pylint: disable=too-many-public-methods, invalid-name
class DateTest(unittest.TestCase):
    "tests for ttt.date"

    def assertDateEqual(self, expected, dstr):
        "assert that date string parses as expected"
        self.assertEqual(expected, read_date(dstr))

    def test_read_date_junk(self):
        "reject junk strings"
        self.assertDateEqual(None, "preface")

    def test_read_date(self):
        "basic tests for the read date function"
        self.assertDateEqual("1521-12", "December 1521")

    def test_read_date_coincidence(self):
        "still get precise date if concidentally match parts"
        self.assertDateEqual("1521-02-15", "February 15, 1521")
        self.assertDateEqual("1521-02", "February 1521")
        self.assertDateEqual("1521-01", "January 1521")