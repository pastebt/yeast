#! /usr/bin/python

import sys

from yeast.acore import Listener, Worker
from yeast.ahttp import  AHTTP


class W(Worker):
    def run(self):
        #self.ah = AHTTP(self.sock, user=self)
        self.ah = AHTTP(self.sock)
        for y in self.ah.get_head():
            yield y
        if self.ah.http_dict['headers'].getheader('content-length') > 0:
            for y in self.ah.get_body():
                yield y
        #msg = self.ah.response_200("ididiid", {"Keep-Alive": "True"})
        msg = self.ah.response_200("ididiid", {"Connection": "keep-alive"})
        #msg = self.ah.build_http_msg("HTTP/1.1 200 OK", "ididiid")
        #, {"Keep-Alive": "True"})
        for y in self.ah.write_all(msg):
            yield y
        print >> sys.stderr, "get one"
        for y in self.ah.get_head():
            yield y
        if self.ah.http_dict['headers'].getheader('content-length') > 0:
            for y in self.ah.get_body():
                yield y
        msg = self.ah.response_200("huhuu")
        for y in self.ah.write_all(msg):
            yield y
        self.sock.close()


l = Listener(addr=('', 8080), worker=W)
l.start()
l.loop()
