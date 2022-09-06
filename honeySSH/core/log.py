import json, os, time
from re import L
from mimetypes import init
from honeySSH.core.config import config

# 日志格式
# {
#   "uuid":None,
#   "loginInfo":{
#     "ip":None,
#     "port": None,
#     "login time":None,
#     "username and password":None,
#     "remote SSH version":None
#   },
#   "commands":[],
#   "file":[]
# }
# 其中commands的格式
# {
#   "time":None,
#   "command":None
# }
# 其中file的格式
# {
#   "time":None,
#   "type":None,
#   "path":None
# }


class logger():

    def __init__(self, log_file, logintime) -> None:

        self.log_path = config().get("log", "log_path") + log_file
        self.time = time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(logintime))
        self.pw_path = config().get("log", "log_path") + self.time + "/" +log_file
        self.commands = []
        self.file = []
        self.log_json = {
                        "loginInfo":{
                            "ip":None,
                            "port": None,
                            "login time":self.time,
                            "username and password":self.pw_path,
                            "remote SSH version":None
                            },
                        "commands":self.commands,
                        "file":self.file
                        }
        self.command_json = {
                              "time":None,
                              "command":None
                            }
        self.file_json = {
                          "time":None,
                          "type":None,
                          "path":None
                        }
        print("[log] 创建日志文件：%s" % self.log_path)
        print("[log] 创建爆破账号密码记录文件：%s", self.pw_path)
        self.creat_password_file()
        self.write()

    def write(self):
        print("")
        f = open(self.log_path, 'w')
        json.dump(self.log_json, f)
        f.close()
        return self.log_json

    def read(self):
        f = open(self.log_path, 'r')
        self.log_json = json.load(f)
        f.close()
        return self.log_json

    def add_command(self, command, logpath):
        pass

    def add_file(self, file, logpath):
        pass

    def set_IP_Port(self, ip, port):
        self.read()
        self.log_json["loginInfo"]["ip"] = ip
        self.log_json["loginInfo"]["port"] = port
        self.write()
        print("[log] 存储IP地址和端口：%s:%s" % (ip, port))

    def set_ssh_version(self, version):
        self.read()
        self.log_json["loginInfo"]["remote SSH version"] = version
        self.write()
        print("[log] 存储远端ssh版本：%s" % version)
    
    def creat_password_file(self):
        dir = config().get("log", "log_path") + self.time + "/"
        if not os.path.exists(dir):
            os.mkdir(dir)

    def add_password(self, username, password):
        if not os.path.exists(self.pw_path):
            self.creat_password_file()
        f = open(self.pw_path, "a")
        f.write("%s %s \r\n" % (username, password))
        f.close()
