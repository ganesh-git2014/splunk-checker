'''_
@author: Curtis Yu
@contact: cuyu@splunk.com
@since: 5/6/16
'''

import logging
from abc import ABCMeta

_LOG_FORMAT = '[%(asctime)s] %(levelname)s - %(name)s: %(message)s'
_FILE_NAME = "splunk-checker.log"


def setup_logger(debug=False):
    """
    Setups up the logging library

    @param debug: If debug log messages are to be outputted
    @type debug: bool
    """
    level = logging.INFO
    if debug:
        level = logging.DEBUG
    logging.basicConfig(filename=_FILE_NAME, filemode='w', level=level, format=_LOG_FORMAT)


class Logging(object):
    __metaclass__ = ABCMeta

    def __init__(self):
        self._logger = self._get_logger()
        super(Logging, self).__init__()

    def _get_logger(self):
        '''
        Creates a new logger for this instance, should only be called once.

        @return: The newly created logger.
        '''
        return logging.getLogger(self._logger_name)

    @property
    def _logger_name(self):
        '''
        The name of the logger.

        @rtype: str
        '''
        return self.__class__.__name__

    @property
    def logger(self):
        '''
        The logger of this Splunk object.

        @return: The associated logger.
        '''
        return self._logger
