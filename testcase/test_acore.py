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
        

class FAKE(acore.ARW):
    def __init__(self, data):
        acore.ARW.__init__(self, user=FAKE_USER())
        self.fileno = 4
        self.src = iter(data)

    def _read(self):
        try:
            return next(self.src)
        except StopIteration:
            self.sep_hit = acore.EOR()
            return ''


#class FAKE(ahttp.AHTTP):
#    def __init__(self, data):
#        self.src = iter(data)
#        self.rdata, self.sep = '', ''
#        self.sock = FakeSock()
#
#    def read(self, sock):
#        return next(self.src)
#
#    def get_http(self, sock, body_size_limit=0):
#        for y in self.get_http_head(sock):
#            yield y
#        for y in self.get_http_body(sock, body_size_limit):
#            yield y


class TestARW(unittest.TestCase):
    def test_read_all1(self):
        f = FAKE(("1234\r\n56",))
        ret = [y for y in f.read_all(seps=('\n',))]
        #print ret
        self.assertEqual(f.request_data, '1234\r\n')
        self.assertEqual(f._data_buf, '56')

    def test_read_all2(self):
        f = FAKE(("1234\r\n56",))
        f._data_buf = '0'
        ret = [y for y in f.read_all(seps=('\n',))]
        self.assertEqual(f.request_data, '01234\r\n')
        self.assertEqual(f._data_buf, '56')

    def test_read_all3(self):
        f = FAKE(("1234\r\n56",))
        f._data_buf = 'abc\r\naa'
        ret = [y for y in f.read_all(seps=('\n',))]
        self.assertEqual(f.request_data, 'abc\r\n')
        self.assertEqual(f._data_buf, 'aa')

    def test_read_all4(self):
        f = FAKE(("\n1234\r\n56",))
        f._data_buf = 'abc\r'
        ret = [y for y in f.read_all(seps=('\r\n',))]
        self.assertEqual(f.request_data, 'abc\r\n')
        self.assertEqual(f._data_buf, '1234\r\n56')
 
    def test_read_all5(self):
        f = FAKE(("\n1234\r\n56",))
        f._data_buf = 'abc'
        ret = [y for y in f.read_all(seps=('\r\n',))]
        self.assertEqual(f.request_data, 'abc\n1234\r\n')
        self.assertEqual(f._data_buf, '56')
 
    def test_read_all6(self):
        f = FAKE(("\r\n1234\r\n56",))
        f._data_buf = 'abc'
        ret = [y for y in f.read_all(seps=('\r\n',))]
        self.assertEqual(f.request_data, 'abc\r\n')
        self.assertEqual(f._data_buf, '1234\r\n56')
 
    def test_read_all7(self):
        # Winner's index is smaller
        f = FAKE(("\n1234\r\n56",))
        f._data_buf = 'abc'
        ret = [y for y in f.read_all(seps=('\r\n', '\n'))]
        self.assertEqual(f.request_data, 'abc\n')
        self.assertEqual(f._data_buf, '1234\r\n56')
 
    def test_read_all8(self):
        f = FAKE(("\n1234\r\n56",))
        f._data_buf = 'abc'
        ret = [y for y in f.read_all(size=2, seps=('\r\n', '\n'))]
        self.assertEqual(f.request_data, 'ab')
        self.assertEqual(f._data_buf, 'c')

    def test_read_all9(self):
        f = FAKE(("\n1234\r\n56",))
        f._data_buf = 'abc'
        ret = [y for y in f.read_all(size=4, seps=('\r\n', '\n'))]
        self.assertEqual(f.sep_hit, '\n')
        self.assertEqual(f.request_data, 'abc\n')
        self.assertEqual(f._data_buf, '1234\r\n56')
 
    def test_read_all10(self):
        f = FAKE(("\n1234\r\n56",))
        f._data_buf = 'abc'
        ret = [y for y in f.read_all(size=5, seps=('\r\n', '\n'))]
        self.assertEqual(f.sep_hit, '\n')
        self.assertEqual(f.request_data, 'abc\n')
        self.assertEqual(f._data_buf, '1234\r\n56')
 
    def test_read_all11(self):
        f = FAKE(("\r\n1234\r\n56",))
        f._data_buf = 'abc'
        ret = [y for y in f.read_all(size=4, seps=('\r\n',))]
        self.assertEqual(f.sep_hit, '')
        self.assertEqual(f.request_data, 'abc\r')
        self.assertEqual(f._data_buf, '\n1234\r\n56')

    def test_read_all12(self):
        f = FAKE(("1234\r\n56",))
        ret = [y for y in f.read_all(seps=('\r\n',))]
        self.assertEqual(f.sep_hit, '\r\n')
        self.assertEqual(f.request_data, '1234\r\n')
        ret = [y for y in f.read_all()]
        self.assertEqual(f.request_data, '56')


if __name__ == '__main__':
    #unittest.main()
    unittest.main(defaultTest='TestARW.test_read_all12')
