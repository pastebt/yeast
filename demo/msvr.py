#! /usr/bin/python

import sys
import socket
from time import sleep
from subprocess import Popen

from yeast import asvr
from yeast import acore


def run(fd):
    l = acore.Listener(fd=fd, worker=asvr.WsgiHandler)
    asvr.WsgiHandler.app = staticmethod(asvr.WsgiApp)
    asvr.WsgiHandler.env['SERVER_PORT'] = '8080'
    l.start()
    l.loop()


def start(proc_num):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('', 8080))
    sock.setblocking(0)
    sock.listen(500)
    for i in range(proc_num):
        p = Popen((sys.argv[0], str(sock.fileno())))
    while True:
        sleep(10)


def main():
    if len(sys.argv) == 2:
        run(int(sys.argv[1]))
    else:
        start(2)


main()
