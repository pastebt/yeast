import sys
import unittest

sys.path.append('../yeast')

import adbs


class FSVR(object):
    def literal(self, msg):
        if isinstance(msg, str):
            return "'%s'" % msg
        return str(msg)


class FakeDB(adbs.MySQLSVR):
    def connect(self):
        self.conn = FSVR()

    def stop(self):
        pass


class T1(adbs.Table):
    _name = 't1'

    uid = adbs.Column(0, autoid=True)
    name = adbs.Column('')
    Pass = adbs.Column('1234', name='pass')


class T2(adbs.Table):
    _name = 't2'
    pwd = adbs.Column('1234', name='passwd')


class TestWhere(unittest.TestCase):
    def test_sql1(self):
        db = FakeDB()
        db.connect()

        w = T1.uid > 1
        self.assertEqual(w.sql(db), '`uid` > 1')
        w = T1.uid < 1
        self.assertEqual(w.sql(db), '`uid` < 1')
        w = T1.uid != 1
        self.assertEqual(w.sql(db), '`uid` <> 1')
        w = T1.uid == 1
        self.assertEqual(w.sql(db), '`uid` = 1')
        w = T1.uid > 'a'
        self.assertEqual(w.sql(db), "`uid` > 'a'")
        w = T1.uid < 'a'
        self.assertEqual(w.sql(db), "`uid` < 'a'")
        w = T1.uid != 'a'
        self.assertEqual(w.sql(db), "`uid` <> 'a'")
        w = T1.uid == 'a'
        self.assertEqual(w.sql(db), "`uid` = 'a'")

    def test_sql2(self):
        db = FakeDB()
        db.connect()
        w = adbs.Where("col1", ">", 1)
        self.assertEqual(w.sql(db), "'col1' > 1")
        w = adbs.Where("col1", ">", '1')
        self.assertEqual(w.sql(db), "'col1' > '1'")
        w = adbs.Where("col1", " >  ", 1)
        self.assertEqual(w.sql(db), "'col1'  >   1")
        w = adbs.Where("col1", ">", 1, False)
        self.assertEqual(w.sql(db), "('col1' > 1)")
        w = adbs.Where("col1", ">", "1")
        self.assertEqual(w.sql(db), "'col1' > '1'")
        w = adbs.Where("col1", ">", '1', False)
        self.assertEqual(w.sql(db), "('col1' > '1')")

    def test_and1(self):
        db = FakeDB()
        db.connect()
        w = (T1.uid > 1).AND(T1.name != 'a')
        self.assertEqual(w.sql(db), "(`uid` > 1 and `name` <> 'a')")
        w = (T1.uid > 1).AND("col2 >  1")
        self.assertEqual(w.sql(db), "(`uid` > 1 and col2 >  1)")
        w = (T1.uid > 1).AND("col2 >  1").AND(T1.name == 'a')
        self.assertEqual(w.sql(db),
                         "((`uid` > 1 and col2 >  1) and `name` = 'a')")

    def test_and2(self):
        db = FakeDB()
        db.connect()
        w = adbs.Where("col1", ">", 1).AND(adbs.Where("col2", ">", 1))
        self.assertEqual(w.sql(db), "('col1' > 1 and 'col2' > 1)")
        w = adbs.Where("col1", ">", 1).AND("col2 >  1")
        self.assertEqual(w.sql(db), "('col1' > 1 and col2 >  1)")
        w = adbs.Where("col1>1").AND("col2 >  1")
        self.assertEqual(w.sql(db), "('col1>1' and col2 >  1)")

    def test_or1(self):
        db = FakeDB()
        db.connect()
        w = (T1.uid > 1).OR(T1.name == 'a')
        self.assertEqual(w.sql(db), "(`uid` > 1 or `name` = 'a')")
        w = (T1.uid > 1).OR("col2 >  1")
        self.assertEqual(w.sql(db), "(`uid` > 1 or col2 >  1)")
        w = (T1.uid > 1).OR("col2 >  1").OR(T1.name == 'a')
        self.assertEqual(w.sql(db),
                         "((`uid` > 1 or col2 >  1) or `name` = 'a')")

    def test_or2(self):
        db = FakeDB()
        db.connect()
        w = adbs.Where("col1", ">", 1).OR(adbs.Where("col2", ">", 1))
        self.assertEqual(w.sql(db), "('col1' > 1 or 'col2' > 1)")
        w = adbs.Where("col1", ">", 1).OR("col2 >  1")
        self.assertEqual(w.sql(db), "('col1' > 1 or col2 >  1)")
        w = adbs.Where("col1>1").OR("col2 >  1")
        self.assertEqual(w.sql(db), "('col1>1' or col2 >  1)")

    def test_add1(self):
        db = FakeDB()
        db.connect()

        w = (T1.uid > 1) + "limit 1"
        self.assertEqual(w.sql(db), "`uid` > 1 limit 1")
        w = adbs.Where("col1", ">", 1) + "limit 1"
        self.assertEqual(w.sql(db), "'col1' > 1 limit 1")

        w = (T1.uid > 'a') + "limit 1"
        self.assertEqual(w.sql(db), "`uid` > 'a' limit 1")
        w = adbs.Where("col1", ">", 'a') + "limit 1"
        self.assertEqual(w.sql(db), "'col1' > 'a' limit 1")


class TestColumn(unittest.TestCase):
    def test_cmp1(self):
        db = FakeDB()
        db.connect()
        w = T1.uid > 1
        self.assertTrue(isinstance(w, adbs.Where))
        self.assertEqual(w.sql(db), '`uid` > 1')

    def test_cmp2(self):
        db = FakeDB()
        db.connect()
        w = T2.pwd > ""
        self.assertTrue(isinstance(w, adbs.Where))
        self.assertEqual(w.sql(db), "`passwd` > ''")

    def test_like1(self):
        db = FakeDB()
        db.connect()
        w = T1.name.LIKE("abc%")
        self.assertTrue(isinstance(w, adbs.Where))
        self.assertEqual(w.sql(db), "(`name` like 'abc%')")

    def test_between1(self):
        db = FakeDB()
        db.connect()
        w = T1.uid.BETWEEN(1, 100)
        self.assertTrue(isinstance(w, adbs.Where))
        self.assertEqual(w.sql(db), "(`uid` between 1 and 100)")

    def test_sql1(self):
        self.assertEqual(T1.Pass.sql(None), "`pass`")


class TestTable(unittest.TestCase):
    def test_table1(self):
        self.assertTrue(isinstance(T1.uid, adbs.Column))
        self.assertEqual(T1.uid.default, 0)
        self.assertEqual(T1.uid.name, 'uid')
        self.assertTrue(T1.uid.autoid)
        self.assertEqual(T1.name.name, 'name')
        self.assertEqual(T1.name.default, '')
        self.assertEqual(T1.Pass.name, 'pass')
        self.assertEqual(T1.Pass.default, '1234')

    def test_table2(self):
        self.assertEqual(T1.table_name(), 't1')
        self.assertEqual(set(T1.table_cols()), set(['uid', 'name', 'Pass']))
        self.assertEqual(T1.name_map(), {'pass': 'Pass'})

    def test_table3(self):
        c = T1.get_col('Pass')
        self.assertTrue(isinstance(c, adbs.Column))
        self.assertEqual(c.name, 'pass')
        self.assertEqual(T1.sel("uid", "name"), (T1, ("uid", "name")))

    def test_table4(self):
        t = T1()
        self.assertEqual(t.sel("uid", "name"), (t, ("uid", "name")))
        self.assertEqual((t.uid, t.name, t.Pass), (0, '', '1234'))

        t = T1(uid=1)
        self.assertEqual((t.uid, t.name, t.Pass), (1, '', '1234'))

        #t = T1(port=1234)
        self.assertRaises(TypeError, T1, *{'port': 1234})


class TestSQL(unittest.TestCase):
    def test_select_sql1(self):
        db = FakeDB()
        db.connect()
        s, f = db._select_sql_(T1, T1.uid > 0)
        self.assertEqual(s, "select `uid`, `pass`, `name` "
                            "from t1 where `uid` > 0")
        s, f = db._select_sql_(T2, T2.pwd > "")
        self.assertEqual(s, "select `passwd` from t2 where `passwd` > ''")

    def test_select_sql2(self):
        db = FakeDB()
        db.connect()
        s, f = db._select_sql_(T1.sel("Pass"), T1.uid > 0)
        self.assertEqual(s, "select `pass` from t1 where `uid` > 0")
        s, f = db._select_sql_(T2.sel("pwd"), T2.pwd > "")
        self.assertEqual(s, "select `passwd` from t2 where `passwd` > ''")

    def test_insert_sql1(self):
        db = FakeDB()
        db.connect()
        t1 = T1(uid=1, Pass="p", name="n")
        s = db._insert_sql_(t1, None)
        self.assertEqual(s, "insert into t1 (`uid`, `pass`, `name`) "
                            "values (1, 'p', 'n')")
        t2 = T2(pwd="p")
        s = db._insert_sql_(t2, None)
        self.assertEqual(s, "insert into t2 (`passwd`) values ('p')")

    def test_insert_sql2(self):
        db = FakeDB()
        db.connect()
        t1 = T1(uid=1, Pass="p", name="n")
        s = db._insert_sql_(t1.sel("Pass"), None)
        self.assertEqual(s, "insert into t1 (`uid`, `pass`, `name`) "
                            "values (1, 'p', 'n') "
                            "on duplicate key update `pass`=values(`pass`)")
        t2 = T2(pwd="p")
        s = db._insert_sql_(t2.sel("pwd"), None)
        self.assertEqual(s, "insert into t2 (`passwd`) values ('p') "
                            "on duplicate key update "
                            "`passwd`=values(`passwd`)")

    def test_insert_sql3(self):
        db = FakeDB()
        db.connect()
        t1 = T1(uid=1, Pass="p", name="n")
        s = db._insert_sql_(t1, "pass=2")
        self.assertEqual(s, "insert into t1 (`uid`, `pass`, `name`) "
                            "values (1, 'p', 'n') "
                            "on duplicate key update pass=2")
        t2 = T2(pwd="p")
        s = db._insert_sql_(t2, "pwd=12")
        self.assertEqual(s, "insert into t2 (`passwd`) values ('p') "
                            "on duplicate key update pwd=12")

    def test_update_sql1(self):
        db = FakeDB()
        db.connect()
        t1 = T1(uid=1, Pass="p", name="n")
        s = db._update_sql_(t1.sel("Pass"), T1.Pass > "")
        self.assertEqual(s, "update t1 set `pass`='p' where `pass` > ''")
        t2 = T2(pwd="p")
        s = db._update_sql_(t2.sel("pwd"), T2.pwd > "")
        self.assertEqual(s, "update t2 set `passwd`='p' where `passwd` > ''")


if __name__ == '__main__':
    unittest.main()
    #unittest.main(defaultTest="TestWhere.test_or2")
