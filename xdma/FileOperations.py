# -*- coding: utf-8 -*-
# @Time    : 2024/10/05 16:48
# @Author  : DAS
# @Site    :
# @File    : FileOperations.py
# @Software: PyCharm
# @Comment :

import platform
import numpy as np

####################
# Platform dependent file operations
####################

from xdma import LinuxFileOperations
from xdma import WindowsFileOperations


def get_platform_specific_module():
    system = platform.system()
    if system == 'Windows':
        return WindowsFileOperations
    elif system in ['Linux', 'Darwin']:  # regard Darwin as Linux
        return LinuxFileOperations
    else:
        raise NotImplementedError(f"Unsupported OS: {system}")


# 动态加载适合当前平台的函数模块
platform_module = get_platform_specific_module()

# 从所选模块中导入特定于平台的函数
GENERIC_READ = platform_module.GENERIC_READ
GENERIC_WRITE = platform_module.GENERIC_WRITE
INVALID_HANDLE_VALUE = platform_module.INVALID_HANDLE_VALUE
get_device_paths = platform_module.get_device_paths
get_handle = platform_module.get_handle
seek_handle = platform_module.seek_handle
close_handle = platform_module.close_handle
write_to_handle = platform_module.write_to_handle
read_from_handle = platform_module.read_from_handle


####################
# Platform independent bit operations
####################


def is_bit_set(reg, position):
    bit = (1 << position)
    return (reg & bit) == bit


def get_bits(reg, start, length):
    mask = ((1 << length) - 1) << start
    return (reg & mask) >> start


if __name__ == '__main__':
    c2h = get_handle("/dev/xdma0_c2h_0", GENERIC_READ)
    h2c = get_handle("/dev/xdma0_h2c_0", GENERIC_WRITE)

    data = np.array([1, 2, 3, 4, 5, 6, 7, 8], dtype=np.uint8)
    result = np.empty_like(data)
    seek_handle(h2c, 2, 0)
    print(result)
    size = write_to_handle(h2c, data, data.nbytes)
    read_from_handle(c2h, result, data.nbytes)
    print(result)
    close_handle(c2h)
    close_handle(h2c)
    print(get_device_paths())
