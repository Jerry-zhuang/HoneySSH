import os, getopt, stat, time
from copy import deepcopy
from honeySSH.core.honeyCMD import HoneyCMDCommand
from honeySSH.core.honeyFilesystem import *

commands = {}

class command_cat(HoneyCMDCommand):
    def call(self):
        for arg in self.args:
            path = self.fs.parse_path(arg, self.honeypot.cwd)
            if self.fs.is_dir(path):
                self.writeln('cat: %s: Is a directory' % (arg,))
                continue
            try:
                self.write(self.fs.file_contents(path))
            except:
                self.writeln('cat: %s: No such file or directory' % (arg,))

commands['/usr/bin/cat'] = command_cat

class command_cd(HoneyCMDCommand):
    def call(self):
        if not self.args or self.args[0] == "~":
            path = self.honeypot.user.home
        else:
            path = self.args[0]
        try:
            newpath = self.fs.parse_path(path, self.honeypot.cwd)
            newdir = self.fs.get_path(newpath)
        except IndexError:
            newdir = None
        if path == "-":
            self.writeln('bash: cd: OLDPWD not set')
            return
        if newdir is None:
            self.writeln('bash: cd: %s: No such file or directory' % path)
            return
        if not self.fs.is_dir(newpath):
            self.writeln('bash: cd: %s: Not a directory' % path)
            return
        self.honeypot.cwd = newpath
commands['cd'] = command_cd

class command_rm(HoneyCMDCommand):
    def call(self):
        recursive = False
        for f in self.args:
            if f.startswith('-') and 'r' in f:
                recursive = True
        for f in self.args:
            path = self.fs.parse_path(f, self.honeypot.cwd)
            try:
                dir = self.fs.get_path('/'.join(path.split('/')[:-1]))
            except IndexError:
                self.writeln(
                    'rm: cannot remove `%s\': No such file or directory' % f)
                continue
            basename = path.split('/')[-1]
            contents = [x for x in dir]
            for i in dir[:]:
                if i[A_NAME] == basename:
                    if i[A_TYPE] == T_DIR and not recursive:
                        self.writeln(
                            'rm: cannot remove `%s\': Is a directory' % \
                            i[A_NAME])
                    else:
                        dir.remove(i)
commands['/usr/bin/rm'] = command_rm

class command_cp(HoneyCMDCommand):
    def call(self):
        if not len(self.args):
            self.writeln("cp: missing file operand")
            self.writeln("Try `cp --help' for more information.")
            return
        try:
            optlist, args = getopt.gnu_getopt(self.args,
                '-abdfiHlLPpRrsStTuvx')
        except getopt.GetoptError as err:
            self.writeln('Unrecognized option')
            return
        recursive = False
        for opt in optlist:
            if opt[0] in ('-r', '-a', '-R'):
                recursive = True

        # TODO: recursive disabled now, recursive needs to be
        # implemented without deepcopy and with limits
        recursive = False

        def resolv(path):
            return self.fs.parse_path(path, self.honeypot.cwd)

        if len(args) < 2:
            self.writeln("cp: missing destination file operand after `%s'" % \
                (self.args[0],))
            self.writeln("Try `cp --help' for more information.")
            return
        sources, dest = args[:-1], args[-1]
        if len(sources) > 1 and not self.fs.is_dir(resolv(dest)):
            self.writeln("cp: target `%s' is not a directory" % (dest,))
            return

        if dest[-1] == '/' and not self.fs.exists(resolv(dest)) and \
                not recursive:
            self.writeln(
                "cp: cannot create regular file `%s': Is a directory" % \
                (dest,))
            return

        if self.fs.is_dir(resolv(dest)):
            is_dir = True
        else:
            is_dir = False
            parent = os.path.dirname(resolv(dest))
            if not self.fs.exists(parent):
                self.writeln("cp: cannot create regular file " + \
                    "`%s': No such file or directory" % (dest,))
                return

        for src in sources:
            if not self.fs.exists(resolv(src)):
                self.writeln(
                    "cp: cannot stat `%s': No such file or directory" % (src,))
                continue
            if not recursive and self.fs.is_dir(resolv(src)):
                self.writeln("cp: omitting directory `%s'" % (src,))
                continue
            s = deepcopy(self.fs.get_file(resolv(src)))
            if is_dir:
                dir = self.fs.get_path(resolv(dest))
                outfile = os.path.basename(src)
            else:
                dir = self.fs.get_path(os.path.dirname(resolv(dest)))
                outfile = os.path.basename(dest.rstrip('/'))
            if outfile in [x[A_NAME] for x in dir]:
                dir.remove([x for x in dir if x[A_NAME] == outfile][0])
            s[A_NAME] = outfile
            dir.append(s)
commands['/usr/bin/cp'] = command_cp

class command_mv(HoneyCMDCommand):
    def call(self):
        if not len(self.args):
            self.writeln("mv: missing file operand")
            self.writeln("Try `mv --help' for more information.")
            return

        try:
            optlist, args = getopt.gnu_getopt(self.args, '-bfiStTuv')
        except getopt.GetoptError as err:
            self.writeln('Unrecognized option')
            self.exit()

        def resolv(path):
            return self.fs.parse_path(path, self.honeypot.cwd)

        if len(args) < 2:
            self.writeln("mv: missing destination file operand after `%s'" % \
                (self.args[0],))
            self.writeln("Try `mv --help' for more information.")
            return
        sources, dest = args[:-1], args[-1]
        if len(sources) > 1 and not self.fs.is_dir(resolv(dest)):
            self.writeln("mv: target `%s' is not a directory" % (dest,))
            return

        if dest[-1] == '/' and not self.fs.exists(resolv(dest)) and \
                len(sources) != 1:
            self.writeln(
                "mv: cannot create regular file `%s': Is a directory" % \
                (dest,))
            return

        if self.fs.is_dir(resolv(dest)):
            is_dir = True
        else:
            is_dir = False
            parent = os.path.dirname(resolv(dest))
            if not self.fs.exists(parent):
                self.writeln("mv: cannot create regular file " + \
                    "`%s': No such file or directory" % \
                    (dest,))
                return

        for src in sources:
            if not self.fs.exists(resolv(src)):
                self.writeln(
                    "mv: cannot stat `%s': No such file or directory" % \
                    (src,))
                continue
            s = self.fs.get_file(resolv(src))
            if is_dir:
                dir = self.fs.get_path(resolv(dest))
                outfile = os.path.basename(src)
            else:
                dir = self.fs.get_path(os.path.dirname(resolv(dest)))
                outfile = os.path.basename(dest)
            if dir != os.path.dirname(resolv(src)):
                s[A_NAME] = outfile
                dir.append(s)
                sdir = self.fs.get_path(os.path.dirname(resolv(src)))
                sdir.remove(s)
            else:
                s[A_NAME] = outfile
commands['/usr/bin/mv'] = command_mv

class command_mkdir(HoneyCMDCommand):
    def call(self):
        for f in self.args:
            path = self.fs.parse_path(f, self.honeypot.cwd)
            if self.fs.exists(path):
                self.writeln(
                    'mkdir: cannot create directory `%s\': File exists' % f)
                return
            ok = self.fs.mkdir(path, 0, 0, 4096, 16877)
            if not ok:
                self.writeln(
                    'mkdir: cannot create directory `%s\': ' % f + \
                    'No such file or directory')
                return
commands['/usr/bin/mkdir'] = command_mkdir

class command_rmdir(HoneyCMDCommand):
    def call(self):
        for f in self.args:
            path = self.fs.parse_path(f, self.honeypot.cwd)
            if len(self.fs.get_path(path)):
                self.writeln(
                    'rmdir: failed to remove `%s\': Directory not empty' % f)
                continue
            try:
                dir = self.fs.get_path('/'.join(path.split('/')[:-1]))
            except IndexError:
                dir = None
            if not dir or f not in [x[A_NAME] for x in dir]:
                self.writeln(
                    'rmdir: failed to remove `%s\': ' % f + \
                    'No such file or directory')
                continue
            for i in dir[:]:
                if i[A_NAME] == f:
                    dir.remove(i)
commands['/usr/bin/rmdir'] = command_rmdir

class command_pwd(HoneyCMDCommand):
    def call(self):
        self.writeln(self.honeypot.cwd)
commands['/usr/bin/pwd'] = command_pwd

class command_touch(HoneyCMDCommand):
    def call(self):
        if not len(self.args):
            self.writeln('touch: missing file operand')
            self.writeln('Try `touch --help\' for more information.')
            return
        for f in self.args:
            path = self.fs.parse_path(f, self.honeypot.cwd)
            if not self.fs.exists(os.path.dirname(path)):
                self.writeln(
                    'touch: cannot touch `%s`: no such file or directory' % \
                    (path))
                return
            if self.fs.exists(path):
                # FIXME: modify the timestamp here
                continue
            self.fs.mkfile(path, 0, 0, 0, 33188)
commands['/usr/bin/touch'] = command_touch


class command_ls(HoneyCMDCommand):

    def uid2name(self, uid):
        if uid == 0:
            return 'root'
        return uid

    def gid2name(self, gid):
        if gid == 0:
            return 'root'
        return gid

    def call(self):
        path = self.honeypot.cwd
        paths = []
        if len(self.args):
            for arg in self.args:
                if not arg.startswith('-'):
                    paths.append(self.honeypot.fs.resolve_path(arg,
                        self.honeypot.cwd))

        self.show_hidden = False
        func = self.do_ls_normal
        for x in self.args:
            if x.startswith('-') and x.count('l'):
                func = self.do_ls_l
            if x.startswith('-') and x.count('a'):
                self.show_hidden = True

        if not paths:
            func(path)
        else:
            for path in paths:
                func(path)

    def do_ls_normal(self, path):
        try:
            files = self.honeypot.fs.get_path(path)
        except:
            self.honeypot.writeln(
                'ls: cannot access %s: No such file or directory' % path)
            return
        l = [x[A_NAME] for x in files \
            if self.show_hidden or not x[A_NAME].startswith('.')]
        if self.show_hidden:
            l.insert(0, '..')
            l.insert(0, '.')
        if not l:
            return
        count = 0
        maxlen = max([len(x) for x in l])

        try:
            wincols = self.honeypot.user.windowSize[1]
        except AttributeError:
            wincols = 80

        perline = int(wincols / (maxlen + 1))
        for f in l:
            if count == perline:
                count = 0
                self.nextLine()
            self.write(f.ljust(maxlen + 1))
            count += 1
        self.nextLine()

    def do_ls_l(self, path):
        try:
            files = self.honeypot.fs.get_path(path)[:]
        except:
            self.honeypot.writeln(
                'ls: cannot access %s: No such file or directory' % path)
            return

        largest = 0
        if len(files):
            largest = max([x[A_SIZE] for x in files])

        # FIXME: should grab these off the parents instead
        files.insert(0,
            ['..', T_DIR, 0, 0, 4096, 16877, time.time(), [], None])
        files.insert(0,
            ['.', T_DIR, 0, 0, 4096, 16877, time.time(), [], None])
        for file in files:
            perms = ['-'] * 10

            if file[A_MODE] & stat.S_IRUSR: perms[1] = 'r'
            if file[A_MODE] & stat.S_IWUSR: perms[2] = 'w'
            if file[A_MODE] & stat.S_IXUSR: perms[3] = 'x'

            if file[A_MODE] & stat.S_IRGRP: perms[4] = 'r'
            if file[A_MODE] & stat.S_IWGRP: perms[5] = 'w'
            if file[A_MODE] & stat.S_IXGRP: perms[6] = 'x'

            if file[A_MODE] & stat.S_IROTH: perms[7] = 'r'
            if file[A_MODE] & stat.S_IWOTH: perms[8] = 'w'
            if file[A_MODE] & stat.S_IXOTH: perms[9] = 'x'

            linktarget = ''

            if file[A_TYPE] == T_DIR:
                perms[0] = 'd'
            elif file[A_TYPE] == T_LINK:
                perms[0] = 'l'
                linktarget = ' -> %s' % (file[A_TARGET],)

            perms = ''.join(perms)
            ctime = time.localtime(file[A_CTIME])

            l = '%s 1 %s %s %s %s %s%s' % \
                (perms,
                self.uid2name(file[A_UID]),
                self.gid2name(file[A_GID]),
                str(file[A_SIZE]).rjust(len(str(largest))),
                time.strftime('%Y-%m-%d %H:%M', ctime),
                file[A_NAME],
                linktarget)

            self.honeypot.writeln(l)
commands['/usr/bin/ls'] = command_ls
# vim: set sw=4 et: