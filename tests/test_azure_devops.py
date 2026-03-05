from openreview.azure_devops import AzureDevOpsClient


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class FakeHttpClient:
    def __init__(self):
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def get(self, url):
        self.calls.append(('GET', url, None))
        if 'iterations?' in url:
            return FakeResponse({'value': [{'id': 1}, {'id': 2}]})
        if '/iterations/2/changes?' in url:
            return FakeResponse({'changeEntries': [
                {'item': {'path': '/a.c'}},
                {'item': {'path': '/b.c'}},
                {'item': {'path': '/a.c'}},
            ]})
        return FakeResponse({'value': [{'id': 11}]})

    def post(self, url, json):
        self.calls.append(('POST', url, json))
        return FakeResponse({'ok': True, 'url': url, 'json': json})

    def patch(self, url, json):
        self.calls.append(('PATCH', url, json))
        return FakeResponse({'ok': True, 'url': url, 'json': json})


def test_client_endpoints(monkeypatch) -> None:
    fake = FakeHttpClient()
    c = AzureDevOpsClient('org', 'proj', 'repo', 'pat')
    monkeypatch.setattr(c, '_client', lambda: fake)

    threads = c.get_pull_request_threads(7)
    assert threads == [{'id': 11}]

    paths = c.get_changed_files_latest_iteration(7)
    assert paths == ['/a.c', '/b.c']

    c.create_thread(7, {'x': 1})
    c.update_thread(7, 9, {'status': 1})
    c.create_comment(7, 9, 'hello')

    verbs = [v for v, *_ in fake.calls]
    assert 'GET' in verbs and 'POST' in verbs and 'PATCH' in verbs
