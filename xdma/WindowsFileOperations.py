# # -*- coding: utf-8 -*-
# # @Time    : 2024/10/05 16:48
# # @Author  : DAS
# # @Site    :
# # @File    : FileOperations.py
# # @Software: PyCharm
# # @Comment :
#
# import ctypes
# import os.path
# import platform
#
# import numpy as np
#
# ####################
# # C function parameters
# ####################
#
# GENERIC_READ = 0x80000000
# GENERIC_WRITE = 0x40000000
# OPEN_EXISTING = 3
# #
# INVALID_HANDLE_VALUE = 0xffffffffffffffff
#
# FILE_BEGIN = 0
# FILE_CURRENT = 1
#
# ####################
# # C functions and its python interface
# ####################
# if platform.system() == "Windows":
#     CreateFile = ctypes.windll.kernel32.CreateFileA
#     ReadFile = ctypes.windll.kernel32.ReadFile
#     WriteFile = ctypes.windll.kernel32.WriteFile
#     SetFilePointer = ctypes.windll.kernel32.SetFilePointer
#     CloseHandle = ctypes.windll.kernel32.CloseHandle
#
#     # specify argument types and return type for these functions
#     CreateFile.argtypes = [ctypes.c_char_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p,
#                            ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p]
#     CreateFile.restype = ctypes.c_void_p
#
#     ReadFile.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint32,
#                          ctypes.POINTER(ctypes.c_uint32), ctypes.c_void_p]
#     ReadFile.restype = ctypes.c_int
#
#     WriteFile.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint32,
#                           ctypes.POINTER(ctypes.c_uint32), ctypes.c_void_p]
#     WriteFile.restype = ctypes.c_int
#
#     SetFilePointer.argtypes = [ctypes.c_void_p, ctypes.c_long, ctypes.POINTER(ctypes.c_long), ctypes.c_uint32]
#     SetFilePointer.restype = ctypes.c_uint32
#
#
# # TODO: implement this part by ctypes(rather than through .dll)
# def get_device_paths():
#     dll_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'xdma_utils.dll')
#     clib = ctypes.CDLL(dll_path)
#     clib.get_device_paths.argtypes = [ctypes.POINTER(ctypes.c_char_p), ctypes.POINTER(ctypes.c_int)]
#
#     device_paths = (ctypes.c_char_p * 128)()  # mutable buffer for the pointer, up to 128 xdma devices
#     num_paths = ctypes.c_int()  # return value
#
#     clib.get_device_paths(device_paths, ctypes.byref(num_paths))  # call the function
#     paths = [device_paths[i].decode('utf-8') for i in range(num_paths.value)]  # convert c-style string in buffer into python list of str
#     return paths
#
#
# def get_handle(path, access_flag):
#     return CreateFile(path.encode('utf-8'), access_flag, 0, None, OPEN_EXISTING, 0, None)
#
# def seek_handle(handle, position, mode=FILE_BEGIN):
#     # SetFilePointer requires 2 32bit address(low & high)
#     # updated high address will be given by in-place modification on high
#     # updated low address will be given by the return value
#     pos_high = ctypes.c_long(position >> 32)
#     pos_low = position & 0xFFFFFFFF
#     pos_low = SetFilePointer(handle, pos_low, ctypes.byref(pos_high), mode)
#     if pos_low == INVALID_HANDLE_VALUE:
#         raise ctypes.WinError()
#     new_position = (pos_high.value << 32) | pos_low
#     if position != new_position:
#         print(f"bad seek {new_position} / {position}")
#     return (pos_high.value << 32) | pos_low
#
# # 封装read和write,将数据接口改为numpy矩阵
# def call_with_func(winfunc, *args):
#     result = winfunc(*args)
#     if not result and winfunc not in (ReadFile, WriteFile):
#         raise ctypes.WinError()
#     return result
#
# def read_from_handle(handle, buf: np.ndarray, nbytes):
#     nread = ctypes.c_uint32()
#     call_with_func(ReadFile, handle, buf.ctypes.data_as(ctypes.c_char_p), nbytes, ctypes.byref(nread), None)
#     if int(nread.value) != int(nbytes):
#         print(f"bad read {nread.value} / {nbytes}")
#     return nread.value
#
#
# def write_to_handle(handle, buf: np.ndarray, nbytes):
#     nwritten = ctypes.c_uint32()
#     call_with_func(WriteFile, handle, buf.ctypes.data_as(ctypes.c_char_p), nbytes, ctypes.byref(nwritten), None)
#     if int(nwritten.value) != int(nbytes):
#         print(f"bad write {nwritten.value} / {nbytes}")
#     return nwritten.value
#
#



