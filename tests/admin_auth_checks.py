import os
import unittest
from unittest.mock import patch


os.environ['REDEEM_SCROLL_ADMIN_PASSWORD'] = 'correct-password'
os.environ['REDEEM_SCROLL_SECRET_KEY'] = 'test-secret-key'

import web_app


SAMPLE_CODE = {
    'id': 1,
    'code': 'TESTCODE123',
    'game': 'genshin',
    'source_title': '원본 게시글',
    'source_url': 'https://example.test/source',
    'source_posted_at': '2026-05-07 12:00',
    'is_valid': True,
    'is_new': True,
    'created_at': '2026-05-07 12:05',
    'sort_at': '2026-05-07T12:00:00',
}


class AdminAuthChecks(unittest.TestCase):
    def setUp(self):
        web_app.app.config.update(TESTING=True)
        self.patches = [
            patch.object(web_app, 'get_all_codes', side_effect=lambda: [SAMPLE_CODE.copy()]),
            patch.object(web_app, 'get_stats', return_value={'total': 1, 'by_game': {'genshin': 1}}),
            patch.object(web_app, 'get_today_count', return_value=1),
        ]
        for patcher in self.patches:
            patcher.start()
        self.client = web_app.app.test_client()

    def tearDown(self):
        for patcher in reversed(self.patches):
            patcher.stop()

    def test_admin_query_parameter_no_longer_logs_in(self):
        response = self.client.get('/?admin=correct-password')

        self.assertEqual(response.status_code, 200)
        self.assertNotIn('class="code-meta"', response.get_data(as_text=True))
        with self.client.session_transaction() as flask_session:
            self.assertNotIn('is_admin', flask_session)

    def test_public_api_strips_admin_metadata(self):
        response = self.client.get('/api/codes')
        data = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertNotIn('source_url', data[0])
        self.assertNotIn('source_posted_at', data[0])
        self.assertNotIn('created_at', data[0])

    def test_login_enables_admin_metadata_and_logout_removes_it(self):
        bad_response = self.client.post('/admin/login', data={'password': 'wrong'})
        self.assertEqual(bad_response.status_code, 401)

        login_response = self.client.post('/admin/login', data={'password': 'correct-password'})
        self.assertEqual(login_response.status_code, 302)
        self.assertEqual(login_response.headers['Location'], '/')

        admin_api = self.client.get('/api/codes').get_json()
        self.assertEqual(admin_api[0]['source_url'], SAMPLE_CODE['source_url'])

        admin_page = self.client.get('/').get_data(as_text=True)
        self.assertIn('class="code-meta"', admin_page)
        self.assertIn('/admin/logout', admin_page)

        self.client.get('/admin/logout')
        public_api = self.client.get('/api/codes').get_json()
        self.assertNotIn('source_url', public_api[0])

    def test_scrape_endpoints_require_admin(self):
        for method, path in (
            ('post', '/api/scrape'),
            ('get', '/api/scrape/status'),
            ('post', '/api/scrape/ack'),
        ):
            with self.subTest(path=path):
                response = getattr(self.client, method)(path)
                self.assertEqual(response.status_code, 403)


if __name__ == '__main__':
    unittest.main()
