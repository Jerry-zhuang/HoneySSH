# HoneySSH

HoneySSH 是一个低交互的SSH蜜罐，使用twisted网络开发工具，借鉴kippo的开发思想进行开发。

## 一、功能

1. 可以为文件系统中的文件添加虚假的内容，当攻击者使用cat查看文件时返回
2. 具有一个较为完整的文件系统和部分常用的指令。
3. 攻击者爆破使用的账号口令可被蜜罐捕获
4. 攻击者执行的指令将被蜜罐存储下来。

## 二、启动

### 2.1 在本机启动

如果没有安装虚拟环境virtualenv，则需要安装：

```bash
pip install virtualenv
```

接着是启动：

```bash
virtualenv venv
source venv/bin/activate
pip install -r requirements.txt
python3 run.py
```

默认允许在5022端口，如若需要，可使用nginx等将服务映射到22端口。

### 2.2 docker compose 启动

需要安装docker以及docker-compose:

ubuntu
```bash
sudo apt install docker.io docker-compose
```

然后在项目根目录下执行：
```bash
sudo docker-compose up -d
```

等待一段时间，便能允许，如若需要，可以在docker-compose.yml中修改映射端口。