# ASVR
## single process
```python
from yeast import asvr

def WsgiApp(env, start_response):
    start_response(200, {})
    return 'Hallo World\r\n'

asvr.start_server(WsgiApp)
```

Then visit http://localhost:8080/ , you will get ```Hallo World```

## multi process
```python
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

```

#TPL

Treat template as DOM, use css selector to manipulate it

set inner text of "a" with id=line_cnt 
```python
from yeast.tpl import MyHtmlParser
tpl = MyHtmlParser(filename='./tpl/index.tpl')
tpl.root_node('a#line_cnt')[0].set_inner_text("123")
```

#ADBS

We define a database "nfc" and table "test" like this:

```python
from yeast import adbs

class NFC(adbs.MySQLSVR):
    _name = 'nfc'
    _user = 'nfc'
    _pass = 'password'
    #_host = 'localhost'
    #_port = 3306
    #_readonly = True
    #_cursor = Cursor
    #_charset = 'utf8'

class TST(adbs.Table):
    _name = 'test'
    uid = adbs.Column(0, name="id", autoid=True)
    time = adbs.Column(0)
    name = adbs.Column('noname')
```


## sync way to use DB
```python
db = NFC().connect()
tsts = db.select(TST, TST.time > 0)
for tst in tsts:
    print tst.name, tst.time
```

## async way to use it
```python
class WK(acore.Acore):
    def run(self):
        self.clt = adbs.DBClt()
        self.clt.connect(NFC())
        for y in self.clt.select(TST, TST.name > ''):
            yield y
        for tst in self.clt.db_result:
            print tst.name, tst.time

wk = WK()
wk.start()
wk.loop()
```
## select 
```python
tsts = db.select(TST, TST.time > 0)
```

or only return one

```python
tst = db.select_one(TST, TST.time > 0)
```

or only return selected column "name" 
```python
tsts = db.select(TST.sel("name"), TST.time > 0)
```
or use Where and RAW
```python
tsts = db.select(TST, adbs.Where(TST.name, "is", adbs.RAW("NULL"), False))
```

or use where and more
```python
tsts = db.select(TST.sel("name"), "where time > 0 order by name desc")
```
## insert
```python
db.insert(tst)
```
or update selected column if has duplicate entry
```python
fdb.insert(tst.sel('time'))
```

## update
This will update tst.time who's name is Name
```python
db.update(tst.sel("time"), TST.name == "Name")
```
