import os
import random
import time
from copy import deepcopy, copy

from twisted.conch import recvline
from twisted.conch.insults import insults

from honeySSH import core
from honeySSH.core.config import config
from honeySSH.core import honeyFilesystem


class HoneyBaseProtocol(insults.TerminalProtocol):
    def __init__(self, user, env):
        self.cfg = config()
        self.user = user
        self.env = env
        self.hostname = self.cfg.get('ssh', 'hostname')
        self.fs = honeyFilesystem.HoneyFilesystem(deepcopy(self.env.fs))
        if self.fs.exists(user.home):
            self.cwd = user.home
        else:
            self.cwd = '/'
        # commands is also a copy so we can add stuff on the fly
        self.commands = copy(self.env.commands)
        self.password_input = False
        self.cmdstack = []

    def logDispatch(self, msg):
        transport = self.terminal.transport.session.conn.transport
        msg = ':dispatch: ' + msg
        # transport.factory.logDispatch(transport.transport.sessionno, msg)

    def logCommand(self, command):
        transport = self.terminal.transport.session.conn.transport
        transport.logger.add_command(command)

    def connectionMade(self):
        self.displayMOTD()

        transport = self.terminal.transport.session.conn.transport

        self.realClientIP = transport.transport.getPeer().host
        self.clientVersion = transport.otherVersionString
        self.logintime = transport.logintime
        # self.ttylog_file = transport.ttylog_file

        # source IP of client in user visible reports (can be fake or real)
        cfg = config()
        if cfg.has_option('ssh', 'fake_addr'):
            self.clientIP = cfg.get('ssh', 'fake_addr')
        else:
            self.clientIP = self.realClientIP

    def displayMOTD(self):
        try:
            self.writeln(self.fs.file_contents('/etc/motd'))
        except:
            pass

    def connectionLost(self, reason):
        pass
    def getCommand(self, cmd, paths):
        if not len(cmd.strip()):
            return None
        path = None
        if cmd in self.commands:    # ???????????????????????????????????????????????????
            return self.commands[cmd]
        if cmd[0] in ('.', '/'):    # ?????????.???/???????????????????????????
            path = self.fs.parse_path(cmd, self.cwd)
            if not self.fs.exists(path):
                return None
        else:
            for i in ['%s/%s' % (self.fs.parse_path(x, self.cwd), cmd) \
                    for x in paths]:
                if self.fs.exists(i):
                    path = i
                    break
            pass

        if path in self.commands:
            return self.commands[path]
        return None

    def lineReceived(self, line):
        if len(self.cmdstack):
            self.cmdstack[-1].lineReceived(line)

    def writeln(self, data):
        self.terminal.write(data)
        self.terminal.nextLine()

    def call_command(self, cmd, *args):
        obj = cmd(self, *args)
        self.cmdstack.append(obj)
        obj.start()

    def addInteractor(self, interactor):
        transport = self.terminal.transport.session.conn.transport
        transport.interactors.append(interactor)

    def delInteractor(self, interactor):
        transport = self.terminal.transport.session.conn.transport
        transport.interactors.remove(interactor)

    def uptime(self, reset = None):
        transport = self.terminal.transport.session.conn.transport
        r = time.time() - transport.factory.starttime
        if reset:
            transport.factory.starttime = reset
        return r

class HoneyPotInteractiveProtocol(HoneyBaseProtocol, recvline.HistoricRecvLine):

    def __init__(self, user, env):
        recvline.HistoricRecvLine.__init__(self)
        HoneyBaseProtocol.__init__(self, user, env)

    def connectionMade(self):
        HoneyBaseProtocol.connectionMade(self)
        recvline.HistoricRecvLine.connectionMade(self)

        self.cmdstack = [core.honeyCMD.HoneyShell(self)]

        transport = self.terminal.transport.session.conn.transport
        # todo
        # transport.factory.sessions[transport.transport.sessionno] = self

        self.keyHandlers.update({
            b'\x04':     self.handle_CTRL_D,
            b'\x15':     self.handle_CTRL_U,
            b'\x03':     self.handle_CTRL_C,
            b'\x09':     self.handle_TAB,
            })

    # this doesn't seem to be called upon disconnect, so please use
    # HoneyPotTransport.connectionLost instead
    def connectionLost(self, reason):
        HoneyBaseProtocol.connectionLost(self, reason)
        recvline.HistoricRecvLine.connectionLost(self, reason)

    # Overriding to prevent terminal.reset()
    def initializeScreen(self):
        self.setInsertMode()

    def call_command(self, cmd, *args):
        self.setTypeoverMode()
        HoneyBaseProtocol.call_command(self, cmd, *args)

    def keystrokeReceived(self, keyID, modifier):
        # transport = self.terminal.transport.session.conn.transport
        # if type(keyID) == type(''):
        #     ttylog.ttylog_write(transport.ttylog_file, len(keyID),
        #         ttylog.TYPE_INPUT, time.time(), keyID)
        recvline.HistoricRecvLine.keystrokeReceived(self, keyID, modifier)

    # Easier way to implement password input?
    def characterReceived(self, ch, moreCharactersComing):
        if self.mode == 'insert':
            self.lineBuffer.insert(self.lineBufferIndex, ch)
        else:
            self.lineBuffer[self.lineBufferIndex:self.lineBufferIndex+1] = [ch]
        self.lineBufferIndex += 1
        if not self.password_input:
            self.terminal.write(ch)

    def handle_RETURN(self):
        if len(self.cmdstack) == 1:
            if self.lineBuffer:
                self.historyLines.append(''.join([c.decode() if isinstance(c, bytes) else c for c in self.lineBuffer]) )
            self.historyPosition = len(self.historyLines)
        self.lineBuffer = [c.encode('utf8') if isinstance(c, str) else c for c in self.lineBuffer]
        return recvline.RecvLine.handle_RETURN(self)

    def handle_CTRL_C(self):
        self.cmdstack[-1].ctrl_c()

    def handle_CTRL_U(self):
        for i in range(self.lineBufferIndex):
            self.terminal.cursorBackward()
            self.terminal.deleteCharacter()
        self.lineBuffer = self.lineBuffer[self.lineBufferIndex:]
        self.lineBufferIndex = 0

    def handle_CTRL_D(self):
        self.call_command(self.commands['exit'])

    def handle_TAB(self):
        self.cmdstack[-1].handle_TAB()

class LoggingServerProtocol(insults.ServerProtocol):
    def connectionMade(self):
        transport = self.transport.session.conn.transport

        # transport.ttylog_file = '%s/tty/%s-%s.log' % \
        #     (config().get('honeypot', 'log_path'),
        #     time.strftime('%Y%m%d-%H%M%S'),
        #     int(random.random() * 10000))
        # print('Opening TTY log: %s' % transport.ttylog_file)
        # # ttylog.ttylog_open(transport.ttylog_file, time.time())

        # transport.ttylog_open = True

        insults.ServerProtocol.connectionMade(self)

    def write(self, bytes, noLog = False):
        # transport = self.transport.session.conn.transport
        # for i in transport.interactors:
        #     i.sessionWrite(bytes)
        # if transport.ttylog_open and not noLog:
        #     ttylog.ttylog_write(transport.ttylog_file, len(bytes),
        #         ttylog.TYPE_OUTPUT, time.time(), bytes)
        insults.ServerProtocol.write(self, bytes)

    # this doesn't seem to be called upon disconnect, so please use
    # HoneyPotTransport.connectionLost instead
    def connectionLost(self, reason):
        insults.ServerProtocol.connectionLost(self, reason)