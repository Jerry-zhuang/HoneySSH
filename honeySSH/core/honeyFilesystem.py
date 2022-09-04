import pickle
import os, time, fnmatch
import sys
sys.path.insert(0, os.path.abspath(os.getcwd()))
from honeySSH.core.config import config

# honeyFilesystem

# 文件系统目录使用列表，采用树结构进行存储
# [A_NAME,  A_TYPE,  A_UID,   A_GID,     A_SIZE,  A_MODE,  A_CTIME, A_CONTENTS, A_TARGET,    A_REALFILE  ]
# [文件名， 文件类型，文件用户，文件用户组，文件大小，保护模式，创建时间，   子树，  link文件目标， 替换的真实文件]
(A_NAME, A_TYPE, A_UID, A_GID, A_SIZE, A_MODE, A_CTIME, A_CONTENTS, A_TARGET, A_REALFILE) = range(0, 10)

# 其中A_TYPE有以下七种
# [T_LINK, T_DIR, T_FILE, T_BLK, T_CHR, T_SOCK, T_FIFO]
# 参考链接：https://www.cnblogs.com/surpassme/p/9344738.html
(T_LINK, T_DIR, T_FILE, T_BLK, T_CHR, T_SOCK, T_FIFO) = range(0, 7)

# 
# 报错信息
# 
class TooManyLevels(Exception):
    pass

class FileNotFound(Exception):
    pass

class HoneyFilesystem():
    def __init__(self, fs):
        self.fs = fs

    def parse_path(self, path:str, cwd:str) -> str:
        """路径解析函数

        Args:
            path (str): 路径
            cwd (str): 当前目录

        Returns:
            str: 解析后的路径
        """
        # 将路径分割为列表
        pieces = path.rstrip('/').split('/')

        if path[0] == '/':  # 如果路径是绝对路径
            cwd = []        # 用不到当前目录
        else:               # 如果是相对路径
            cwd = [x for x in cwd.split('/') if len(x) and x is not None]   # 分割当前目录

        # 循环处理，函数的核心部分
        while True:
            if not pieces:    # 如果列表为空
                break           # 退出循环
            piece = pieces.pop(0)
            if piece == '..':   # 如果是..上级目录
                if cwd:     # 如果当前列表目录不为空
                    cwd.pop()    # 当前目录回退一格
                    continue
            if piece in ('.', ''):  # 如果是.当前目录
                continue
            cwd.append(piece)
        return '/%s' % '/'.join(cwd)

    def parse_path_wc(self, path, cwd):
        """借鉴Kippo，进行指令查找，区分指令和参数

        Args:
            path (_type_): _description_
            cwd (_type_): _description_

        Returns:
            _type_: _description_
        """
        pieces = path.rstrip('/').split('/')
        if len(pieces[0]):
            cwd = [x for x in cwd.split('/') if len(x) and x is not None]
            path = path[1:]
        else:
            cwd, pieces = [], pieces[1:]
        found = []
        def foo(p, cwd):
            if not len(p):
                found.append('/%s' % '/'.join(cwd))
            elif p[0] == '.':
                foo(p[1:], cwd)
            elif p[0] == '..':
                foo(p[1:], cwd[:-1])
            else:
                names = [x[A_NAME] for x in self.get_path('/'.join(cwd))]
                matches = [x for x in names if fnmatch.fnmatchcase(x, p[0])]
                for match in matches:
                    foo(p[1:], cwd + [match])
        foo(pieces, cwd)
        return found

    def get_path(self, path:str) -> list:
        """获取指定路径下的文件，也就是寻找指定节点下的子树

        Args:
            path (str): 路径

        Returns:
            list: 子树
        """
        p = self.fs     # 指向当前文件
        for i in path.split('/'):   # 分割路径，进行循环
            if not i:
                continue
            p = [x for x in p[A_CONTENTS] if x[A_NAME] == i][0]     # 递归寻找
        return p[A_CONTENTS]

    def get_file(self, path:str) -> list or bool:
        """获取文件节点

        Args:
            path (str): 路径

        Returns:
            list or bool: 结果，未找到返回False
        """
        if path == '/':     # 如果是根目录
            return self.fs  # 返回当前文件
        pieces = path.strip('/').split('/')     # 切割路径
        p = self.fs  # 指向当前文件
        while True:
            if not pieces:  # 如果为空
                break       # 退出循环
            piece = pieces.pop(0)   
            if piece not in [x[A_NAME] for x in p[A_CONTENTS]]:     # 如果在当前文件(夹)的下层文件中不包含该文件
                return False
            p = [x for x in p[A_CONTENTS] if x[A_NAME] == piece][0] # 指向下一级文件(夹)
        return p

    def exists(self, path:str) -> bool:
        """文件是否存在

        Args:
            path (str): 路径

        Returns:
            bool: 结果
        """
        f = self.get_file(path)
        if f is not False:
            return True
        return f

    def update_realfile(self, f:list, realfile:str):
        """更新真实文件，将文件指向用户提供的真实文件

        Args:
            f (list): 修改的文件
            realfile (str): 真实文件路径
        """
        if not f[A_REALFILE] and os.path.exists(realfile) and \
            not os.path.islink(realfile) and os.path.isfile(realfile):
            print('Updating realfile to %s' % realfile)
            f[A_REALFILE] = realfile

    def realfile(self, f:list, path:str) -> str or None:
        """获取真实文件

        Args:
            f (list): 文件
            path (str): 路径

        Returns:
            str or None: 结果
        """
        self.update_realfile(f, path)
        if f[A_REALFILE]:
            return f[A_REALFILE]
        return None

    def mkfile(self, path, uid, gid, size, mode, ctime = None) -> bool:
        """创建文件

        Args:
            path : 文件在系统中的真实路径
            uid : 用户id
            gid : 用户组id
            size : 文件大小
            mode : 文件的保护模式
            ctime : 文件创建时间. Defaults to None.

        Returns:
            bool: 结果
        """
        if ctime is None:       # 如果创建时间为空，获取当前时间
            ctime = time.time()
        dir = self.get_path(os.path.dirname(path))  # 获取文件所在路径
        outfile = os.path.basename(path)            # 文件名
        if outfile in [x[A_NAME] for x in dir]:     # 如果虚拟文件系统中含有该文件
            dir.remove([x for x in dir if x[A_NAME] == outfile][0])     # 删除
        dir.append([outfile, T_FILE, uid, gid, size, mode, ctime, [],
            None, None])
        return True

    def mkdir(self, path, uid, gid, size, mode, ctime = None):
        """创建目录

        Args:
            path : 文件在系统中的真实路径
            uid : 用户id
            gid : 用户组id
            size : 文件大小
            mode : 文件的保护模式
            ctime : 文件创建时间. Defaults to None.

        Returns:
            bool: 结果
        """
        if ctime is None:       # 如果创建时间为空，获取当前时间
            ctime = time.time()
        if not path.strip('/'): # 如果路径为空
            return False
        try:
            dir = self.get_path(os.path.dirname(path.strip('/')))   # 获取目录路径
        except IndexError:
            return False
        dir.append([os.path.basename(path), T_DIR, uid, gid, size, mode,
            ctime, [], None, None])     # 添加
        return True

    def is_dir(self, path):
        """判断指定文件受否为目录

        Args:
            path (str): 路径

        Returns:
            bool: 结果
        """
        if path == '/':     # 如果为根目录
            return True
        dir = self.get_path(os.path.dirname(path))      # 获取虚假文件系统中的文件路径
        l = [x for x in dir
            if x[A_NAME] == os.path.basename(path) and
            x[A_TYPE] == T_DIR]     # 存在，且为目录
        if l:
            return True
        return False

    def file_contents(self, target, count = 0):
        """获取文件内容

        Args:
            target (str): 文件路径
            count (int, optional): 递归计数器. Defaults to 0.

        Raises:
            TooManyLevels: 递归次数过多报错
            FileNotFound: 文件未找到报错

        Returns:
            str: 文件内容
        """
        if count > 10:  # 递归次数超过10
            raise TooManyLevels
        path = self.parse_path(target, os.path.dirname(target))
        print('%s parse into %s' % (target, path))
        if not path or not self.exists(path):   # 如果文件不存在
            raise FileNotFound
        f = self.get_file(path)      # 获取文件节点
        if f[A_TYPE] == T_LINK:     # 如果文件为链接文件，重新使用指向的文件
            return self.file_contents(f[A_TARGET], count + 1)

        realfile = self.realfile(f, '%s/%s' % \
            (config().get('filesystem', 'path'), path))     # 获取真实文件
        if realfile:
            return open(realfile, 'rb').read()  # 打开


if __name__ == "__main__":
    # 测试部分
    fs = pickle.load(open('filesystem', 'rb'))
    hfs = HoneyFilesystem(fs)
    print(hfs.file_contents("/etc/hosts"))
