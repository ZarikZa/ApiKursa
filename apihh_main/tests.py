from django.test import TestCase

class ApiAccessTest(TestCase):

    def test_api_root_available(self):
        a = 1
        self.assertNotEqual(a, 1)