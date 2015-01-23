import os
import sys
import time
import fcntl
import socket
import select
import logging
import functools
from errno import EINTR, EISCONN, ETIMEDOUT, EAGAIN


class TimeOut(Exception):
    "exception for timeout"


class PollError(Exception):
    "exception for socket closed"


class EOR(Exception):
    "End Of Read"


class SocketClosed(EOR):
    "exception for socket closed"


class Aact(object):
    def __init__(self, num):
        self.num = num

    def __eq__(self, other):
        return (isinstance(other, Aact) and self.num == other.num) or (
                isinstance(other, int) and self.num == other)

    def __rand__(self, other):
        return self.__and__(other)

    def __and__(self, other):
        if isinstance(other, Aact):
            return self.num & other.num
        elif isinstance(other, int):
            return self.num & other
        # 'return NotImplemented' will try other.__rand__
        return NotImplemented


class IsUserFunc(object):
    code2func = {}

    def __call__(self, func):
        self.code2func[func.func_code] = func
        return func

    @classmethod
    def get_func_from_code(cls, code):
        return cls.code2func.get(code)



class Acore(object):
    W = Aact(select.POLLOUT)
    R = Aact(select.POLLIN)

    WAIT_SLEEP = Aact(0)
    WAIT_POST = Aact(-1)

    poller = select.poll()
    fdmap = {}              # fp mapper
    postoffice = []
    running = True
    last_time = time.time()

    def __init__(self):
        self.started = False
        self.tocnt = 0

    def start(self, dat=None):
        if self.started:
            raise Exception("already started")
        self.started = True
        self._data = dat    # init data for run
        self._wait = 0      # what is your waiting for (W, R, WAIT_POST)
        self._back = 0      # what is back from poll, (W, R, E, I, H)
        self._iter = self.run()
        self.next()

    #@IsUserFunc()
    def next(self, back=0):
        self._back = back
        try:
            self._wait = self._iter.next()
            if self._back == None:
                self._back = self._wait
        except StopIteration:
            pass

    @classmethod
    def post(cls, obj, dat=None):
        cls.postoffice.append((obj, dat))

    def stop(self):
        Acore.running = False

    def reg(self, arw, act):
        """
        any moment, Acore object can have one arw
        but can use different arw different time """
        self.arw, fd = arw, arw.fileno
        flags = select.POLLERR | select.POLLHUP | select.POLLNVAL
        if act == self.W:
            flags |= select.POLLOUT
        if act == self.R:
            flags |= select.POLLIN | select.POLLPRI
        self.poller.register(fd, flags)
        self.fdmap[fd] = self

    def unreg(self, arw):
        assert arw == self.arw, "arw miss match: arw=%s, self.arw=%s" % (
                                 arw, self.arw)
        fd = arw.fileno
        self.poller.unregister(fd)
        del self.fdmap[fd]
        del self.arw    # have to clean it, for save timeout

    def run(self):
        raise NotImplementedError('Acore.run not implemented')

    def check_it(self, arw):
        # check timeout and error
        if self.tocnt < 0 or arw.tocnt < 0:
            raise TimeOut()
        if self._back == self._wait:
            return
        if self._wait == self.R and self._back == select.POLLPRI:
            return
        msg = "_wait = %s, _back = %s, arw=%s" % (
               self._wait, self._back, str(arw))
        if self._wait & self._back > 0:
            return
        if self._back & select.POLLHUP:
            #raise PollError("Hung up: " + msg)
            arw.sep_hit = EOR()
            return
        logging.warn(msg)
        if self._back & select.POLLNVAL:
            raise PollError("Invalid request: descriptor not open: " + msg)
        if self._back & select.POLLERR:
            raise PollError("Error condition of some sort: " + msg)
        raise PollError(msg)

    def write_all(self, arw, msg):
        #print >> sys.stderr, "acore.write_all"
        self.reg(arw, self.W)
        try:
            for y in arw.awrite(msg):
                yield y
                self.check_it(arw)
        finally:
            self.unreg(arw)

    def read_all(self, arw, size=0, seps=()):
        self.reg(arw, self.R)
        try:
            for y in arw.aread(size, seps):
                yield y
                self.check_it(arw)
            self.rdata = arw.request_data
        finally:
            self.unreg(arw)

    def sleep(self, sec):
        self.tocnt = time.time() + sec
        self.fdmap[-id(self)] = self
        while self.tocnt > 0:
            yield 0
        del self.fdmap[-id(self)]

    @classmethod
    def loop(cls):
        cls.last_time = time.time()
        while cls.running:
            if len(cls.fdmap) < 1 and len(cls.postoffice) < 1:
                break
            cls._one_loop()

    @classmethod
    def _one_loop(cls):
        if cls.postoffice:
            pt = 0
        else:
            pt = 1000
        try:
            live = cls.poller.poll(pt)  # ms
        except select.error, err:
            if err[0] != EINTR:
                raise
            return
        # process something is ready
        for f, a in live:
            n = cls.fdmap.get(f, None)
            if not n:
                logging.error("Can not find f %s in fdmap" % f)
            else:
                n.next(a)
        # check if someone is timeout
        tt = time.time()
        if tt > cls.last_time + 1:
            cls.last_time = tt
            cls._check_timeout(tt)
        # send notification
        # because cls.postoffice may has new entry when running next
        # so we use a copy here
        po = cls.postoffice[:]
        del cls.postoffice[:]
        for obj, dat in po:
            if obj._wait == cls.WAIT_POST:
                obj.next(dat)   # if waiting for IO, should not call here

    @classmethod
    def _check_timeout(cls, tt):
        # check if someone is timeout
        for obj in cls.fdmap.values():
            if 0 < obj.tocnt < tt:
                obj.tocnt = -1
                obj.next()
            elif hasattr(obj, 'arw') and 0 < obj.arw.tocnt < tt:
                # any moment, obj only can have one arw
                obj.arw.tocnt = -1
                obj.next()


class AIO(object):
    def __init__(self, user=None):
        self.tocnt = 0
        self.bound_user = None
        if user is not None:
            self.bind_user(user)

    def bind_user(self, user):
        if not isinstance(user, Acore):
            raise ValueError("user should be a Acore")
        self.bound_user = user
        #self.read_all = functools.partial(user.read_all, self)
        #self.write_all = functools.partial(user.write_all, self)

    def unbind_user(self):
        """
        try to unbind user, this will make read_all/write_all try
        to find user by search frame bottom to top, then bind user
        """
        self.bound_user = None
        #if hasattr(self, 'user'):
        #    del self.user
        #if hasattr(self, 'read_all'):
        #    del self.read_all
        #if hasattr(self, 'write_all'):
        #    del self.write_all

    def find_user(self):
        fm = sys._getframe(3)
        while fm:
            #if IsUserFunc.get_func_from_code(fm.f_code):
            if fm.f_code is Acore.next.func_code:
                #if func and 'self' in fm.f_locals:
                break
            fm = fm.f_back
        self.bind_user(fm.f_locals.get('self'))


class TICKER(Acore):
    def __init__(self, receiver_list):
        Acore.__init__(self)
        self.rev_list = receiver_list

    def run(self):
        while self.running:
            for y in self.sleep(1):
                yield y
            #print self.owner.waiting
            for r in self.rev_list:
                self.post(r)


class Aqueue(object):
    """
    in process, size unlimited
    This version can support Multiple queue instance in one process
    In order support this, we need a Getter instance to handle different user
    But can not return data via Getter or Aqueue instance, so we return via
    yield, user should check by isinstance(y, Aact) to get return
    Or use get_getter
    """

    def __init__(self):
        self.task_queue = []
        self.waiting = set()
        self.ticker = TICKER(self.waiting)
        self.ticker.start()

    class Getter(AIO):
        def __init__(self, task, wait, user=None):
            AIO.__init__(self, user)
            self.task_queue = task
            self.waiting = wait

        def get(self, timeout=0):
            if self.bound_user is None:
                self.find_user()
            if timeout > 0:
                self.tocnt = time.time() + timeout
            self.waiting.add(self.bound_user)
            print self.waiting, self.task_queue, self.bound_user.running, self.tocnt
            self.data = ''
            while self.bound_user.running:
                if self.task_queue:
                    self.data = self.task_queue.pop(0)
                    self.waiting.remove(self.bound_user)
                    break
                if time.time() > self.tocnt > 0:
                    self.waiting.remove(self.bound_user)
                    break
                yield self.bound_user.WAIT_POST
                print "resume from WAIT_POST: %s" % (self.tocnt,)

    def get(self, timeout=0, user=None):
        getter = self.Getter(self.task_queue, self.waiting, user)
        for y in getter.get(timeout):
            yield y
        yield getter.data

    def get_getter(self):
        return self.Getter(self.task_queue, self.waiting)

    def put(self, dat):
        self.task_queue.append(dat)
        for u in self.waiting:
            u.post(u)


class ARW(AIO):
    """ Async Read Write"""
    W = Acore.W
    R = Acore.R

    def __init__(self, user=None, timeout=0):
        AIO.__init__(self, user)
        self.fileno = 0
        self.timeout = timeout
        self.request_data = ''  # caller asked data
        self._data_buf = ''     # buffer
        self.sep_hit = ''       # hit which seperator

    def read_all(self, size=None, seps=()):
        if self.bound_user is None:
            self.find_user()
        for y in self.bound_user.read_all(self, size, seps):
            yield y

    def write_all(self, msg):
        #print >> sys.stderr, "arw.write_all"
        if self.bound_user is None:
            self.find_user()
        for y in self.bound_user.write_all(self, msg):
            yield y

    def set_timeout(self, to):
        " set new timeout, return old timeout "
        ot, self.timeout = self.timeout, to
        return ot

    def _set_tocnt(self):
        if self.timeout > 0:
            self.tocnt = time.time() + self.timeout
        else:
            self.tocnt = 0

    def _write(self, msg):
        del msg
        raise NotImplementedError("ARW._write")

    def awrite(self, msg):
        self._set_tocnt()
        while msg:
            yield self.W
            if self.tocnt < 0:
                raise TimeOut(str(self))
            n = self._write(msg)
            #print 'ARW.write:', n
            msg = msg[n:]
            #print 'ARW.write:', msg

    def close(self):
        pass

    def _read(self):
        raise NotImplementedError("ARW._read")

    def aread(self, size=None, seps=()):
        self.sep_hit = ''
        self._set_tocnt()
        #print "aread1"
        while not self._got_request(size, seps):
            #print 'yield self.R'
            yield self.R
            if self.tocnt < 0:
                raise TimeOut(str(self))
            self._data_buf += self._read()
        #print "aread2"
        l = size
        if isinstance(self.sep_hit, EOR):
            l = len(self._data_buf)
        elif self.sep_hit:
            l = self._data_buf.find(self.sep_hit) + len(self.sep_hit)
        if l and size:
            l = min(l, size)
        #print "set request_data", l
        self.request_data = self._data_buf[:l]
        self._data_buf = self._data_buf[l:]

    def raw_read(self):
        self.sep_hit = ''
        self._data_buf += self._read()
        self.request_data, self._data_buf = self._data_buf, ''

    def _got_request(self, size, seps):
        if isinstance(self.sep_hit, EOR) or size == 0:
            return True
        l = len(self._data_buf)
        if l == 0:
            return False
        if isinstance(size, int) and size < l:
            l = size
        for sep in seps:
            if 0 <= self._data_buf.find(sep) <= l - len(sep):
                self.sep_hit = sep
        #print "sep_hit:", repr(self.sep_hit), "l:", l, "size:", size
        return self.sep_hit != '' or l == size


class ACUDP(ARW):
    " Async Client UDP "

    def __init__(self, sock=None, dest_addr=None, user=None, timeout=0):
        ARW.__init__(self, user, timeout)
        if sock is None:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        else:
            self.sock = sock
        self.sock.setblocking(0)
        self.dest_addr = dest_addr
        self.fileno = self.sock.fileno()

    def _read(self):
        self.sep_hit = EOR()
        data, self.remote_udp_addr = self.sock.recvfrom(409600)
        return data

    def _write(self, msg):
        return self.sock.sendto(msg, self.dest_addr)

    def __str__(self):
        return "ACUDP: " + str(self.dest_addr)


class ACTCP(ARW):
    " Async Client TCP "

    def __init__(self, sock=None, dest_addr=None, user=None, timeout=0):
        ARW.__init__(self, user, timeout)
        if sock is None:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        else:
            self.sock = sock
        self.sock.setblocking(0)
        self.dest_addr = dest_addr
        if dest_addr is not None:
            self.sock.connect_ex(dest_addr)
        self.fileno = self.sock.fileno()

    def _read(self):
        dat = self.sock.recv(409600)
        if not dat:
            self.sep_hit = EOR()
        return dat

    def _write(self, msg):
        return self.sock.send(msg)

    def __str__(self):
        return "ACTCP: " + str(self.dest_addr)


class AFILE(ARW):
    def __init__(self, opened_file=None, user=None, timeout=0, fd=None):
        ARW.__init__(self, user, timeout)
        self.ofile = opened_file
        if hasattr(self.ofile, 'fileno'):
            self.fileno = self.ofile.fileno()
        else:
            self.fileno = fd
        fl = fcntl.fcntl(self.fileno, fcntl.F_GETFL)
        fl |= os.O_NONBLOCK
        fcntl.fcntl(self.fileno, fcntl.F_SETFL, fl)

    def _read(self):
        dat = os.read(self.fileno, 4096000)
        #dat = self.ofile.read()
        if dat == '':
            #print "AFILE.EOR"
            self.sep_hit = EOR()
        return dat

    def _write(self, msg):
        return os.write(self.fileno, msg)
        #return self.ofile.write(msg)

    def __str__(self):
        if hasattr(self.ofile, 'name'):
            return "AFILE: " + self.ofile.name
        return "AFILE: " + str(self.fileno)


class ACall(ACTCP):
    """ socket can get from socketfromfd, so we split this from AFunc """

    def __init__(self, sock, user=None, timeout=0):
        #print sock
        assert not isinstance(sock, socket.socket), "sock must be a socket"
        ACTCP.__init__(self, sock, user=user, timeout=timeout)

    def call(self, cmd):
        self.func_ret = ''
        msg = "%d\n%s" % (len(cmd), cmd)
        for y in self.write_all(msg):
            yield y
       # print "ACall, call write_all done"
        for y in self.read_all(seps=('\n',)):
            yield y
        l = int(self.request_data)
        if l == 0:
            self.request_data = ''
            return
        for y in self.read_all(size=l):
            yield y
        self.func_ret = self.request_data


class AFunc(ACall):
    """ async run a function in subprocess, function take one connected
        socket as arg will be used to communicate with parent
    """

    def __init__(self, func, user=None, timeout=0):
        assert hasattr(func, '__call__')
        #assert user is not None
        self.func = func
        p2c, self.c2p = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
        ACall.__init__(self, p2c, user=user, timeout=timeout)

    def start(self):
        pid = os.fork()
        if pid:
            return
        self.func(self.c2p)
        sys.exit(0)


class Worker(Acore):
    def __init__(self, sock, addr):
        self.addr = addr
        self.sock = sock
        Acore.__init__(self)

    def run(self):
        raise NotImplementedError('Worker.run')


class Listener(Acore):
    def __init__(self, addr=("", 8080), worker=Worker, fd=None):
        self.fd = fd
        self.addr = addr
        self.work_cls = worker
        self._pass11 = bool(self.fd)
        Acore.__init__(self)

    def _act(self):
        # accept it
        try:
            s, a = self.sock.accept()
        except socket.error, e:
            if e[0] == 11 and self._pass11:
                # forked will cause this issue, it is OK to pass
                # (11, 'Resource temporarily unavailable')
                return
            raise
        #s, a = self.sock.accept()
        s.setblocking(0)
        logging.info("get connect from %s", a)
        self.work_cls(s, a).start()

    def get_sock(self):
        if self.fd:
            self.sock = socket.fromfd(self.fd, socket.AF_INET,
                                      socket.SOCK_STREAM)
        else:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def act_sock(self):
        if not self.fd and self.addr:
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.bind(self.addr)
        self.sock.setblocking(0)
        arw = ARW()
        arw.fileno = self.sock.fileno()
        self.reg(arw, self.R)
        if not self.fd:
            self.sock.listen(500)

    def bind(self):
        self.get_sock()
        self.act_sock()

    def run(self):
        self.bind()
        while self.running:
            yield self.R
            self._act()
