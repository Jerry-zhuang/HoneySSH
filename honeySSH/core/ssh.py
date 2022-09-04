#!/usr/bin/env python

import sys, time

from zope.interface import implementer

import twisted
from twisted.conch import avatar
from twisted.conch.checkers import InMemorySSHKeyDB, SSHPublicKeyChecker
from twisted.conch.ssh import connection, factory, keys, session, userauth, transport
from twisted.conch.ssh.transport import SSHServerTransport
from twisted.cred import portal
from twisted.conch.openssh_compat import primes
from twisted.cred.checkers import InMemoryUsernamePasswordDatabaseDontUse
from twisted.internet import protocol, reactor
from twisted.python import components, log

from honeySSH.core import honeyCMD, honeyProtocol
from honeySSH.core.config import config         # 读取配置文件的工具
from honeySSH.core.utils import str2byte

log.startLogging(sys.stderr)

# Path to RSA SSH keys used by the server.
SERVER_RSA_PRIVATE = "ssh-keys/ssh_host_rsa_key"
SERVER_RSA_PUBLIC = "ssh-keys/ssh_host_rsa_key.pub"

class HoneySSHTransport(transport.SSHServerTransport):

    hadVersion = False

    def connectionMade(self):
        """建立连接时，输出相关信息
        - 攻击机IP 
        - 攻击机端口
        - 蜜罐IP
        - 蜜罐端口
        """
        # 打印相关信息到终端
        print('New connection: %s:%s (%s:%s) [session: %d]' % \
            (self.transport.getPeer().host, self.transport.getPeer().port,
            self.transport.getHost().host, self.transport.getHost().port,
            self.transport.sessionno))
        self.interactors = []
        self.logintime = time.time()
        self.ttylog_open = False
        # [todo] 日志信息
        transport.SSHServerTransport.connectionMade(self)

    def sendKexInit(self):
        # 不要过早地发送密钥交换
        if not self.gotVersion:
            return
        transport.SSHServerTransport.sendKexInit(self)

    def dataReceived(self, data):
        # 参考
        # https://programtalk.com/python-examples/twisted.version.major/
        transport.SSHServerTransport.dataReceived(self, data)
        
        if twisted.version.major < 11 and \
                not self.hadVersion and self.gotVersion:
            self.sendKexInit()
            self.hadVersion = True

    def ssh_KEXINIT(self, packet):
        # 输出客户端SSH的版本信息
        print('Remote SSH version: %s' % (self.otherVersionString,))
        return transport.SSHServerTransport.ssh_KEXINIT(self, packet)

    def connectionLost(self, reason):
        for i in self.interactors:
            i.sessionClosed()
        # if self.transport.sessionno in self.factory.sessions:
        #     del self.factory.sessions[self.transport.sessionno]
        # self.lastlogExit()
        # if self.ttylog_open:
        #     # ttylog.ttylog_close(self.ttylog_file, time.time())
        #     self.ttylog_open = False
        transport.SSHServerTransport.connectionLost(self, reason)

    def sendDisconnect(self, reason, desc):
        if not 'bad packet length' in desc:
            # With python >= 3 we can use super?
            transport.SSHServerTransport.sendDisconnect(self, reason, desc)
        else:
            self.transport.write('Protocol mismatch.\n')
            log.msg('Disconnecting with error, code %s\nreason: %s' % \
                (reason, desc))
            self.transport.loseConnection()

class HoneySSHSession(session.SSHSession):
    def request_env(self, data):
        print('request_env: %s' % (repr(data)))

@implementer(session.ISession, session.ISessionSetEnv)
class HoneySSHAvatar(avatar.ConchUser):

    def __init__(self, username, env):
        avatar.ConchUser.__init__(self)
        self.cfg = config()
        self.username = username
        self.env = env
        self.channelLookup.update({b"session": HoneySSHSession})

        # 设置家目录
        if self.username == 'root':
            self.home = '/root'
        else:
            self.home = '/home/' + self.username.decode('utf8')

    def getPty(self, term, windowSize, attrs):
        print('Terminal size: %s %s' % windowSize[0:2])
        self.windowSize = windowSize
        return None

    def execCommand(self, proto, cmd):
        raise Exception("not executing commands")

    def openShell(self, protocol):
        serverProtocol = honeyProtocol.LoggingServerProtocol(
            honeyProtocol.HoneyPotInteractiveProtocol, self, self.env)
        serverProtocol.makeConnection(protocol)
        protocol.makeConnection(session.wrapProtocol(serverProtocol))

    def eofReceived(self):
        pass

    def closed(self):
        pass

@implementer(portal.IRealm)
class HoneySSHRealm:

    def __init__(self):
        self.env = honeyCMD.HoneyCMDEnvironment()

    def requestAvatar(self, avatarId, mind, *interfaces):
        return interfaces[0], HoneySSHAvatar(avatarId, self.env), lambda: None

class HoneySSHFactory(factory.SSHFactory):

    # protocol = HoneySSHTransport
    # Service handlers.
    services = {
        b"ssh-userauth": userauth.SSHUserAuthServer,
        b"ssh-connection": connection.SSHConnection,
    }

    def __init__(self):

        self.cfg = config()
        #
        # 获得[users]下的所有键值对
        #
        if "users" not in self.cfg.sections():
            # [todo] 产生报错信息
            # 使用默认账号密码
            users = {"root": b"password"}
        else:
            users = str2byte(dict(self.cfg.items("users")))
        #
        # 配置账号密码
        #
        passwdDB = InMemoryUsernamePasswordDatabaseDontUse(**users)
        self.portal = portal.Portal(HoneySSHRealm(), [passwdDB])

    def buildProtocol(self, addr):
        """
        借鉴kippo写的
        """

        _modulis = '/etc/ssh/moduli', '/private/etc/moduli'

        cfg = config()

        t = HoneySSHTransport()

        if cfg.has_option('ssh', 'version'):
            t.ourVersionString = str2byte(cfg.get('ssh','version'))
        else:
            t.ourVersionString = b"SSH-2.0-OpenSSH_8.2p1 Ubuntu-4ubuntu0.5"

        t.supportedPublicKeys = self.privateKeys.keys()

        for _moduli in _modulis:
            try:
                self.primes = primes.parseModuliFile(_moduli)
                break
            except IOError as err:
                pass

        if not self.primes:
            ske = t.supportedKeyExchanges[:]
            ske.remove('diffie-hellman-group-exchange-sha1')
            t.supportedKeyExchanges = ske

        t.factory = self
        return t

    def getPublicKeys(self):
        SERVER_RSA_PUBLIC = self.cfg.get("ssh", "server_rsa_public")
        return {b"ssh-rsa": keys.Key.fromFile(SERVER_RSA_PUBLIC)}

    def getPrivateKeys(self):
        SERVER_RSA_PRIVATE = self.cfg.get("ssh", "server_rsa_private")
        return {b"ssh-rsa": keys.Key.fromFile(SERVER_RSA_PRIVATE)}


if __name__ == "__main__":
    reactor.listenTCP(5022, HoneySSHFactory())
    reactor.run()
