#! /usr/bin/python

import sys
import time
from urlparse import parse_qs

sys.path.append('../yeast')
from yeast.ahttp import ARPC
from yeast.asvr import WsgiHandler, start_server
from yeast.acore import Listener, Acore, ARW, TimeOut, Aact
from yeast.acore import Aqueue as QUEUE


q = QUEUE()

def MyApp(env, start_response):
    '''
    Consumer will query task, wait 5 sec, if timeout get empty
    curl http://127.0.0.1:8008/consumer
    Supplier will submit task, save in queue, wait consumer to query
    curl http://127.0.0.1:8008/supplier?url=1&ebg=2&cate=3
    '''

    path = env.get('PATH_INFO', '')
    q_dict = parse_qs(env['QUERY_STRING'])
    if path.startswith('/supplier'):
        # accept submission
        try:
            url = q_dict['url'][0]
            eng = q_dict['eng'][0]
            cate = q_dict['cate'][0]
        except:
            start_response(500, {})
            return "ERROR\n"
        else:
            #q = QUEUE()
            q.put({'url': url, 'eng': eng, 'cate': cate})
            start_response(200, {})
            return "Accepted\n"
    elif path.startswith('/consumer'):
        # get worker
        start_response(200, {})
        return WorkerAPP2()
    start_response(400, {})
    return ""


def WorkerAPP1():
    for y in q.get(timeout=5):
        if isinstance(y, Aact):
            yield y
    ret = y
    yield str(ret)


def WorkerAPP2():
    g = q.get_getter()
    for y in g.get(timeout=5):
        yield y
    yield str(g.data)


def main():
    start_server(MyApp, addr=('', 8008))


if __name__ == '__main__':
    main()
