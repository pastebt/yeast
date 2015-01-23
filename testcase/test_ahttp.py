import sys
import unittest
from StringIO import StringIO

sys.path.append('../yeast')
import ahttp
import acore


class FAKE_USER(acore.Acore):
    def read_all(self, arw, size=0, seps=()):
        for y in arw.aread(size, seps):
            yield y
        

#class FakeSock(object):
#    def fileno(self):
#        return 4


class FAKE(ahttp.AHTTP):
    def __init__(self, data):
        acore.ARW.__init__(self, user=FAKE_USER())
        self.fileno = 4
        self.src = iter(data)

    def get_http(self, body_size_limit=None):
        for y in self.get_head():
            yield y
        for y in self.get_body(body_size_limit):
            yield y

    def _read(self):
        try:
            return next(self.src)
        except StopIteration:
            self.sep_hit = acore.EOR()
            #print "StopIteration", repr(self.sep_hit)
            return ''


class TestAhttp(unittest.TestCase):
    def test_get_head1(self):
        f = FAKE("GET / HTTP/1.1\r\nHost: url.host\r\n\r\n")
        ret = [y for y in f.get_head()]
        self.assertEqual(f.sep_hit, '\n\r\n')
        self.assertEqual(f.http_dict['action'], 'GET')
        self.assertEqual(f.http_dict['path'], '/')
        self.assertEqual(f.http_dict['version'], 'HTTP/1.1')
        self.assertEqual(f.http_dict['headers'].get('host'), 'url.host')

    def test_get_head2(self):
        f = FAKE(("GET / HTTP/1.1\r",
                  "\nHost: url.host\r\n\r\n"))
        ret = [y for y in f.get_head()]
        self.assertEqual(f.sep_hit, '\n\r\n')
        self.assertEqual(f.http_dict['action'], 'GET')
        self.assertEqual(f.http_dict['path'], '/')
        self.assertEqual(f.http_dict['version'], 'HTTP/1.1')
        self.assertEqual(f.http_dict['headers'].get('host'), 'url.host')

    def test_get_head3(self):
        f = FAKE(("GET / HTTP/1.1",
                  "\nHost: url.host\n\n"))
        ret = [y for y in f.get_head()]
        self.assertEqual(f.sep_hit, '\n\n')
        self.assertEqual(f.http_dict['action'], 'GET')
        self.assertEqual(f.http_dict['path'], '/')
        self.assertEqual(f.http_dict['version'], 'HTTP/1.1')
        self.assertEqual(f.http_dict['headers'].get('host'), 'url.host')

    def test_get_head4(self):
        f = FAKE(("HTTP/1.1 200 this is good\r",
                  "\nHost: url.host\r\n",
                  "Content-length:5\r\n\r\n12345"))
        ret = [y for y in f.get_head()]
        self.assertEqual(f.sep_hit, '\n\r\n')
        self.assertEqual(f.http_dict['version'], 'HTTP/1.1')
        self.assertEqual(f.http_dict['status'], '200')
        self.assertEqual(f.http_dict['reason'], 'this is good')
        h = f.http_dict['headers']
        self.assertEqual(h.get('host'), 'url.host')
        self.assertEqual(h.get('content-length'), '5')

    def test_get_head5(self):
        f = FAKE("AAA AA\r\nHost: url.host\r\n\r\n")
        #with self.assertRaises(Exception) as e:
        #    ret = [y for y in f.get_head()]
        #self.assertTrue(str(e), "Miss status line 'AAA AA'")
        try:
            ret = [y for y in f.get_head()]
        except Exception, e:
            self.assertTrue(str(e), "Miss status line 'AAA AA'")
        else:
            self.assertTrue(False)

    def test_get_head6(self):
        f = FAKE("AA A AA\r\nHost: url.host\r\n\r\n")
        #with self.assertRaises(Exception) as e:
        #    ret = [y for y in f.get_head()]
        #self.assertTrue(str(e), "Bad status line 'AA A AA'")
        try:
            ret = [y for y in f.get_head()]
        except Exception, e:
            self.assertTrue(str(e), "Bad status line 'AA A AA'")
        else:
            self.assertTrue(False)

    def test_get_http1(self):
        f = FAKE(("HTTP/1.1 200 this is good\r",
                  "\nHost: url.host\r\n",
                  "Content-length:5\r\n\r\n12345"))
        ret = [y for y in f.get_head()]
        self.assertEqual(f.sep_hit, '\n\r\n')
        self.assertEqual(f.http_dict['version'], 'HTTP/1.1')
        self.assertEqual(f.http_dict['status'], '200')
        self.assertEqual(f.http_dict['reason'], 'this is good')
        h = f.http_dict['headers']
        self.assertEqual(h.get('host'), 'url.host')
        self.assertEqual(h.get('content-length'), '5')
        self.assertEqual(f._data_buf, '12345')
        ret = [y for y in f.get_body()]
        self.assertEqual(f.http_dict['body'].getvalue(), '12345')

    def test_get_http2(self):
        f = FAKE(("HTTP/1.1 200 this is good\r",
                  "\nHost: url.host\r\n",
                  "Content-length:5\r\n\r\n12345"))
        ret = [y for y in f.get_http()]
        self.assertEqual(f.http_dict['body'].getvalue(), '12345')

    def test_get_http3(self):
        f = FAKE(("HTTP/1.1 200 this is good\r\n\r\n12345"))
        ret = [y for y in f.get_http()]
        self.assertEqual(f.http_dict['body'].getvalue(), '12345')
        #print f.http_dict['header_string']

    def test_get_http4(self):
        f = FAKE(("HTTP/1.1 200 this is good\r\n",
                  "Host: url.host\r\n",
                  "Content-length: 5\r\n\r\n12345"))
        ret = [y for y in f.get_http(4)]
        self.assertEqual(f.http_dict['body'].getvalue(), '1234')
        #print f.http_dict['header_string']

    def test_get_http5(self):
        f = FAKE(("HTTP/1.1 200 this is good\r\n",
                  "Host: url.host\r\n",
                  "Transfer-Encoding: Chunked\r\n\r\n",
                  "2\r\n12\r\n3;aa\r\n345\r\n0\r\n"))
        ret = [y for y in f.get_http()]
        self.assertEqual(f.http_dict['body'].getvalue(), '12345')
        #print f.http_dict['header_string']


if __name__ == '__main__':
    #unittest.main()
    unittest.main(defaultTest='TestAhttp.test_get_head6')
