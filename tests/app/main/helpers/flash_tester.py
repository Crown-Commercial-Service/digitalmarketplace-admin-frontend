def assert_flashes(self, expected_message, expected_category='message'):
    with self.client.session_transaction() as session:
        try:
            category, message = session['_flashes'][0]
        except KeyError:
            raise AssertionError('nothing flashed')
        assert expected_message in message
        assert expected_category in category
