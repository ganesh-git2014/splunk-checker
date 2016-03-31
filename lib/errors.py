'''_
@author: Curtis Yu
@contact: cuyu@splunk.com
@since: 3/30/16
'''


class HTTPException(BaseException):
    def __init__(self, type, content=None):
        """
        Transform
        """
        self.messages = dict()
        self.messages['is_http_exception'] = True
        if type == 'Response':
            response = content
            self.messages = response.json()
            # This key value is used for ClusterChecker._check_http_exception to identify weather
            # the check result is a http exception or a normal result.
            self.messages['status_code'] = response.status_code
            self.messages['url'] = response.url
        elif type == 'Skip':
            # Try to fake a similar structure as above
            tmp = dict()
            tmp['text'] = 'The check is skipped due to http exception.'
            self.messages['messages'] = []
            self.messages['messages'].append(tmp)
            self.messages['status_code'] = None
            self.messages['url'] = None
        elif type == 'ReadTimeout':
            err = content
            tmp = dict()
            tmp['text'] = err.message.message
            self.messages['messages'] = []
            self.messages['messages'].append(tmp)
            self.messages['status_code'] = None
            self.messages['url'] = err.message.url
        else:
            raise Exception('Exception type not supported!')
