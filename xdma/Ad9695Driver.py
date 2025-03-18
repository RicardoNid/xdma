# -*- coding: utf-8 -*-
# @Time    : 2024/6/19 18:41
# @Author  : ltr
# @Site    : ${SITE}
# @File    : Ad9695Driver.py
# @Software: PyCharm 
# @Comment :

import random

from xdma.XdmaSpiController import SpiController
from xdma.XdmaDeviceFile import *


class Ad9695Driver(SpiController):
    SCRATCH_PAD = 0x000A  # a register for software debug
    PLL_STATUS = 0x056F

    def exists(self):
        original = self.read_byte(self.SCRATCH_PAD)
        value = random.randint(0, 128)
        self.write_byte(self.SCRATCH_PAD, value)
        pass_0 = self.read_byte(self.SCRATCH_PAD) == value
        self.write_byte(self.SCRATCH_PAD, original)
        pass_1 = self.read_byte(self.SCRATCH_PAD) == original
        return pass_0 and pass_1

    def __init__(self, read_device_file_path, write_device_file_path, base_address):
        super().__init__(read_device_file_path, write_device_file_path, base_address, 0x4_0000)

    def soft_reset(self):
        self.write_byte(0x0000, 0x81)  # soft reset,这个寄存器是对称的,因为这个寄存器决定了SPI的MSB/LSB first设置,它必须兼容MSB/LSB first
        time.sleep(0.1)

    def datapath_soft_reset(self):
        self.write_byte(0x0001, 0x02)  # datapath soft reset
        time.sleep(0.1)

    def check_accessibility(self):
        assert self.read_byte(0x0004) == 0xDE and self.read_byte(0x0005) == 0x00, "AD9695 not accessible"

    def set_fast_detect(self, function: str):
        function_value = 0
        match function:
            case "force 0":
                fast_detect = True
                function_value = 9
            case "force 1":
                fast_detect = True
                function_value = 13
            case "detect":
                fast_detect = True
                function_value = 1
            case "LMFC":
                fast_detect = False

        if fast_detect:
            self.set_byte(0x0040, 0x00)  # set pin function as fast detect(disabled by default)
            self.set_byte(0x0245, function_value)  # enable fast detect pins
        else:
            self.set_byte(0x0040, 0x01)  # set pin function as GPIO for LMFC

    def check_status(self):
        assert is_bit_set(self.read_byte(self.PLL_STATUS), 7) and not is_bit_set(self.read_byte(self.PLL_STATUS), 3), "AD9695: bad status"

    def set_jesd204_test_pattern(self, test_mode: str):
        match test_mode:
            case "normal":
                self.set_byte(0x0573, 0x00)
            case "ramp":
                self.set_byte(0x0573, 0x08)
            case "toggle":
                self.set_byte(0x0573, 0x02)

    def init_for_das(self, startup_mode: str = "normal"):
        match startup_mode:
            case "normal":
                self.set_byte(0x0002, 0x00)  # power-up
            case "standby":
                self.set_byte(0x0002, 0x02)  # standby mode, disable datapath, sending known data through JESD204B interface
        self.soft_reset()
        self.datapath_soft_reset()
        # 设置量程
        # self.set_byte(0x1910, 0x00)  # 设置量程为最大值,2.04Vpp
        self.set_byte(0x1910, 0x0A)  # 设置量程为最小值,1.36Vpp
        # 设置直流耦合,参见 "performing SPI writes for dc coupling operation" in AD9695 manual
        self.set_byte(0x1908, 0x04)  # 设置耦合方式为DC
        self.set_byte(0x18A6, 0x00)  # turn off the voltage reference
        self.set_byte(0x18E6, 0x00)  # turn off the temperature diode export
        self.set_byte(0x18E0, 0x02)
        self.set_byte(0x18E1, 0x14)
        self.set_byte(0x18E2, 0x14)
        self.set_byte(0x18E3, 0x40)
        self.set_byte(0x18E3, 0x54)
        time.sleep(0.1)
        # 设置JESD204B参数,参见Use the following procedure to configure the output
        self.write_byte(0x0571, 0x15)  # turn off the link, sending K28.5 in standby mode
        self.set_byte(0x056E, 0x00)  # 线速率范围,6.75 Gbps to 13.5 Gbps
        self.set_byte(0x058B, 0x83)  # turn on scrambling, lanes per link(L) = 4
        self.set_byte(0x058C, 0x00)  # octets per frames(F) = 1
        self.set_byte(0x058D, 0x1F)  # K = 32
        self.set_byte(0x058E, 0x01)  # M = 2
        self.set_byte(0x058F, 0x0D)  # CS = 0, N = 14
        self.set_byte(0x0120, 0x02)  # SYSREF±,continuous
        # self.set_byte(0x0120, 0x04)  # SYSREF±,N-shot
        self.write_byte(0x0571, 0x14)  # turn on the link, sending K28.5 in standby mode
        # setting up JESD204B test mode

        time.sleep(0.1)
        # JESD204B初始化,参见Table 34
        self.set_byte(0x1228, 0x4F)
        self.set_byte(0x1228, 0x0F)
        self.set_byte(0x1222, 0x00)
        self.set_byte(0x1222, 0x04)
        self.set_byte(0x1222, 0x00)
        self.set_byte(0x1262, 0x08)
        self.set_byte(0x1262, 0x00)
        time.sleep(0.1)
        self.set_fast_detect("LMFC")  # 设置fast detect引脚功能
        # self.set_byte(0x0572, 0x20) # invert syncinb
        # self.set_byte(0x0572, 0x80) # force CGS
        time.sleep(1.0)
        return self.init_done()

    def init_done(self):
        pll_lock = is_bit_set(self.read_byte(self.PLL_STATUS), 7)
        pll_not_loss = not is_bit_set(self.read_byte(self.PLL_STATUS), 3)
        return pll_lock and pll_not_loss

    def show_info(self):
        print(f"\nAD9695 info:")
        print(f"\n\tscrambling enabled: {is_bit_set(self.read_byte(0x058B), 0)}")
        print(f"\toctets per frame(F): {get_bits(self.read_byte(0x058C), 0, 8) + 1}")
        print(f"\tframes per multiframe(K): {get_bits(self.read_byte(0x058D), 0, 5) + 1}")
        print(f"\tlanes in use(L): {get_bits(self.read_byte(0x058B), 0, 4) + 1}")
        print(f"\tsubclass: {get_bits(self.read_byte(0x0590), 5, 3)}")
        pll_stauts = self.read_byte(self.PLL_STATUS)
        print(f"\tPLL lock: {is_bit_set(pll_stauts, 7)}")
        print(f"\tLoss of lock: {is_bit_set(pll_stauts, 3)}")


if __name__ == '__main__':
    device_file = os.path.join(get_device_paths()[0], "user")
    ad9695 = Ad9695Driver(device_file, device_file, 0x8_0000)
    ad9695.show_info()
    ad9695.init_for_das()
    ad9695.show_info()
