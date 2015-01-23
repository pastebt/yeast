import os
import time
import urllib
import logging
import mimetypes
from hashlib import md5
from random import random
from cStringIO import StringIO
from Cookie import SimpleCookie

from ahttp import AHTTP
from acore import Worker, Listener, Aact, Acore, SocketClosed, AFILE

from fgdwcfpy.log import logexc


class AbstractSessionMiddleWare(Acore):
    def __init__(self, app):
        Acore.__init__(self)
        self.app = app
        self.session_id = None
        self.is_new_session_cookie = False
        self.sess_cookie_name = "YEASTSESSIONID"
        self.session_return_data = None

    def get(self, key):
        raise NotImplementedError("AbstractSessionMiddleWare.get")

    def put(self, key, value):
        raise NotImplementedError("AbstractSessionMiddleWare.put")

    def start(self):
        " from env, get Cookie, get Session ID "
        cookie = SimpleCookie(self.env.get("HTTP_COOKIE", ""))
        if self.sess_cookie_name not in cookie:
            cookie[self.sess_cookie_name] = self._build_session_id_str()
            self.is_new_session_cookie = True
        self.session_cookie = cookie[self.sess_cookie_name]
        self.session_id = self.session_cookie.value

    def _build_session_id_str(self):
        return md5("%s_%s_%s_%s_%s" % (self.env['REMOTE_ADDR'],
                                       self.env['REMOTE_PORT'],
                                       self.env['REQUEST_PATH'],
                                       time.time(), random()
                   )).hexdigest()

    def handle_start_response(self, status, headers, exc_info=None):
        # modify header to set session cookie
        if self.is_new_session_cookie:
            #logging.warn("Set-Cookie")
            headers['Set-Cookie'] = self.session_cookie.OutputString()
        # call original start_response with modifed header
        self.upper_start_response(status, headers, exc_info)

    def __call__(self, env, start_response):
        self.env = env
        #self.acc.bind_user(env['yeast.SELF'])
        env['yeast.session'] = self
        self.upper_start_response = start_response
        return self._call_(env, self.handle_start_response)

    def _call_(self, env, start_response):
        for y in self.app(env, start_response):
            yield y


class SessionInMemory(AbstractSessionMiddleWare):
    sessions_dict = {}

    def get(self, key, default=None):
        self.session_data = self.sessions_dict.get(
                            self.session_id, {}).get(key, default)
        return self.session_data

    def put(self, key, value):
        if self.session_id not in self.sessions_dict:
            self.sessions_dict[self.session_id] = {}
        self.sessions_dict[self.session_id][key] = value


def WsgiApp(env, start_response):
    start_response(200, {})
    return 'Hallo World\r\n'


class WsgiHandler(Acore):
    app = None
    env = {'SERVER_NAME': 'yeast asvr 0.1',
           #'GATEWAY_INTERFACE'] = 'CGI/1.1'
           'SERVER_PORT': '8080',
           'SCRIPT_NAME': '',
          }

    def __init__(self, sock, addr):
        Acore.__init__(self)
        self.addr = addr
        self.ahttp = AHTTP(sock, user=self)

    def setup_env(self):
        env = self.environ = self.env.copy()
        http_dict = self.ahttp.http_dict
        hs = http_dict['headers']
        env['yeast.SELF'] = self
        env['yeast.AHTTP'] = self.ahttp
        #env['HTTP_HEADERS'] = hs
        env['REMOTE_ADDR'] = self.addr[0]
        env['REMOTE_PORT'] = self.addr[1]
        if hs.typeheader is None:
            env['CONTENT_TYPE'] = hs.type
        else:
            env['CONTENT_TYPE'] = hs.typeheader
        l = hs.getheader('content-length')
        if l:
            env['CONTENT_LENGTH'] = l
        env['SERVER_PROTOCOL'] = http_dict['version']
        env['REQUEST_METHOD'] = http_dict['action']
        env['REQUEST_PATH'] = path = http_dict['path']

        pq = path.split('?', 1)
        p, q = pq[0], pq[1] if len(pq) == 2 else ''

        env['PATH_INFO'] = urllib.unquote(p)
        env['QUERY_STRING'] = q

        for k, v in hs.items():
            k = k.replace('-', '_').upper()
            v = v.strip()
            if k in env:
                continue                     # skip content length, type,etc.
            if 'HTTP_' + k in env:
                env['HTTP_' + k] += ',' + v  # comma-separate multiple headers
            else:
                env['HTTP_' + k] = v

    def wsgi_write(self, data):
        self._buf.write(data)
        self.sent_size += len(data)

    def start_response(self, status, headers, exc_info=None):
        self._buf = StringIO()
        self.sent_size = 0
        self.app_status = status
        self.app_headers = headers
        return self.wsgi_write

    def handle_error(self):
        #self.start_response()
        pass

    def get_body(self):
        #print int(self.environ.get('CONTENT_LENGTH', 0))
        if int(self.environ.get('CONTENT_LENGTH', 0)) > 0:
            for y in self.ahttp.get_body():
                yield y
        #else:
        #    self.ahttp.http_dict['body'] = StringIO()

    def _run(self):
        #assert isinstance(self.app, callable)
        try:
            for y in self.ahttp.get_head():
                yield y
        except SocketClosed:
            self.ahttp.sock.close()
            logging.debug("%s SocketClosed" % str(self.addr))
            return
        self.setup_env()

        for y in self.get_body():
            yield y

        self.result = self.app(self.environ, self.start_response)
        #print repr(self.result)
        for x in self.result:
            if isinstance(x, Aact):
                yield x
            else:
                self.wsgi_write(x)

        # process http status and headers
        msg = StringIO()
        msg.write("%s %d OK\r\n" % (
                   self.ahttp.http_dict['version'], self.app_status))

        # FIXME? is this the right way?
        self.app_headers['Content-Length'] = self.sent_size

        for h, v in self.app_headers.iteritems():
            msg.write("%s: %s\r\n" % (h, v))
        msg.write('\r\n')
        for y in self.ahttp.write_all(msg.getvalue()):
            yield y
        # http body
        for y in self.ahttp.write_all(self._buf.getvalue()):
            yield y
        # FIXME
        self.ahttp.sock.close()

    def run(self):
        try:
            for y in self._run():
                yield y
        except Exception, e:
            logging.error("self.addr = %s" % str(self.addr))
            logexc()
            #logging.error(e)


# copy from wsgiref/handlers.py
# Weekday and month names for HTTP date/time formatting; always English!
_weekdayname = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
_monthname = [None,     # Dummy so we can use 1-based month numbers
              "Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def format_date_time(timestamp):
    year, month, day, hh, mm, ss, wd, y, z = time.gmtime(timestamp)
    return "%s, %02d %3s %4d %02d:%02d:%02d GMT" % (
        _weekdayname[wd], day, _monthname[month], year, hh, mm, ss
    )


def static_file_info(fn):
    # Content-Type: text/css
    # Last-Modified: Mon, 07 Oct 2013 18:25:10 GMT
    logging.debug("static_file " + fn)
    try:
        ct, e = mimetypes.guess_type(fn)
        lm = format_date_time(os.path.getmtime(fn))
        fin = open(fn)
    except IOError, e:
        return (None, 404, {})
    else:
        return (fin, 200, {"Last-Modified": lm, "Content-Type": ct})


def start_server(app, handler=WsgiHandler, addr=('', 8080)):
    l = Listener(addr=addr, worker=handler)
    handler.app = staticmethod(app)
    handler.env['SERVER_PORT'] = str(l.addr[1])
    l.start()
    l.loop()
