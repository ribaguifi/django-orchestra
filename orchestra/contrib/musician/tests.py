from django.test import TestCase

from .models import DatabaseService, UserAccount
from .utils import get_bootstraped_percent


class DatabaseTest(TestCase):
    def test_database_from_json(self):
        data = {
            "url": "https://example.org/api/databases/1/",
            "id": 1,
            "name": "bluebird",
            "type": "mysql",
            "users": [
                    {
                        "url": "https://example.org/api/databaseusers/2/",
                        "id": 2,
                        "username": "bluebird"
                    }
            ],
            "resources": [
                {
                    "name": "disk",
                    "used": "1.798",
                    "allocated": None,
                    "unit": "MiB"
                }
            ]
        }

        database = DatabaseService.new_from_json(data)
        self.assertEqual(0, database.usage['percent'])


class DomainsTestCase(TestCase):
    def test_domain_not_found(self):
        response = self.client.post(
            '/auth/login/',
            {'username': 'admin', 'password': 'admin'},
            follow=True
        )
        self.assertEqual(200, response.status_code)

        response = self.client.get('/domains/3/')
        self.assertEqual(404, response.status_code)


class UserAccountTest(TestCase):
    def test_user_never_logged(self):
        data = {
            'billcontact': {'address': 'foo',
                            'city': 'Barcelona',
                            'country': 'ES',
                            'name': '',
                            'vat': '12345678Z',
                            'zipcode': '08080'},
            'date_joined': '2020-01-14T12:38:31.684495Z',
            'full_name': 'Pep',
            'id': 2,
            'is_active': True,
            'language': 'EN',
            'short_name': '',
            'type': 'INDIVIDUAL',
            'url': 'http://example.org/api/accounts/2/',
            'username': 'pepe'
        }
        account = UserAccount.new_from_json(data)
        self.assertIsNone(account.last_login)

    def test_user_never_logged2(self):
        # issue #6 Error on login when user never has logged into the system
        data = {
            'billcontact': {'address': 'bar',
                            'city': 'Barcelona',
                            'country': 'ES',
                            'name': '',
                            'vat': '12345678Z',
                            'zipcode': '34561'},
            'date_joined': '2020-01-14T12:38:31Z',
            'full_name': 'Pep',
            'id': 2,
            'is_active': True,
            'language': 'CA',
            'last_login': None,
            'short_name': '',
            'type': 'INDIVIDUAL',
            'url': 'http://127.0.0.1:9090/api/accounts/2/',
            'username': 'pepe'
        }
        account = UserAccount.new_from_json(data)
        self.assertIsNone(account.last_login)

    def test_user_without_billcontact(self):
        data = {
            'billcontact': None,
            'date_joined': '2020-03-05T09:49:21Z',
            'full_name': 'David Rock',
            'id': 2,
            'is_active': True,
            'language': 'CA',
            'last_login': '2020-03-19T10:21:49.504266Z',
            'resources': [{'allocated': None,
                           'name': 'disk',
                           'unit': 'GiB',
                           'used': '0.000'},
                          {'allocated': None,
                           'name': 'traffic',
                           'unit': 'GiB',
                           'used': '0.000'}],
            'short_name': '',
            'type': 'STAFF',
            'url': 'https://example.org/api/accounts/2/',
            'username': 'drock'
        }
        account = UserAccount.new_from_json(data)
        self.assertIsNotNone(account.billing)


class GetBootstrapedPercentTest(TestCase):
    BS_WIDTH = [0, 25, 50, 100]

    def test_exact_value(self):
        value = get_bootstraped_percent(25, 100)
        self.assertIn(value, self.BS_WIDTH)
        self.assertEqual(value, 25)

    def test_round_to_lower(self):
        value = get_bootstraped_percent(26, 100)
        self.assertIn(value, self.BS_WIDTH)
        self.assertEqual(value, 25)

    def test_round_to_higher(self):
        value = get_bootstraped_percent(48, 100)
        self.assertIn(value, self.BS_WIDTH)
        self.assertEqual(value, 50)

    def test_max_boundary(self):
        value = get_bootstraped_percent(200, 100)
        self.assertIn(value, self.BS_WIDTH)
        self.assertEqual(value, 100)

    def test_min_boundary(self):
        value = get_bootstraped_percent(-10, 100)
        self.assertIn(value, self.BS_WIDTH)
        self.assertEqual(value, 0)

    def test_invalid_total_is_zero(self):
        value = get_bootstraped_percent(25, 0)
        self.assertEqual(value, 0)

    def test_invalid_total_is_none(self):
        value = get_bootstraped_percent(25, None)
        self.assertEqual(value, 0)
