from collections import Counter
from contextlib import redirect_stdout
from io import StringIO

from django.test import SimpleTestCase
from openpyxl import load_workbook

from .triage import get_reliability_meta, _blocked_for_urgent_reliability
from .views import XLSX_PATH, XLSX_SHEET, _load_resources_from_xlsx


class ResourceDataTests(SimpleTestCase):
    def test_master_sheet_fields_match_every_resource(self):
        with redirect_stdout(StringIO()):
            resources, diagnostics = _load_resources_from_xlsx()
        self.assertEqual(diagnostics['errors'], [])
        self.assertEqual(diagnostics['skipped_no_coords'], 0)
        self.assertEqual(diagnostics['bad_latlng'], 0)
        workbook = load_workbook(XLSX_PATH, data_only=True)
        try:
            values = workbook[XLSX_SHEET].values
            headers = next(values)
            rows = [dict(zip(headers, row)) for row in values if any(v is not None for v in row)]
        finally:
            workbook.close()
        self.assertEqual(len(resources), len(rows))
        self.assertGreater(len(resources), 0)
        fields = {
            'name': 'Name of Service', 'address': 'Address',
            'phone_number': 'Phone Number', 'days': 'Days of Service',
            'restrictions': 'Restrictions of Service', 'link': 'link to site',
            'classification': 'Classification', 'description': 'Description',
            'condensed_reliability_description': 'Reliability Description',
        }
        for resource, row in zip(resources, rows):
            for field, column in fields.items():
                self.assertEqual(resource[field], str(row[column] or '').strip())
            self.assertEqual(get_reliability_meta(resource)['label'], row['Classification'])
        self.assertEqual(Counter(r['classification'] for r in resources),
                         Counter(row['Classification'] for row in rows))

    def test_classification_overrides_numeric_ratings(self):
        for label in ['Highly Reliable', 'Reliable', 'Mixed Reviews',
                      'Low Reliability', 'Insufficient Reviews']:
            resource = {'classification': label, 'reliability': 10, 'avg_reliability_ratings': 10}
            self.assertEqual(get_reliability_meta(resource)['label'], label)
            self.assertEqual(_blocked_for_urgent_reliability(resource, 1), label == 'Low Reliability')
        self.assertEqual(get_reliability_meta({'reliability': 10})['label'], 'Not Yet Confirmed')

    def test_map_and_count_use_master_sheet(self):
        with redirect_stdout(StringIO()):
            response = self.client.get('/map/', HTTP_HOST='localhost')
            count = self.client.get('/resources/count/', HTTP_HOST='localhost')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(count.json()['count'], len(response.context['resources']))
        self.assertContains(response, 'Restrictions</span>')
        self.assertContains(response, 'Insufficient Reviews')
