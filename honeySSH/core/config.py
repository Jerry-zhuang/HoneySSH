import configparser, os

def config(cfgfile = "setup.conf"):
    """读取设置函数

    Args:
        cfgfile (str, optional): 配置文件路径. Defaults to "setup.conf".

    Returns:
        cfg: 返回配置文件
    """
    cfg = configparser.ConfigParser()
    if os.path.exists(cfgfile):
        cfg.read(cfgfile)
        return cfg
    return None