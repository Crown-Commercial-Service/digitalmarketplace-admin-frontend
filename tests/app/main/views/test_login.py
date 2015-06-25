from lxml import html
try:
    from urlparse import urlsplit
    from StringIO import StringIO
except ImportError:
    from urllib.parse import urlsplit
    from io import BytesIO as StringIO

from ...helpers import BaseApplicationTest


class TestSession(BaseApplicationTest):

    def _login(self, username, password, is_authenticated=True):
        post_response = self.client.post('/admin/login', data=dict(
            username=username,
            password=password
        ))

        get_response = self.client.get('/admin')

        if is_authenticated:
            self.assertEquals(302, post_response.status_code)
            self.assertEquals(
                "/admin", urlsplit(post_response.location).path)
            self.assertEquals(200, get_response.status_code)
        else:
            self.assertEquals(200, post_response.status_code)
            self.assertEquals(302, get_response.status_code)
            self.assertEquals(
                "/admin/login", urlsplit(get_response.location).path)

    def test_index(self):
        response = self.client.get('/admin')
        self.assertEquals(302, response.status_code)

    def test_url_with_non_canonical_trailing_slash(self):
        response = self.client.get('/admin/')
        self.assertEquals(301, response.status_code)
        self.assertEquals("http://localhost/admin", response.location)

    def test_valid_login(self):
        self._login(
            username="admin",
            password="admin"
        )

    def test_invalid_logins(self):
        invalid_logins = [
            ("admin", "wrong"),
            ("adminadmin", ""),
            ("", "adminadmin")
        ]

        for invalid_login in invalid_logins:
            self._login(
                username=invalid_login[0],
                password=invalid_login[1],
                is_authenticated=False
            )


class TestLoginFormsNotAutofillable(BaseApplicationTest):

    def _forms_and_inputs_not_autofillable(
            self, url, expected_title
    ):
        response = self.client.get(url)
        self.assertEqual(200, response.status_code)

        document = html.fromstring(response.get_data(as_text=True))

        page_title = document.xpath(
            '//div[@class="page-container"]//h1/text()')[0].strip()
        self.assertEqual(expected_title, page_title)

        forms = document.xpath('//div[@class="page-container"]//form')

        for form in forms:
            self.assertEqual("off", form.get('autocomplete'))
            non_hidden_inputs = form.xpath('//input[@type!="hidden"]')

            for input in non_hidden_inputs:
                self.assertEqual("off", input.get('autocomplete'))

    def test_login_form_and_inputs_not_autofillable(self):
        self._forms_and_inputs_not_autofillable(
            "/admin/login",
            "Administrator login"
        )
