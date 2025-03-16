import os
import numpy as np


def get_device_paths():
    xdma_device_files = [f"/dev/{device}" for device in os.listdir("/dev") if device.startswith("xdma")]
    xdma_root_device_files = list(set([device.split("_")[0] for device in xdma_device_files]))
    return xdma_root_device_files


####################
# Device file I/O functions
####################

GENERIC_READ = os.O_RDONLY
# GENERIC_WRITE = os.O_WRONLY | os.O_CREAT
GENERIC_WRITE = os.O_WRONLY  # do not create when device file doesn't exist
INVALID_HANDLE_VALUE = -1  # catch OSError and return this value for consistency
FILE_BEGIN = 0


def get_handle(device_path, access):
    try:
        handle = os.open(device_path, access)
        return handle
    except OSError as e:
        print(f"Failed to open {device_path}: {e}")
        return INVALID_HANDLE_VALUE


def seek_handle(handle, offset, whence=FILE_BEGIN):
    new_pos = os.lseek(handle, offset, whence)
    return new_pos


def call_with_func(winfunc, *args):
    result = winfunc(*args)
    return result


def read_from_handle(handle, buf: np.ndarray, nbytes: int) -> int:
    """
    从给定的文件描述符读取数据到NumPy数组。

    :param handle: 文件描述符
    :param buf: 目标NumPy数组
    :param nbytes: 要读取的字节数
    :return: 实际读取的字节数
    """
    # 使用buf.view将NumPy数组转换为字节视图
    nread = os.read(handle, nbytes)
    actual_nbytes = len(nread)
    if actual_nbytes > 0:
        # 将读取的数据复制到目标缓冲区
        buf[:actual_nbytes] = np.frombuffer(nread, dtype=buf.dtype, count=actual_nbytes) # FIXME: buffer is smaller than requested size when test integrity
    if actual_nbytes != nbytes:
        print(f"bad read {actual_nbytes} / {nbytes}")
    return actual_nbytes


def write_to_handle(handle, buf: np.ndarray, nbytes: int) -> int:
    """
    将NumPy数组中的数据写入给定的文件描述符。

    :param handle: 文件描述符
    :param buf: 源NumPy数组
    :param nbytes: 要写入的字节数
    :return: 实际写入的字节数
    """
    # 确保只尝试写入请求的字节数量
    data_to_write = buf[:nbytes].tobytes()
    nwritten = os.write(handle, data_to_write)
    if nwritten != nbytes:
        print(f"bad write {nwritten} / {nbytes}")
    return nwritten


def close_handle(handle):
    os.close(handle)
