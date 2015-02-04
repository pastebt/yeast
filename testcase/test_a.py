#! /usr/bin/python

import os
import sys
import signal
import select
from errno import EINTR


class A(object):
    time_cnt = 0

    @classmethod
    def tout(cls, *arg):
        #print >> sys.stderr, "tout"
        cls.time_cnt += 1
        signal.alarm(1)


p = select.poll()
p.register(sys.stdin, select.POLLIN)
signal.signal(signal.SIGALRM, A.tout)
signal.alarm(1)
while True:
    try:
        print p.poll()
    except select.error, e:
        # select.error: (4, 'Interrupted system call')
        if e[0] == EINTR:
            pass
    print A.time_cnt
