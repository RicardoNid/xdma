# -*- coding: utf-8 -*-
# @Time    : 2024/6/19 18:40
# @Author  : ltr
# @Site    : ${SITE}
# @File    : XdmaSpiController.py
# @Software: PyCharm 
# @Comment :
from abc import abstractmethod

from XdmaWindowsDeviceFile import *


class SpiController(XdmaWindowsDeviceFile):
    def write_byte(self, addr: int, value: int):
        assert 0 <= value <= 0xFF, "bad register value"
        byte = np.array([value], dtype=np.uint8)
        self.write(addr, byte)

    def read_byte(self, addr: int):
        reg = np.ones(1, dtype=np.uint8)
        self.read(addr, reg)
        return reg[0]

    def set_byte(self, addr: int, value: int):
        assert 0 <= value <= 0xFF, "bad register value"
        self.write_byte(addr, value)
        value_after_write = self.read_byte(addr)
        if value_after_write != value:
            print(f"expected = {hex(value)}, actual = {hex(value_after_write)} @ {hex(addr)}")

    def show_default(self):
        self.write_byte(0x0000, 0x01)
        self.write_byte(0x0000, 0x00)
        time.sleep(0.1)
        for i in range(0x0E):
            print(f"register value = {hex(self.read_byte(i))} @ {hex(i)}")

    @abstractmethod
    def exists(self):
        # check device existence by reading/writing a harmless register
        pass
