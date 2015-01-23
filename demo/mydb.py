
import sys
sys.path.append("../yeast")

import pickle 

import acore
import adbs

from fgdwcfpy.log import loginit


class NFC(adbs.MySQLSVR):
    _name = 'nfc'
    _user = 'nfc'
    _pass = '1234'
    _host = '172.17.93.23'


class TST(adbs.Table):
    _name = 'test'
    time = adbs.Column(0)
    name = adbs.Column('')


class WK(acore.Acore):
    def run(self):
        self.clt = adbs.DBClt()
        self.clt.connect(NFC())
        #for y in self.clt.query("select count(*) from test"):
        #    yield y
        for y in self.clt.select(TST, TST.name > ''):
            yield y
        #print dbt.clt.afunc.func_ret
        for tst in wk.clt.db_result:
            print tst.name, tst.time
        print "-------------------------------------"
        for y in self.clt.select(TST, TST.time > 0):
            yield y
        for tst in wk.clt.db_result:
            print tst.name, tst.time


loginit(level='DEBUG')


#t = TST()
#print pickle.dumps(TST)
#sys.exit(1)

wk = WK()
wk.start()
wk.loop()

print "============= sync usage: ==========="
db = NFC().connect()
tsts = db.select(TST, TST.time > 0)
for tst in tsts:
    print tst.name, tst.time

print "============= select_one usage: ==========="
tst = db.select_one(TST, TST.name == 'abcd')
print tst
print tst.name, tst.time
