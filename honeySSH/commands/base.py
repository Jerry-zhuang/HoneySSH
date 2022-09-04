import os, time, datetime
from honeySSH.core.honeyCMD import HoneyCMDCommand
from twisted.internet import reactor

commands = {}

class command_whoami(HoneyCMDCommand):
    def call(self):
        self.writeln(self.honeypot.user.username)
commands['/usr/bin/whoami'] = command_whoami

class command_echo(HoneyCMDCommand):
    def call(self):
        self.writeln(' '.join(self.args))
commands['/usr/bin/echo'] = command_echo

class command_clear(HoneyCMDCommand):
    def call(self):
        self.honeypot.terminal.reset()
commands['/usr/bin/clear'] = command_clear

class command_uname(HoneyCMDCommand):
    def call(self):
        if self.args and self.args[0].strip() in ('-a', '--all'):
            self.writeln(
                'Linux %s 5.15.0-43-generic #46~20.04.1-Ubuntu SMP Thu Jul 14 15:20:17 UTC 2022 x86_64 x86_64 x86_64 GNU/Linux' % \
                self.honeypot.hostname
            )
        else:
            self.writeln('Linux')
commands['/usr/bin/uname'] = command_uname

class command_exit(HoneyCMDCommand):
    def call(self):
        print(self.honeypot.clientVersion)
        if b'PuTTY' in self.honeypot.clientVersion or \
                b'libssh' in self.honeypot.clientVersion or \
                b'sshlib' in self.honeypot.clientVersion or \
                b'OpenSSH' in self.honeypot.clientVersion:
            self.honeypot.terminal.loseConnection()
            return
        self.honeypot.terminal.reset()
        self.writeln('Connection to server closed.')
        self.honeypot.hostname = 'localhost'
        self.honeypot.cwd = '/root'
        if not self.fs.exists(self.honeypot.cwd):
            self.honeypot.cwd = '/'
commands['exit'] = command_exit
commands['logout'] = command_exit

class command_hostname(HoneyCMDCommand):
    def call(self):
        self.writeln(self.honeypot.hostname)
commands['/usr/bin/hostname'] = command_hostname

class command_ps(HoneyCMDCommand):
    def call(self):
        user = self.honeypot.user.username.decode()
        args = ''
        if len(self.args):
            args = self.args[0].strip()
        _user, _pid, _cpu, _mem, _vsz, _rss, _tty, _stat, \
            _start, _time, _command = range(11)
        output = (
            ('USER      ', ' PID', ' %CPU', ' %MEM', '    VSZ', '   RSS', ' TTY      ', 'STAT ', 'START', '   TIME ', 'COMMAND',),
            ('root      ', '   1', '  0.0', '  0.1', '   2100', '   688', ' ?        ', 'Ss   ', 'Nov06', '   0:07 ', 'init [2]  ',),
            ('root      ', '   2', '  0.0', '  0.0', '      0', '     0', ' ?        ', 'S<   ', 'Nov06', '   0:00 ', '[kthreadd]',),
            ('root      ', '   3', '  0.0', '  0.0', '      0', '     0', ' ?        ', 'S<   ', 'Nov06', '   0:00 ', '[migration/0]',),
            ('root      ', '   4', '  0.0', '  0.0', '      0', '     0', ' ?        ', 'S<   ', 'Nov06', '   0:00 ', '[ksoftirqd/0]',),
            ('root      ', '   5', '  0.0', '  0.0', '      0', '     0', ' ?        ', 'S<   ', 'Nov06', '   0:00 ', '[watchdog/0]',),
            ('root      ', '   6', '  0.0', '  0.0', '      0', '     0', ' ?        ', 'S<   ', 'Nov06', '   0:17 ', '[events/0]',),
            ('root      ', '   7', '  0.0', '  0.0', '      0', '     0', ' ?        ', 'S<   ', 'Nov06', '   0:00 ', '[khelper]',),
            ('root      ', '  39', '  0.0', '  0.0', '      0', '     0', ' ?        ', 'S<   ', 'Nov06', '   0:00 ', '[kblockd/0]',),
            ('root      ', '  41', '  0.0', '  0.0', '      0', '     0', ' ?        ', 'S<   ', 'Nov06', '   0:00 ', '[kacpid]',),
            ('root      ', '  42', '  0.0', '  0.0', '      0', '     0', ' ?        ', 'S<   ', 'Nov06', '   0:00 ', '[kacpi_notify]',),
            ('root      ', ' 170', '  0.0', '  0.0', '      0', '     0', ' ?        ', 'S<   ', 'Nov06', '   0:00 ', '[kseriod]',),
            ('root      ', ' 207', '  0.0', '  0.0', '      0', '     0', ' ?        ', 'S    ', 'Nov06', '   0:01 ', '[pdflush]',),
            ('root      ', ' 208', '  0.0', '  0.0', '      0', '     0', ' ?        ', 'S    ', 'Nov06', '   0:00 ', '[pdflush]',),
            ('root      ', ' 209', '  0.0', '  0.0', '      0', '     0', ' ?        ', 'S<   ', 'Nov06', '   0:00 ', '[kswapd0]',),
            ('root      ', ' 210', '  0.0', '  0.0', '      0', '     0', ' ?        ', 'S<   ', 'Nov06', '   0:00 ', '[aio/0]',),
            ('root      ', ' 748', '  0.0', '  0.0', '      0', '     0', ' ?        ', 'S<   ', 'Nov06', '   0:00 ', '[ata/0]',),
            ('root      ', ' 749', '  0.0', '  0.0', '      0', '     0', ' ?        ', 'S<   ', 'Nov06', '   0:00 ', '[ata_aux]',),
            ('root      ', ' 929', '  0.0', '  0.0', '      0', '     0', ' ?        ', 'S<   ', 'Nov06', '   0:00 ', '[scsi_eh_0]',),
            ('root      ', '1014', '  0.0', '  0.0', '      0', '     0', ' ?        ', 'D<   ', 'Nov06', '   0:03 ', '[kjournald]',),
            ('root      ', '1087', '  0.0', '  0.1', '   2288', '   772', ' ?        ', 'S<s  ', 'Nov06', '   0:00 ', 'udevd --daemon',),
            ('root      ', '1553', '  0.0', '  0.0', '      0', '     0', ' ?        ', 'S<   ', 'Nov06', '   0:00 ', '[kpsmoused]',),
            ('root      ', '2054', '  0.0', '  0.2', '  28428', '  1508', ' ?        ', 'Sl   ', 'Nov06', '   0:01 ', '/usr/sbin/rsyslogd -c3',),
            ('root      ', '2103', '  0.0', '  0.2', '   2628', '  1196', ' tty1     ', 'Ss   ', 'Nov06', '   0:00 ', '/bin/login --     ',),
            ('root      ', '2105', '  0.0', '  0.0', '   1764', '   504', ' tty2     ', 'Ss+  ', 'Nov06', '   0:00 ', '/sbin/getty 38400 tty2',),
            ('root      ', '2107', '  0.0', '  0.0', '   1764', '   504', ' tty3     ', 'Ss+  ', 'Nov06', '   0:00 ', '/sbin/getty 38400 tty3',),
            ('root      ', '2109', '  0.0', '  0.0', '   1764', '   504', ' tty4     ', 'Ss+  ', 'Nov06', '   0:00 ', '/sbin/getty 38400 tty4',),
            ('root      ', '2110', '  0.0', '  0.0', '   1764', '   504', ' tty5     ', 'Ss+  ', 'Nov06', '   0:00 ', '/sbin/getty 38400 tty5',),
            ('root      ', '2112', '  0.0', '  0.0', '   1764', '   508', ' tty6     ', 'Ss+  ', 'Nov06', '   0:00 ', '/sbin/getty 38400 tty6',),
            ('root      ', '2133', '  0.0', '  0.1', '   2180', '   620', ' ?        ', 'S<s  ', 'Nov06', '   0:00 ', 'dhclient3 -pf /var/run/dhclient.eth0.pid -lf /var/lib/dhcp3/dhclien',),
            ('root      ', '4969', '  0.0', '  0.1', '   5416', '  1024', ' ?        ', 'Ss   ', 'Nov08', '   0:00 ', '/usr/sbin/sshd: %s@pts/0' % user,),
            ('%s'.ljust(8) % user, '5673', '  0.0', '  0.2', '   2924', '  1540', ' pts/0    ', 'Ss   ', '04:30', '   0:00 ', '-bash',),
            ('%s'.ljust(8) % user, '5679', '  0.0', '  0.1', '   2432', '   928', ' pts/0    ', 'R+   ', '04:32', '   0:00 ', 'ps %s' % ' '.join(self.args),)
            )
        for i in range(len(output)):
            if i != 0:
                if 'a' not in args and output[i][_user].strip() != user:
                    continue
                elif 'a' not in args and 'x' not in args \
                        and output[i][_tty].strip() != 'pts/0':
                    continue
            l = [_pid, _tty, _time, _command]
            if 'a' in args or 'x' in args:
                l = [_pid, _tty, _stat, _time, _command]
            if 'u' in args:
                l = [_user, _pid, _cpu, _mem, _vsz, _rss, _tty, _stat,
                    _start, _time, _command]
            s = ''.join([output[i][x] for x in l])
            if 'w' not in args:
                s = s[:80]
            self.writeln(s)
commands['/usr/bin/ps'] = command_ps

class command_history(HoneyCMDCommand):
    def call(self):
        if len(self.args) and self.args[0] == '-c':
            self.honeypot.historyLines = []
            self.honeypot.historyPosition = 0
            return
        count = 1
        for l in self.honeypot.historyLines:
            self.writeln(' %s  %s' % (str(count).rjust(4), l))
            count += 1
commands['history'] = command_history

class command_yes(HoneyCMDCommand):
    def start(self):
        self.y()

    def y(self):
        self.writeln('y')
        self.scheduled = reactor.callLater(0.01, self.y)

    def ctrl_c(self):
        self.scheduled.cancel()
        self.exit()
commands['/usr/bin/yes'] = command_yes

class command_nop(HoneyCMDCommand):
    def call(self):
        pass
commands['umask'] = command_nop
commands['set'] = command_nop
commands['unset'] = command_nop
commands['export'] = command_nop
commands['alias'] = command_nop
commands['/usr/bin/kill'] = command_nop
commands['/usr/bin/su'] = command_nop
commands['/usr/bin/chown'] = command_nop
commands['/usr/bin/chgrp'] = command_nop
commands['/usr/bin/chattr'] = command_nop