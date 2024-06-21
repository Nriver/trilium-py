import unittest
from datetime import datetime, timezone
from trilium_py.client import ETAPI

class TestETAPI(unittest.TestCase):
    def setUp(self):
        self.etapi = ETAPI()

    def test_format_date_local(self):
        # Test case 1: Test with local date and time
        date = datetime(2023, 8, 21, 23, 38, 51, 110, tzinfo=timezone.utc)
        formatted_date = self.etapi.format_date(date, 'local')
        expected_date = '2023-08-21 23:38:51.110+0000'
        self.assertEqual(formatted_date, expected_date)

        # Test case 2: Test with local date and time in a different timezone
        date = datetime(2023, 8, 21, 23, 38, 51, 110, tzinfo=timezone(offset=timedelta(hours=2)))
        formatted_date = self.etapi.format_date(date, 'local')
        expected_date = '2023-08-21 21:38:51.110+0000'  # Adjusted for UTC
        self.assertEqual(formatted_date, expected_date)

    def test_format_date_utc(self):
        # Test case 1: Test with UTC date and time
        date = datetime(2011, 3, 8, 7, 0, 0, 83, tzinfo=timezone.utc)
        formatted_date = self.etapi.format_date(date, 'UTC')
        expected_date = '2011-03-08 07:00:00.083Z'
        self.assertEqual(formatted_date, expected_date)

        # Test case 2: Test with UTC date and time with milliseconds
        date = datetime(2022, 9, 15, 10, 30, 45, 456789, tzinfo=timezone.utc)
        formatted_date = self.etapi.format_date(date, 'UTC')
        expected_date = '2022-09-15 10:30:45.456Z'
        self.assertEqual(formatted_date, expected_date)

    def test_format_date_edge_cases(self):
        # Test case 1: Test with date as None
        date = None
        formatted_date = self.etapi.format_date(date, 'local')
        self.assertIsNone(formatted_date)

        # Test case 2: Test with date with a different timezone
        date = datetime(2022, 12, 31, 23, 59, 59, tzinfo=timezone(offset=timedelta(hours=3)))
        formatted_date = self.etapi.format_date(date, 'local')
        expected_date = '2022-12-31 20:59:59.000+0000'  # Adjusted for UTC
        self.assertEqual(formatted_date, expected_date)

if __name__ == '__main__':
    unittest.main()        
