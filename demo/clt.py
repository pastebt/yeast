
import sys
import socket

from yeast.acore import Acore
from yeast.ahttp import AHTTP


class W(Acore):
    def run(self):
        print >> sys.stderr, "I am here"
        #self.ah = AHTTP(dest_addr=("127.0.0.1", 8080), user=self)
        self.ah = AHTTP(dest_addr=("172.17.94.72", 8080), user=self)
        msg = self.ah.build_get_request("/abcd")
        print >> sys.stderr, "I am here2"
        for y in self.ah.write_all(msg):
            yield y
        print >> sys.stderr, "I am here3"
        for y in self.ah.get_head():
            yield y
        print >> sys.stderr, "I am here4"
        if self.ah.http_dict['headers'].getheader('content-length') > 0:
            for y in self.ah.get_body():
                yield y
        print >> sys.stderr, "I am here5", self.ah.http_dict['body'].getvalue()
        #-------------------------
        msg = self.ah.build_get_request("/abcd")
        for y in self.ah.write_all(msg):
            yield y
        print >> sys.stderr, "I am here6"
        for y in self.ah.get_head():
            yield y
        print >> sys.stderr, "I am here7"
        if self.ah.http_dict['headers'].getheader('content-length') > 0:
            for y in self.ah.get_body():
                yield y
        print >> sys.stderr, "I am here8", self.ah.http_dict['body'].getvalue()

w = W()
w.start()
w.loop()
