import unittest

from django.test import TestCase


# Create your tests here.


@unittest.skip("Skipping GenerateChartDataTest")
class GenerateChartDataTest(TestCase):
    def test_generate_user_chart_data(self):
        # Setup any necessary data for the test
        # Call the generate_user_chart_data function
        result = "something"
        # Add assertions to verify the expected outcome
        self.assertIsNotNone(result)
        # Add more specific assertions based on the expected result

        # with open('chart_data.json', 'w') as json_file:
        #     json.dump(result, json_file)
