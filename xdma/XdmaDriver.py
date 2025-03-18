# -*- coding: utf-8 -*-
# @Time    : 2024/6/5 23:39
# @Author  : ltr
# @Site    : 
# @File    : XdmaTest.py
# @Software: PyCharm 
# @Comment :

import os.path

from xdma.XdmaDeviceFile import *


class XdmaDriver:
    """XDMA设备驱动,包含几个可能存在的Device File的相关方法"""
    device_path: str
    h2c_devices: list[XdmaDeviceFile]
    c2h_devices: list[XdmaDeviceFile]
    dma_devices: list[XdmaDeviceFile]
    bypass_device: XdmaDeviceFile
    control_device: XdmaDeviceFile  # XDMA IP控制寄存器组,使用AXI-Lite接口
    user_device: XdmaDeviceFile  # XDMA 用户寄存器组,使用AXI-Lite接口

    def is_axi_st(self) -> bool:
        with self.control_device as control:
            return control.check_register_bit(0, 15)

    def __init__(self, device_index: int):
        self.device_path = get_device_paths()[device_index]
        self.channel_count = 1 if platform.system() == "Linux" else 4  # for windows, traversing up to 4 DMA channels
        print(f"device path={self.device_path}")
        self.h2c_devices, self.c2h_devices, self.dma_devices = [], [], []
        for i in range(self.channel_count):
            c2h_path = f"{self.device_path}{FILE_SEPERATOR}c2h_{i}"
            h2c_path = f"{self.device_path}{FILE_SEPERATOR}h2c_{i}"
            self.c2h_devices.append(XdmaDeviceFile(read_device_file_path=c2h_path))
            self.h2c_devices.append(XdmaDeviceFile(write_device_file_path=h2c_path))
            self.dma_devices.append(
                XdmaDeviceFile(read_device_file_path=c2h_path, write_device_file_path=h2c_path))
        self.bypass_path = f"{self.device_path}{FILE_SEPERATOR}bypass"
        self.bypass_device = XdmaDeviceFile(self.bypass_path, self.bypass_path)
        self.control_path = f"{self.device_path}{FILE_SEPERATOR}control"
        self.control_device = XdmaDeviceFile(self.control_path, self.control_path)
        self.user_path = f"{self.device_path}{FILE_SEPERATOR}user"
        self.user_device = XdmaDeviceFile(self.user_path, self.user_path)

        # list DMA subsystem information
        self.dma_config = "AXI4-Stream" if self.is_axi_st() else "AXI4 Memory Mapped"
        self.all_device_files = self.h2c_devices + self.c2h_devices + self.dma_devices + [self.bypass_device,
                                                                                          self.control_device,
                                                                                          self.user_device]
        print(f"DMA configured as {self.dma_config}, containing following device files:")
        for device_file in self.all_device_files:
            if device_file.open():
                print(f"\t{device_file}")
                device_file.close()

    def show_info(self):
        # TODO: more status information
        print("\nInformation in register space will be listed below:")
        with self.control_device as control:
            for i in range(7):
                base = i * 0x1000
                channel_identifier = control.read_register_field(0 + base, 16, 4)
                match channel_identifier:
                    case 0:
                        print("\tH2C blocks")
                        self.print_channel(base)
                    case 1:
                        print("\tC2H blocks")
                        self.print_channel(base)
                    # TODO: for more information of other blocks, see PG195, DMA/Bridge Subsystem for PCI Express

    def print_channel(self, base):
        for i in range(self.channel_count):
            channel_base = base + i * 0x100
            identifier = self.control_device.read_register_field(channel_base + 0x00, 0, 32)
            if identifier & 0x1cf00000:  # for unused channel, identifier = 0x00000000
                print(f"\t\tchannel id: {self.control_device.read_register_field(channel_base + 0x00, 8, 4)}")
                print(f"\t\t\tstreaming: {self.control_device.check_register_bit(channel_base + 0x00, 15)}")


if __name__ == '__main__':
    xdma_device = XdmaDriver(0)
    xdma_device.show_info()
    xdma_device.dma_devices[0].test_integrity()
    xdma_device.dma_devices[0].test_bandwidth(8 << 20)
