import twisted
from copy import deepcopy, copy
import os
import shlex
import pickle

from honeySSH.core.config import config

class HoneyCMDCommand(object):
    def __init__(self, honeypot, *args):
        self.honeypot = honeypot
        self.args = args
        self.writeln = self.honeypot.writeln
        self.write = self.honeypot.terminal.write
        self.nextLine = self.honeypot.terminal.nextLine
        self.fs = self.honeypot.fs

    def start(self):
        self.call()
        self.exit()

    def call(self):
        self.honeypot.writeln('Hello World! [%s]' % repr(self.args))

    def exit(self):
        self.honeypot.cmdstack.pop()
        self.honeypot.cmdstack[-1].resume()

    def ctrl_c(self):
        print('Received CTRL-C, exiting..')
        self.writeln('^C')
        self.exit()

    def lineReceived(self, line):
        print('INPUT: %s' % line)

    def resume(self):
        pass

    def handle_TAB(self):
        pass

class HoneyShell(object):
    def __init__(self, honeypot, interactive = True):
        self.honeypot = honeypot
        self.interactive = interactive
        self.showPrompt()
        self.cmdpending = []
        self.envvars = {
            'PATH':     '/bin:/usr/bin:/sbin:/usr/sbin',
            }

    def lineReceived(self, line):
        if type(line) == bytes:
            line = line.decode()
        print('CMD: %s' % line)
        line = str(line[:500])
        for i in [x.strip() for x in line.strip().split(';')[:10]]:
            if not len(i):
                continue
            self.cmdpending.append(i)
        if len(self.cmdpending):
            self.runCommand()
        else:
            self.showPrompt()

    def runCommand(self):
        def runOrPrompt():
            if len(self.cmdpending):
                self.runCommand()
            else:
                self.showPrompt()

        if not len(self.cmdpending):
            if self.interactive:
                self.showPrompt()
            else:
                self.honeypot.terminal.transport.loseConnection()
            return

        line = self.cmdpending.pop(0)
        try:
            cmdAndArgs = shlex.split(line)
        except:
            self.honeypot.writeln(
                'bash: syntax error: unexpected end of file')
            # could run runCommand here, but i'll just clear the list instead
            self.cmdpending = []
            self.showPrompt()
            return

        # probably no reason to be this comprehensive for just PATH...
        envvars = copy(self.envvars)
        cmd = None
        while len(cmdAndArgs):
            piece = cmdAndArgs.pop(0)
            if piece.count('='):
                key, value = piece.split('=', 1)
                envvars[key] = value
                continue
            cmd = piece
            break
        args = cmdAndArgs

        if not cmd:
            runOrPrompt()
            return

        rargs = []
        for arg in args:
            matches = None
            matches = self.honeypot.fs.parse_path_wc(arg, self.honeypot.cwd)
            if matches:
                rargs.extend(matches)
            else:
                rargs.append(arg)
        cmdclass = self.honeypot.getCommand(cmd, envvars['PATH'].split(':'))
        if cmdclass:
            print('Command found: %s' % (line,))
            self.honeypot.logCommand(line)  # 调用存储指令到日志
            self.honeypot.call_command(cmdclass, *rargs)
        else:
            print('Command not found: %s' % (line,))
            if len(line):
                self.honeypot.writeln('bash: %s: command not found' % cmd)
                runOrPrompt()

    def resume(self):
        if self.interactive:
            self.honeypot.setInsertMode()
        self.runCommand()

    def showPrompt(self):
        """bash的交互前缀
        """
        if not self.interactive:
            return
        prompt = '%s@%s:%%(path)s' % (self.honeypot.user.username.decode('utf8'), self.honeypot.hostname,)
        if self.honeypot.user.username.decode('utf8') == "root":
            prompt += '# '    # Root用户
        else:
            prompt += '$ '    # 非Root用户


        path = self.honeypot.cwd
        # 对于home目录下的一些修改
        homelen = len(self.honeypot.user.home)
        if path == self.honeypot.user.home: # 如果是家目录，替换为home
            path = '~'
        elif len(path) > (homelen+1) and \
                path[:(homelen+1)] == self.honeypot.user.home + '/':
            path = '~' + path[homelen:]

        attrs = {'path': path}
        self.honeypot.terminal.write(prompt % attrs)

    def ctrl_c(self):
        self.honeypot.lineBuffer = []
        self.honeypot.lineBufferIndex = 0
        self.honeypot.terminal.nextLine()
        self.showPrompt()

    # Tab 补全
    # 时间有限，暂未实现
    def handle_TAB(self):
        return None

class HoneyCMDEnvironment(object):
    def __init__(self):
        self.cfg = config()
        self.commands = {}

        import honeySSH.commands
        for c in honeySSH.commands.__all__:
            module = __import__('honeySSH.commands.%s' % c,
                globals(), locals(), ['commands'])
            self.commands.update(module.commands)

        # 读取虚假的文件系统
        self.fs = pickle.load(open(
            self.cfg.get('filesystem', 'filesystem_path'), 'rb'))