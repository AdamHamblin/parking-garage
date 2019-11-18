class Request(object):
    def __init__(self, body=None, headers=None, context=None, path='', params=None):
        self.body = body
        if headers is None:
            headers = {'Content-Type': 'application/json'}
        self.headers = headers
        self.context = context
        self.path = path
        if params is None:
            params = {}
        self.params = params


class Response(object):
    def __init__(self, body='', status='200 OK'):
        self.body = body
        self.status = status


