import os

def get_storage_size(folder: str = "storage") -> int:
    """递归计算 storage 目录下所有文件的总大小 (字节)"""
    total_size = 0
    if not os.path.exists(folder):
        return 0
    for dirpath, dirnames, filenames in os.walk(folder):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            # 排除链接等异常文件
            if os.path.exists(fp):
                total_size += os.path.getsize(fp)
    return total_size
