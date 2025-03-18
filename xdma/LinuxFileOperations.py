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
GENERIC_WRITE = os.O_WRONLY  # do not create when device file doesn't exist
GENERIC_RW = os.O_RDWR

INVALID_HANDLE_VALUE = -1  # catch OSError and return this value for consistency
FILE_BEGIN = os.SEEK_SET


def get_handle(device_path, access):
    try:
        handle = os.open(device_path, access)
        return handle
    except OSError as e:
        print(f"Failed to open {device_path}: {e}")
        return INVALID_HANDLE_VALUE


def seek_handle(handle, offset, how=FILE_BEGIN):
    new_pos = os.lseek(handle, offset, how)
    return new_pos


def call_with_func(winfunc, *args):
    result = winfunc(*args)
    return result


def read_from_handle(handle, buf: np.ndarray, nbytes: int) -> int:
    """将文件中的数据读入NumPy数组"""
    data = os.read(handle, nbytes)
    nread = len(data)
    buf[:] = np.frombuffer(data, dtype=buf.dtype).reshape(buf.shape)
    if nread != nbytes:
        print(f"bad read {nread} / {nbytes}")
    return nread


def write_to_handle(handle, buf: np.ndarray, nbytes: int) -> int:
    """将NumPy数组中的数据写入文件"""
    nwritten = os.write(handle, buf.flatten().tobytes())
    if nwritten != nbytes:
        print(f"bad write {nwritten} / {nbytes}")
    return nwritten


def close_handle(handle):
    os.close(handle)
