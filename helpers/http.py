import json
import urllib2
import traceback
from keystoneclient import exceptions
from keystoneclient.v2_0 import Client as KeystoneClient

from tools import logger


class HTTPClient(object):
    """HTTPClient."""  # TODO documentation

    def __init__(self, url, keystone_url, credentials, **kwargs):
        logger.info('Initiate HTTPClient with url %s', url)
        self.url = url
        self.keystone_url = keystone_url
        self.creds = dict(credentials, **kwargs)
        self.keystone = None
        self.opener = urllib2.build_opener(urllib2.HTTPHandler)

    def authenticate(self):
        try:
            logger.info('Initialize keystoneclient with url %s',
                        self.keystone_url)
            self.keystone = KeystoneClient(
                auth_url=self.keystone_url, **self.creds)
            # it depends on keystone version, some versions doing auth
            # explicitly some don't, but we are making it explicitly always
            self.keystone.authenticate()
            logger.debug('Authorization token is successfully updated')
        except exceptions.AuthorizationFailure:
            logger.warning(
                'Cant establish connection to keystone with url %s',
                self.keystone_url)

    @property
    def token(self):
        if self.keystone is not None:
            try:
                return self.keystone.auth_token
            except exceptions.AuthorizationFailure:
                logger.warning(
                    'Cant establish connection to keystone with url %s',
                    self.keystone_url)
            except exceptions.Unauthorized:
                logger.warning("Keystone returned unauthorized error, trying "
                               "to pass authentication.")
                self.authenticate()
                return self.keystone.auth_token
        return None

    def get(self, endpoint):
        req = urllib2.Request(self.url + endpoint)
        return self._open(req)

    def post(self, endpoint, data=None, content_type="application/json"):
        if not data:
            data = {}
        req = urllib2.Request(self.url + endpoint, data=json.dumps(data))
        req.add_header('Content-Type', content_type)
        return self._open(req)

    def put(self, endpoint, data=None, content_type="application/json"):
        if not data:
            data = {}
        req = urllib2.Request(self.url + endpoint, data=json.dumps(data))
        req.add_header('Content-Type', content_type)
        req.get_method = lambda: 'PUT'
        return self._open(req)

    def delete(self, endpoint):
        req = urllib2.Request(self.url + endpoint)
        req.get_method = lambda: 'DELETE'
        return self._open(req)

    def _open(self, req):
        try:
            return self._get_response(req)
        except urllib2.HTTPError as e:
            if e.code == 401:
                logger.warning('Authorization failure: {0}'.format(e.read()))
                self.authenticate()
                return self._get_response(req)
            elif e.code == 504:
                logger.error("Got HTTP Error 504: "
                             "Gateway Time-out: {}".format(e.read()))
                return self._get_response(req)
            else:
                logger.error('{} code {} [{}]'.format(e.reason,
                                                      e.code,
                                                      e.read()))
                raise

    def _get_response(self, req):
        if self.token is not None:
            try:
                logger.debug('Set X-Auth-Token to {0}'.format(self.token))
                req.add_header("X-Auth-Token", self.token)
            except exceptions.AuthorizationFailure:
                logger.warning('Failed with auth in http _get_response')
                logger.warning(traceback.format_exc())
        return self.opener.open(req)
