# HoneySSH 开发文档

## 一、项目结构

```shell
├── doc                             # 开发文档
├── docker-compose.yml              # docker-compose 配置文档
├── Dockerfile                      # Dockerfile 配置文档
├── filesystem                      # 虚假的文件系统，pickle序列化导出
├── hfs                             # 虚假文件系统的文件内容
│   ├── etc
│   │   ├── group
│   │   ├── hostname
│   │   ├── hosts
│   │   ├── issue
│   │   ├── passwd
│   │   ├── resolv.conf
│   │   └── shadow
│   └── proc
│       ├── cpuinfo
│       ├── meminfo
│       └── version
├── honeySSH                        # 代码部分
│   ├── commands                    # 蜜罐内具体指令的实现
│   │   ├── base.py                 # 基础的一些指令，如cd, ls, whoami等
│   │   ├── filesystem.py           # 与文件系统操作相关的指令，如：cp, mv, touch, mkdir等
│   │   ├── __init__.py
│   │   └── ping.py                 # ping指令
│   ├── core                        # 核心代码部分
│   │   ├── config.py               # 导入配置文件
│   │   ├── honeyCMD.py             # 上面指令系统开发的父类，写了细写指令的基础部分
│   │   ├── honeyFilesystem.py      # 虚假文件系统的相关代码
│   │   ├── honeyProtocol.py        # 重构twisted的terminal相关类，插入我们的文件系统、指令系统和日志系统
│   │   ├── __init__.py
│   │   ├── log.py                  # 日志记录的相关代码
│   │   ├── ssh.py                  # 重构twisted的ssh相关类，插入我们的文件系统、指令系统和日志系统
│   │   └── utils.py                # 工具相关函数
│   └── __init__.py
├── log                             # 日志存储地址
├── README.md
├── requirements.txt
├── run.py                          # 启动文件
├── setup.conf                      # 配置文件
├── ssh-keys                        # 一些公钥私钥的存储
│   ├── client_rsa
│   ├── client_rsa.pub
│   ├── ssh_host_rsa_key
│   └── ssh_host_rsa_key.pub
└── utils                           # 项目构建用到的一些文件，来源为kippo
    ├── createfs.py
    └── fsctl.py
```