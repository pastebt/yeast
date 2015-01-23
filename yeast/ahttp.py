import logging
import xmlrpclib
from httplib import HTTPMessage
from cStringIO import StringIO

from acore import EOR, ACTCP, SocketClosed


class ACHUNK(ACTCP):
    "http://en.wikipedia.org/wiki/Chunked_transfer_encoding"

    def read_one_chunk(self, dstio=None):
        self.chunk_size = 0
        for y in self.read_all(seps=('\r\n',)):
            yield y
        s = self.request_data.strip().split(';', 1)
        self.chunk_size = int(s[0], 16)
        if len(s) > 1:
            self.chunk_attr = s[1]
        else:
            self.chunk_attr = None
        if self.chunk_size == 0:
            self.request_data = ''
            return
        for y in self.read_all(size=self.chunk_size):
            yield y
        if hasattr(dstio, 'write'):
            dstio.write(self.request_data)
        self.chunk_data = self.request_data
        for y in self.read_all(size=2):
            yield y
        if self.request_data != '\r\n':
            raise Exception("chunked format wrong")

    def write_one_chunk(self, data, attr_str=None):
        msg = str(len(data))
        if attr_str is not None:
            msg += ";" + attr_str
        msg += '\r\n'
        if data:
            msg += data + '\r\n'
        for y in self.write_all(msg):
            yield y


class AHTTP(ACHUNK):
    def get_head(self):
        for y in self.read_all(seps=("\n\r\n", "\n\n")):
            yield y
        if self.request_data == '' and isinstance(self.sep_hit, EOR):
            raise SocketClosed()
        shs = StringIO(self.request_data)
        self.http_dict = {'header_string': self.request_data}
        # state line
        self.http_dict['status_line'] = stl = shs.readline()
        hh = stl.split(None, 2)
        if len(hh) != 3:
            raise Exception("Miss status line %s" % repr(stl))
        if hh[0].startswith("HTTP"):    # server responce, use for client
            self.http_dict['version'] = hh[0]
            self.http_dict['status'] = hh[1]
            self.http_dict['reason'] = hh[2].strip()
            #self.http_dict.update(zip(('version', 'status', 'reason'), hh))
        elif hh[2].startswith("HTTP"):  # client request, use for server
            self.http_dict['action'] = hh[0]
            self.http_dict['path'] = hh[1]
            self.http_dict['version'] = hh[2].strip()
            #self.http_dict.update(action=hh[0], path=hh[1], version=hh[2])
        else:
            raise Exception("Bad status line: %s" % repr(stl))
        # shs be readed one line, ready for http headers
        self.http_dict['headers'] = HTTPMessage(shs, 0)

    def get_body(self, body_size_limit=None):
        hd = self.http_dict['headers']
        # http://en.wikipedia.org/wiki/Chunked_transfer_encoding
        c = hd.getheader("Transfer-Encoding", "").lower()
        if c == "chunked":
            for y in self._get_chunked():
                yield y
            return
        c = hd.getheader('Content-Length', None)
        # c == None means we wait for socket close, or get body_size_limit
        if c is None:
            ds = body_size_limit
        else:
            lc = int(c)
            if body_size_limit is None:
                ds = lc
            else:
                ds = min(body_size_limit, lc)
        for y in self.read_all(size=ds):
            yield y
        if isinstance(self.sep_hit, EOR) and ds is not None:
            raise self.sep_hit  # we not wait for socket close, raise it
        if c is not None and ds < lc:
            # we cut the data by body_size_limit
            hd["Content-Length"] = str(ds)
            self.http_dict['header_string'] = (self.http_dict['status_line']
                                               + "".join(hd.headers))
        self.http_dict['body'] = StringIO(self.request_data)
        self.http_dict['body'].seek(0)

    # http://en.wikipedia.org/wiki/Chunked_transfer_encoding
    def _get_chunked(self):
        body = StringIO()
        self.chunk_size = True      # fake init value, start while
        while self.chunk_size:
            for y in self.read_one_chunk(body):
                yield y
        body.seek(0)
        self.http_dict['body'] = body

    @classmethod
    def build_http_msg(cls, status, msg, headers={}):
        ret = StringIO()
        ret.write("%s\r\n" % status)
        #logging.debug("headers = %s" % str(headers))
        for h, v in headers.iteritems():
            ret.write("%s: %s\r\n" % (h, v))

        if "Content-Type" not in headers and msg:
            ret.write("Content-Type: text/html; charset=UTF-8\r\n")
        if "Content-Length" not in headers and msg:
            ret.write("Content-Length: %d\r\n" % len(msg))

        ret.write("\r\n")
        ret.write(msg)
        #logging.debug(ret.getvalue())
        return ret.getvalue()

    @classmethod
    def response_200(cls, msg, headers={}):
        return cls.build_http_msg("HTTP/1.0 200 OK", msg, headers)

    @classmethod
    def response_400(cls, msg, headers={}):
        return cls.build_http_msg("HTTP/1.0 400 Bad Request", msg, headers)

    @classmethod
    def build_get_request(cls, path, headers={}, host=None):
        if host:
            get = "GET %s HTTP/1.1" % path
            headers["Host"] = host
        else:
            get = "GET %s HTTP/1.0" % path
        return cls.build_http_msg(get, "", headers)


class ARPC(AHTTP):
    def __init__(self, rpc_addr, rpc_path, user=None, timeout=0):
        AHTTP.__init__(self, dest_addr=rpc_addr, user=user, timeout=timeout)
        self.rpc_path = rpc_path

    def call(self, func_name, arg):
        data = xmlrpclib.dumps(arg, "query_url")
        head = ("POST %s HTTP/1.0\r\n"
                "Content-Type: text/xml\r\n"
                "Content-Length: %d\r\n"
                "\r\n"
                "%s" % (self.rpc_path, len(data), data))
        for y in self.write_all(head):
            yield y
        logging.debug("sent query_rpc")
        for y in self.get_head():
            yield y
        logging.debug("get query_rpc head")
        for y in self.get_body():
            yield y
        logging.debug("get query_rpc body")
        self.rpc_return = xmlrpclib.loads(
                          self.http_dict['body'].getvalue())[0][0]
