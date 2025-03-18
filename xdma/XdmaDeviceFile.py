# -*- coding: utf-8 -*-
# @Time    : 2024/5/29 18:15
# @Author  : ltr
# @Site    : 
# @File    : xdma_windows_driver.py
# @Software: PyCharm 
# @Comment :
import mmap
import os
import threading
import time
from threading import Thread

from xdma.FileOperations import *
from xdma.Register32 import Register32

FILE_SEPERATOR = "_" if platform.system() == "Linux" else "/"


####################
# Device file abstraction
####################

class XdmaDeviceFile:
    def __init__(self, read_device_file_path: str = None, write_device_file_path: str = None, base_address: int = 0,
                 capacity: int = 0x1_0000_0000):
        """
        There are four possible scenarios:

        Read-only device: read_device_file_path only
        Write-only device: write_device_file_path only
        A read/write device consisting of read-only and write-only devices mapped to the same address space: read_device_file_path != write_device_file_path
        Read/write device: read_device_file_path = write_device_file_path
        """
        assert base_address >= 0 and capacity > 0

        self.read_path = read_device_file_path
        self.write_path = write_device_file_path
        self.read_handle = INVALID_HANDLE_VALUE  # file descriptor for reading
        self.write_handle = INVALID_HANDLE_VALUE  # file descriptor for writing
        self.base_address = base_address
        self.max_address = self.base_address + capacity

    def __enter__(self):
        # self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # self.close()
        pass

    def read_exists(self):
        return self.read_path is not None

    def write_exists(self):
        return self.write_path is not None

    def exists(self):
        return self.read_exists() or self.write_exists()

    def __str__(self):
        read_name = self.read_path.split('\\')[-1] if self.read_path else 'None'
        write_name = self.write_path.split('\\')[-1] if self.write_path else 'None'
        return f"device file read @ {read_name}, write @ {write_name}"

    ####################
    # For AXI MM
    ####################

    def open(self):
        assert (self.read_path is not None) or (self.write_path is not None)
        if self.read_path == self.write_path:
            self.read_handle = get_handle(self.read_path, GENERIC_RW)
            self.write_handle = self.read_handle
        else:
            if self.read_path is not None:
                self.read_handle = get_handle(self.read_path, GENERIC_READ)
            if self.write_path is not None:
                self.write_handle = get_handle(self.write_path, GENERIC_WRITE)
        return self.read_handle != INVALID_HANDLE_VALUE or self.write_handle != INVALID_HANDLE_VALUE

    def close(self):
        if self.read_handle != INVALID_HANDLE_VALUE:
            close_handle(self.read_handle)
            self.read_handle = INVALID_HANDLE_VALUE
        if self.write_handle != INVALID_HANDLE_VALUE and self.read_path != self.write_path:
            close_handle(self.write_handle)
            self.write_handle = INVALID_HANDLE_VALUE

    def seek(self, handle: int, addr: int):
        if addr > 0:
            if addr + self.base_address < self.max_address:
                seek_handle(handle, addr + self.base_address)
            else:
                raise IndexError(f'target address {hex(addr)} out of range')
        else:
            pass  # for stream read/write

    def write(self, addr: int, data: np.ndarray):
        self.open()
        if self.write_exists():
            if addr >= 0:
                self.seek(handle=self.write_handle, addr=addr)
            bytes_write = write_to_handle(self.write_handle, data, data.nbytes)
            self.close()
            return bytes_write
        else:
            raise FileNotFoundError(f'{self.write_path} not found.')

    def read(self, addr: int, buffer: np.ndarray):
        self.open()
        if self.read_exists():
            if addr >= 0:
                self.seek(handle=self.read_handle, addr=addr)
            bytes_read = read_from_handle(self.read_handle, buffer, buffer.nbytes)
            self.close()
            return bytes_read
        else:
            raise FileNotFoundError(f'{self.read_path} not found.')

    ####################
    # For AXI ST
    ####################
    def write_stream(self, data: np.ndarray):
        self.write(-1, data)

    def read_stream(self, buffer: np.ndarray):
        self.read(-1, buffer)

    ####################
    # For AXI LITE, based on mmap
    ####################
    # Due to the existence of alignment mechanisms, it is not possible to directly read or write to a portion of a 32-bit register. Ultimately, the _read_register and _write_register methods must be used.
    def _read_register(self, addr: int, access_width='w'):
        addr = addr + self.base_address
        if addr >= self.max_address:
            raise IndexError(f'target address {hex(addr)} out of range')

        # 打开字符设备
        fd = os.open(self.read_path, os.O_RDWR | os.O_SYNC)
        if fd == -1:
            print(f"打开字符设备 {self.read_path} 失败: {os.strerror(os.errno)}")
            return None
        # 获取页面大小
        pgsz = os.sysconf('SC_PAGE_SIZE')

        offset = addr % pgsz
        target_aligned = addr & ~(pgsz - 1)

        # 内存映射
        map_size = offset + 4
        with mmap.mmap(fd, map_size, mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE, offset=target_aligned) as mm:
            mm.seek(offset)
            if access_width == 'b':
                result = mm.read_byte()
            else:
                result = int.from_bytes(mm.read(4), byteorder='little', signed=False)

        # 关闭文件描述符
        os.close(fd)
        return result

    def _write_register(self, addr: int, value: int, access_width='w'):
        # print(f"local addr = {hex(addr)}")
        addr = addr + self.base_address
        if addr >= self.max_address:
            raise IndexError(f'target address {hex(addr)} out of range')
        # 打开字符设备
        fd = os.open(self.write_path, os.O_RDWR | os.O_SYNC)
        if fd == -1:
            print(f"打开字符设备 {self.write_path} 失败: {os.strerror(os.errno)}")
            return False

        # 获取页面大小
        pgsz = os.sysconf('SC_PAGE_SIZE')
        offset = addr % pgsz
        target_aligned = addr & ~(pgsz - 1)
        # print(f"addr = {hex(addr)}, page size = {pgsz}, offset = {offset}, target_aligned = {target_aligned}")

        # 内存映射
        map_size = offset + 4
        with mmap.mmap(fd, map_size, mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE, offset=target_aligned) as mm:
            mm.seek(offset)
            if access_width == 'b':
                mm.write_byte(value)
            else:
                mm.write(int(value).to_bytes(4, byteorder='little', signed=False))

        # 关闭文件描述符
        os.close(fd)
        return True

    @staticmethod
    def _update_field(reg_value: np.uint32, start: int, length: int, field_value: np.uint32) -> np.uint32:
        end = length + start
        mask = ((1 << (end - start)) - 1) << start
        mask = np.uint32(mask)
        reg_value &= ~mask  # 将需要修改的部分置0
        field_value = (field_value << start) & mask
        return reg_value | field_value

    def read_register_field(self, addr: int, start: int, length: int) -> np.uint32:
        return get_bits(self._read_register(addr), start, length)

    def write_register_field(self, addr: int, start: int, length: int, value: np.uint32, strict: bool = True):
        current_value = self._read_register(addr)
        new_value = self._update_field(current_value, start, length, value)
        self._write_register(addr, new_value)
        if strict:
            actual_value = self._read_register(addr)
            assert actual_value == new_value, f"write failed: expected = {hex(new_value)}, actual = {hex(actual_value)}"

    def check_register_bit(self, addr: int, position: int):
        return is_bit_set(self._read_register(addr), position)

    def read_register32(self, reg: Register32):
        reg.from_value(self._read_register(reg.address))
        return reg

    def write_register32(self, reg: Register32):
        self._write_register(reg.address, reg.to_value())

    ####################
    # Self-test for AXI MM
    ####################

    def test_integrity(self):
        if self.read_exists() and self.write_exists():
            test_data_size = 8192
            source = np.random.randint(0, 256, size=test_data_size, dtype=np.int16)
            target = np.empty(shape=test_data_size, dtype=np.int16)
            addr = np.random.randint(0, self.max_address - test_data_size, dtype=np.int64)
            self.write(addr, source)
            self.read(addr, target)
            data_match = (source == target).all()
            if data_match:
                print(f"integrity: passed")
            else:
                print(f"integrity: failed, bad data integrity")
                print(f"expected = {source}, actual = {target}")
        else:
            print(f"integrity: skipped")

    def to_device_thread(self, buf: np.ndarray, times: int):
        for i in range(times):
            self.write(0, buf)

    def from_device_thread(self, buf: np.ndarray, times: int):
        for i in range(times):
            self.read(0, buf)

    def test_bandwidth(self, block_size):

        block_count = 1000
        source = np.random.randint(0, 256, size=block_size, dtype=np.uint8)
        target = np.random.randint(0, 256, size=block_size, dtype=np.uint8)
        if self.read_exists():
            device_thread_handle = threading.Thread(target=self.from_device_thread, args=(target, block_count))
            start = time.time()
            device_thread_handle.start()
            device_thread_handle.join()
            time_elapsed = time.time() - start
            print(
                f"carrier to host bandwidth @ {block_size / 1024}KB block: {block_count * block_size / (1 << 20) / time_elapsed} MB/s")
        if self.write_exists():
            device_thread_handle: Thread = threading.Thread(target=self.to_device_thread, args=(source, block_count))
            start = time.time()
            device_thread_handle.start()
            device_thread_handle.join()
            time_elapsed = time.time() - start
            print(
                f"host to carrier bandwidth @ {block_size / 1024}KB block: {block_count * block_size / (1 << 20) / time_elapsed} MB/s")

    ####################
    # Factories
    ####################
    def remap(self, base_address: int, capacity: int):
        return XdmaDeviceFile(self.read_path, self.write_path, base_address, capacity)


import os
import sys
import mmap


def read_from_device(device, address, access_width):
    # 打开字符设备
    fd = os.open(device, os.O_RDWR | os.O_SYNC)
    if fd == -1:
        print(f"打开字符设备 {device} 失败: {os.strerror(os.errno)}")
        return None

    # 获取页面大小
    pgsz = os.sysconf('SC_PAGE_SIZE')
    # pgsz = 0x1_0000_0000
    offset = address % pgsz
    target_aligned = address & ~(pgsz - 1)

    print(f"offset = {hex(offset)}")

    # 内存映射
    map_size = offset + 4
    with mmap.mmap(fd, map_size, mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE, offset=target_aligned) as mm:
        mm.seek(offset)

        # 根据访问宽度读取数据
        if access_width == 'b':
            result = mm.read_byte()
        elif access_width == 'h':
            result = int.from_bytes(mm.read(2), byteorder='little', signed=False)
        elif access_width == 'w':
            result = int.from_bytes(mm.read(4), byteorder='little', signed=False)
        else:
            print("不支持的访问宽度，默认使用32位 (word)")
            result = int.from_bytes(mm.read(4), byteorder='little', signed=False)

    # 关闭文件描述符
    os.close(fd)
    return result


def write_to_device(device, address, data, access_width):
    # 打开字符设备
    fd = os.open(device, os.O_RDWR | os.O_SYNC)
    if fd == -1:
        print(f"打开字符设备 {device} 失败: {os.strerror(os.errno)}")
        return False

    # 获取页面大小
    pgsz = os.sysconf('SC_PAGE_SIZE')
    # pgsz = 0x1_0000_0000
    offset = address % pgsz
    target_aligned = address & ~(pgsz - 1)

    # 内存映射
    map_size = offset + 4
    with mmap.mmap(fd, map_size, mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE, offset=target_aligned) as mm:
        mm.seek(offset)

        # 根据访问宽度写入数据
        if access_width == 'b':
            mm.write_byte(data)
        elif access_width == 'h':
            mm.write(data.to_bytes(2, byteorder='little', signed=False))
        elif access_width == 'w':
            mm.write(data.to_bytes(4, byteorder='little', signed=False))
        else:
            print("不支持的访问宽度，默认使用32位 (word)")
            mm.write(data.to_bytes(4, byteorder='little', signed=False))

    # 关闭文件描述符
    os.close(fd)
    return True


if __name__ == '__main__':
    device_path = get_device_paths()[0]

    c2h_0_path = os.path.join(f"{device_path}_c2h_0")
    h2c_0_path = os.path.join(f"{device_path}_h2c_0")
    user_path = os.path.join(f"{device_path}_user")
    control_path = os.path.join(f"{device_path}_control")

    dma = XdmaDeviceFile(c2h_0_path, h2c_0_path, 0, 0x8000_0000)
    dma.test_integrity()
    dma.test_bandwidth(8 << 20)
    dma.test_bandwidth(1 << 20)

    # unidirectional
    user = XdmaDeviceFile(user_path, user_path, 0, 0x4_0000)
    rwTest = 0x10
    data = 0xEF
    user._write_register(rwTest, data)
    assert user._read_register(rwTest) == data

