#! /usr/bin/python

import sys
from socket import socket
from heapq import heappop, heappush

from acore import Acore, Worker


class Cache(Acore):
    def __init__(self, timeout=120):
        self.timeout = timeout
        # key : (last, dat)
        self.dat_map = {}
        # (last, dat)
        self.dat_que = []

    def get(self, key):
        # query data with key
        ret = self.dat_map.get(key)
        if not ret:
            return ret
        ts = self.last_time + self.timeout
        heappush(self.dat_que, (ts, key))
        if ts > ret[0]:
            self.dat_map[key] = (ts, ret[1])
        return ret[1]

    def pop(self, key, default=None):
        return self.dat_map.pop(key, default)

    def put(self, key, data):
        # save data with key
        ts = self.last_time + self.timeout
        heappush(self.dat_que, (ts, key))
        self.dat_map[key] = (ts, data)

    def chk(self):
        # check if any data expire and clean
        while len(self.dat_que):
            ts, key = heappop(self.dat_que)
            if ts > self.last_time:
                heappush((ts, key))
                return
            last, dat = self.dat_map.pop(key, (0, None)) 
            if last > ts:
                self.dat_map[key] = (last, dat)

    def run(self):
        ts = max(self.timeout / 10, 1)
        while True:
            for y in self.sleep(ts):
                yield y
            self.chk()


class DiskCache(Cache):
    """ will save cache in disk """
    def __init__(self, filename, timeout=120):
        Cache.__init__(self, timeout)

    def save_to(self, key, value):
        pass

    def get_from(self, key):
        pass

    def close(self):
        pass


class CacheWorker(Worker):
    """ A Cache worker accept GET and PUT via tcp connect """
    cache = None
    dispatcher = None

    def run(self):
        for y in self.read_exactly(self, seps=('\n',)):
            yield y
        cmd, l = self.rdata.split(None, 1)
        size = len(l.strip())
        for y in self.read_exactly(self, size=int(self.rdata.strip())):
            yield y
        if cmd == 'GET':
            data = self.cache.get(self.rdata)
            for y in self.writeall(self.sock, "%d\n%s" % (len(data), data)):
                yield y
        elif cmd == 'PUT':
            key, value = self.rdata.split('\n', 1)
            self.cache.put(key, value)
            for y in self.writeall(self.sock, "2\nOK"):
                yield y
        elif cmd == 'STOP':
            if hasattr(selr.cache, 'close'):
                self.cache.close()
            self.dispatcher.running = False
            

def start_cache_server(addr=('', 1234), filename=''):
    """ A TCP server accept GET and PUT cache request """
    if filename:
        CacheWorker.cache = DiskCache("filename")
    else:
        CacheWorker.cache = Cache()
    l = Listern(addr, CacheWorker)
    CacheWorker.dispatcher = l
    l.start()
    l.loop()


class CacheClient(Acore):
    """
    cache protocol is:
    GET nnn\npickled string
    PUT nnn\npickled string
    """
    svr_addr = ('127.0.01', 1234)

    def __init__(self):
        Acore.__init__(self)
        self.cache_key = ''
        self.cache_data = ''
        self.running = True

    def get(self, key):
        self.post(self, "GET %d\n%s" % (len(key), key))
        yield self.WAIT_POST
        self.cache_key = key
        self.cache_data = self._data

    def put(self, key, value):
        dat = "%s\n%s" % (key, value)
        self.post(self, "PUT %d\n%s" % (len(dat), dat))
        yield self.WAIT_POST

    def stop(self):
        self.running = False
        self.post(self)

    def run_one(self):
        for y in self.writeall(self.sock, self._data):
            yield y
        self.rdata_left = ''
        for y in self.read_exactly(self, seps=('\n',)):
            yield y
        for y in self.read_exactly(self, size=int(self.rdata.strip())):
            yield y
        self.post(self, self.rdata)

    def run(self):
        self.sock = socket()
        self.sock.connect(self.svr_addr)
        while self.running:
            yield self.WAIT_POST
            if not self._data:
                continue
            for y in self.run_one():
                yield y
