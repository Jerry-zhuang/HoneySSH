

def str2byte(data):
    """将字符串类型转为字节类型
       由于twisted内，许多协议的传输采用byte类型，所以需要将一些str转为byte

    Args:
        data (_type_): 输入

    Returns:
        _type_: 输出
    """
    if isinstance(data,str):  return bytes(data, encoding = 'utf8')
    if isinstance(data,dict):   return {k:str2byte(v) for k,v in data.items()}
    if isinstance(data,tuple):  return (str2byte(i) for i in data)
    if isinstance(data,list):  return [str2byte(i) for i in data]

    return data