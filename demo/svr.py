import sys
sys.path.append('../yeast')

import asvr

asvr.start_server(asvr.WsgiApp)
