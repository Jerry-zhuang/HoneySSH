import sys, os
# 设置项目的根目录
sys.path.insert(0, os.path.abspath(os.getcwd()))

from twisted.internet import reactor

from honeySSH.core.ssh import HoneySSHFactory

reactor.listenTCP(5022, HoneySSHFactory())
reactor.run()