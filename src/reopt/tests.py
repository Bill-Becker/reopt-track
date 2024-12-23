from django.test import TestCase
from .views import generate_chart_data
import json
import unittest

# Create your tests here.

# @unittest.skip("Skipping GenerateChartDataTest")
class GenerateChartDataTest(TestCase):
    def test_generate_chart_data(self):
        # Setup any necessary data for the test
        # Call the generate_chart_data function
        result = generate_chart_data()
        # Add assertions to verify the expected outcome
        self.assertIsNotNone(result)
        # Add more specific assertions based on the expected result

        # with open('chart_data.json', 'w') as json_file:
        #     json.dump(result, json_file)
