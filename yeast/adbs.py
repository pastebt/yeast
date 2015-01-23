import logging
import functools
import cPickle as pickle

from acore import ACall, AFunc

try:
    import MySQLdb
except ImportError:
    pass
try:
    from MySQLdb.cursors import Cursor
except ImportError:
    Cursor = None


class DBSVR(object):
    def connect(self):
        raise NotImplementedError('DBSVR.connect')

    def stop(self):
        raise NotImplementedError('DBSVR.stop')

    def pstart(self, sock):
        self.sock = sock
        self.running = True
        self.data = ''
        self.connect()
        while self.running:
            self.cmd = self.ret = None
            self.get_cmd()
            self.run_cmd()
            self.ret_res()
        self.stop()

    def start(self, sock):
        self.sock = sock
        self.running = True
        self.data = ''
        while self.running:
            self.cmd = self.ret = None
            self.get_cmd()
            try:
                self.connect()
                self.run_cmd()
            except Exception, e:
                self.ret = {'error': e, 'cmd': self.cmd}
            self.stop()
            self.ret_res()

    def get_cmd(self):
        while True:
            self.data += self.sock.recv(10000)
            if '\n' in self.data:
                break
        s, d = self.data.split('\n', 1)
        size = int(s.strip())
        while size > len(d):
            d += self.sock.recv(10000)
        self.cmd = pickle.loads(d[:size])
        self.data = d[size:]

    def run_cmd(self):
        logging.debug(str(self.cmd))
        # FIXME, verify function name
        f = getattr(self, self.cmd['name'])
        self.ret = f(*(self.cmd['args']), **(self.cmd['keywords']))

    def ret_res(self):
        data = pickle.dumps(self.ret)
        msg = "%d\n%s" % (len(data), data)
        self.sock.sendall(msg)


class RAW(object):
    def __init__(self, dat):
        self.dat = dat

    def __str__(self):
        return str(self.dat)


class MySQLSVR(DBSVR):
    _name = ''
    _user = ''
    _pass = ''
    _host = 'localhost'
    _port = 3306
    _readonly = True
    _cursor = Cursor
    _charset = 'utf8'

    def connect(self):
        self.conn = MySQLdb.connect(
                            #use_unicode=False, 
                            charset=self._charset, 
                            host=self._host,
                            user=self._user,
                            passwd=self._pass,
                            db=self._name,
                            port=self._port,
                            cursorclass=self._cursor,
                        )
        try:
            self.conn.ping(True)
        except:
            pass
        self.conn.encoders[RAW] = lambda x, d: x.dat
        self.__cur = self.conn.cursor()
        return self

    def stop(self):
        try:
            self.__cur.close()
        except Exception, e:
            logging.error('MySQLSVR.stop: ' + str(e))
        self.conn = None

    def escape(self, data):
        " escape msg by mysql "
        #if data is None:
        #    return ''
        return self.conn.literal(data)

    def _execute(self, query, param=None):
        #logging.debug(query)
        try:
            try:
                self.__cur.execute(query, param)
            except MySQLdb.OperationalError, e:
                logging.error("_execute: %s %s" % (repr(e), str(e)))
                logging.error(repr(e.args))
                #logging.error(repr(e.message))
                #if hasattr(e, 'errno') and e.errno in (2006, 2013):
                logging.warn("Try to re-connect MySQL server")
                self.stop()
                self.connect()
                self.__cur.execute(query, param)
        except:
            logging.error(query)
            raise

    def _return_list(self, _list, res):
        if not res:
            return None
        data = dict(zip([i[0] for i in self.__cur.description], res))
        return [data[l] for l in _list]

    def _return_obj(self, _class, res):
        #print 'res =', res
        if res is None:
            return None
        obj = _class()
        nm = _class.name_map()
        for n, v in zip([i[0] for i in self.__cur.description], res):
            setattr(obj, nm.get(n, n), v)
        return obj

    def _get_where(self, where):
        if isinstance(where, Where):
            return 'where ' + where.sql(self)
        else:
            return str(where)

    def _select_sql_(self, who, where):
        """
        return a list, even may only one item
        can be called as:
        select(Table.sel("col1", "col2"), WHERE_OBJ)
        select(Table.sel("col1", "col2"), "where and more string")
        select(Table, where)
        """
        if isinstance(who, tuple):
            assert len(who) == 2
            #assert isinstance(who[0], str)
            assert issubclass(who[0], Table)
            #tname, cols = who
            tname = who[0].table_name()
            cols = [who[0].get_col(col).name for col in who[1]]
            rfunc = functools.partial(self._return_list, cols)
        else:
            #assert hasattr(who, table_name)
            #assert hasattr(who, table_cols)
            #assert hasattr(who, name_map)
            assert issubclass(who, Table)
            tname = who.table_name()
            cols = [who.get_col(col).name for col in who.table_cols()]
            rfunc = functools.partial(self._return_obj, who)
        sql = "select `%s` from %s %s" % ('`, `'.join(cols), tname,
                                          self._get_where(where))
        return sql, rfunc

    def _select_(self, who, where, multi):
        sql, rfunc = self._select_sql_(who, where)
        self._execute(sql)
        if not multi:
            return rfunc(self.__cur.fetchone())
        return [rfunc(res) for res in self.__cur.fetchall()]

    def select(self, who, where):
        return self._select_(who, where, multi=True)

    def select_one(self, who, where='limit 1'):
        """return None, or first one item"""
        return self._select_(who, where, multi=False)

    def _insert_sql_(self, what, ondup):
        """can be called as:
        insert(obj.sel('col1', 'col2'))
            Col1, Col2 will update if duplicate
        insert(obj, "col1=values(col1)")
        insert(obj, "col1=2")
        """
        if isinstance(what, tuple):
            assert len(what) == 2
            assert isinstance(what[0], Table)
            obj, upcols = what
            cols = obj.table_cols()
            od = ", ".join(["`%s`=values(`%s`)" % (obj.get_col(col).name,
                            obj.get_col(col).name) for col in upcols])
        else:
            #assert hasattr(what, table_name)
            assert isinstance(what, Table)
            assert hasattr(what, 'table_cols')
            #assert hasattr(what, name_map)
            obj, cols = what, what.table_cols()
            od = ondup
        cs = ", ".join(["`%s`" % obj.get_col(col).name for col in cols])
        vs = ", ".join([self.escape(getattr(obj, col)) for col in cols])
        sql = "insert into %s (%s) values (%s)" % (obj.table_name(), cs, vs)
        if od:
            sql += " on duplicate key update " + od
        return sql

    def insert(self, what, ondup=None):
        self._execute(self._insert_sql_(what, ondup))

    def delete(self, who, where):
        """can be called like:
        delete(Table, Where_and_more_Obj)
        delete(Table, 'Where_and_more_str')
        """
        sql = "delete from %s %s" % (who.table_name(), self._get_where(where))
        self._execute(sql)

    def _update_sql_(self, who, where):
        """can be called like:
        update(obj.sel('col1', 'col2'), Where_and_More_Obj)
        update(obj.sel('col1', 'col2'), 'where_and_more_str')
        """
        assert isinstance(who, tuple)
        assert len(who) == 2
        assert isinstance(who[0], Table)
        obj, cols = who
        sql = "update %s set " % obj.table_name()
        def setv(o, col):
            return "`%s`=%s" % (o.get_col(col).name,
                                self.escape(getattr(o, col)))
        sql += ", ".join([setv(obj, col) for col in cols])
        sql += " "
        sql += self._get_where(where)
        return sql

    def update(self, who, where):
        self._execute(self._update_sql_(who, where))

    def query(self, sql, param=None):
        self._execute(sql, param)
        if not sql[:7].lower() != 'select':
            return None
        return self.__cur.fetchall()


class CMPMixIn(object):
    def __gt__(self, obj):
        return Where(self, ">", obj)

    def __lt__(self, obj):
        return Where(self, "<", obj)

    def __ge__(self, obj):
        return Where(self, ">=", obj)

    def __le__(self, obj):
        return Where(self, "<=", obj)

    def __eq__(self, obj):
        return Where(self, "=", obj)

    def __ne__(self, obj):
        return Where(self, "<>", obj)


class Where(CMPMixIn):
    def __init__(self, left=None, act='', right=None, one=True):
        self.left, self.right = left, right
        self.act, self.one = act, one

    def sql(self, db):
        l, r = self.left, self.right

        if hasattr(self.left, 'sql'):
            l = self.left.sql(db)
        elif self.left is None:
            l = ''
        else:
            l = str(db.escape(self.left))

        if hasattr(self.right, 'sql'):
            r = self.right.sql(db)
        elif self.right is None:
            r = ''
        else:
            r = str(db.escape(self.right))

        ret = ' '.join([x for x in (l, self.act, r) if x])
        if self.one:
            return ret
        return '(' + ret + ')'

    def __add__(self, s):
        # one is True
        return Where(left=self, right=RAW(s))

    def AND(self, obj):
        if isinstance(obj, str):
            return Where(self, 'and', RAW(obj), False)
        return Where(self, 'and', obj, False)

    def OR(self, obj):
        if isinstance(obj, str):
            return Where(self, 'or', RAW(obj), False)
        return Where(self, 'or', obj, False)


class Column(CMPMixIn):
    def __init__(self, default=None, name=None, autoid=False):
        self.default = default
        self.name = name
        self.autoid = autoid

    def BETWEEN(self, a, b):
        #return Where(self.name, 'between', a).AND(b)
        #return Where("`%s`" % self.name, 'between', RAW("'%s' and '%s'" % (a, b)))
        #return Where("`%s`" % self.name, 'between', a).AND(Where(left='', right=b))
        #return Where(self, 'between', a).AND(Where(left='', right=b))
        return Where(self, 'between', a).AND(Where(right=b))

    def LIKE(self, t):
        return Where(self, 'like', t, False)

    def sql(self, db):
        return "`%s`" % self.name


class TableMeta(type):
    def __new__(mcs, name, bases, dicti):
        # list of table coumn
        #cl = dicti.setdefault('_column_list', [])
        cl = dicti['_column_list'] = []
        # if class property name is diff from column name
        # here is table column name mape to class property
        #nm = dicti.setdefault('_name_map', {})
        nm = dicti['_name_map'] = {}
        for d, v in dicti.items():
            if isinstance(v, Column):
                #v.table_name = dicti['_name']
                if v.name is None:
                    v.name = d
                elif v.name != d:
                    nm[v.name] = d
                cl.append(d)
        dicti['_column_set'] = set(cl)
        return type.__new__(mcs, name, bases, dicti)


class Table(object):
    __metaclass__ = TableMeta
    _name = ''
    # follow columns definiation
    #id = Column(0, autoid=True)

    @classmethod
    def table_name(cls):
        return cls._name

    @classmethod
    def table_cols(cls):
        return cls._column_list

    @classmethod
    def name_map(cls):
        return cls._name_map

    @classmethod
    def sel(cls, *args):
        return (cls, args)

    @classmethod
    def get_col(cls, name):
        return getattr(cls, name)

    def _sel(self, *args):
        return (self, args)

    def __init__(self, **kws):
        self.sel = self._sel
        for k, v in kws.items():
            if k not in self._column_set:
                raise TypeError("got an unexpected keyword argument '%s'" % k)
            setattr(self, k, v)
        for n in (self._column_set - set(kws.keys())):
            setattr(self, n, getattr(self.__class__, n).default)

    def __getstate__(self):
        # for pickle, skip instance method
        return dict([(k, v) for k, v in self.__dict__.iteritems()
                            if k in self._column_set])


class DBClt(object):
    def __init__(self):
        self.afunc = None

    def connect(self, dbsvr):
        self.dbsvr = dbsvr
        self.db_result = None
        self.afunc = AFunc(self.dbsvr.start)
        self.afunc.start()
        return self

    def _call_(self, func_name, *args, **keywords):
        msg = pickle.dumps({'name': func_name, 'args': args,
                            'keywords': keywords})
        for y in self.afunc.call(msg):
            yield y
        self.db_result = pickle.loads(self.afunc.func_ret)

    def __getattr__(self, name):
        return functools.partial(self._call_, name)
