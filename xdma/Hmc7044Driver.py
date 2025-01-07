# -*- coding: utf-8 -*-
# @Time    : 2024/6/19 18:41
# @Author  : ltr
# @Site    : ${SITE}
# @File    : Hmc7044Driver.py
# @Software: PyCharm 
# @Comment :

import os
import random
import time

from xdma.XdmaSpiController import SpiController
from xdma.XdmaWindowsDeviceFile import *


class Hmc7044Driver(SpiController):
    # registers
    PLL1_REFERENCE_PRIORITY = 0x0014
    STATUS = 0x007D

    def __init__(self, read_device_file_path, write_device_file_path, base_address):
        super().__init__(read_device_file_path, write_device_file_path, base_address, 0x4_0000)

    def exists(self):
        priority = self.read_byte(self.PLL1_REFERENCE_PRIORITY)
        value = random.randint(0, 128)
        self.write_byte(self.PLL1_REFERENCE_PRIORITY, value)
        pass_0 = self.read_byte(self.PLL1_REFERENCE_PRIORITY) == value
        self.write_byte(self.PLL1_REFERENCE_PRIORITY, priority)
        pass_1 = self.read_byte(self.PLL1_REFERENCE_PRIORITY) == priority
        return pass_0 and pass_1

    def show_info(self):
        """
        展示寄存器默认值,通过对照这一方法输出的数值与手册中的默认值,我们可以验证read_byte方法的有效性
        """
        status_byte = self.read_byte(self.STATUS)
        print(f"\nHMC7044 status:")
        print(f"\n\tPLL2 locked (or disabled), but unsynchronized: {is_bit_set(status_byte, 4)}")
        print(f"\tPLL1 and PLL2 are locked: {is_bit_set(status_byte, 3)}")
        print(f"\tSYSREF of the HMC7044 is valid and locked: {is_bit_set(status_byte, 2)}")
        print(f"\tThe HMC7044 has been synchronized with an external sync pulse or a sync request from the SPI: {not is_bit_set(status_byte, 1)}")
        print(f"\tPLL2 near locked: {is_bit_set(status_byte, 0)}")

    def check_status(self):
        """
        检查HMC7044当前工作状态
        """
        status_byte = self.read_byte(0x007D)
        assert is_bit_set(status_byte, 3) and is_bit_set(status_byte, 2), "HMC7044: bad status"

    def soft_reset(self):
        """
        复位所有寄存器,dividers和FSMs
        """
        self.write_byte(0x0000, 0x01)
        self.write_byte(0x0000, 0x00)
        time.sleep(0.1)

    def set_gpo(self, gpo_id: int, function: str):
        """
        设置GPIO引脚作为output时的功能和模式
        """
        assert 1 <= gpo_id <= 4, "bad gpo id"
        addr = 0x50 + (gpo_id - 1)
        function_value = 0
        match function:
            case "lock":
                function_value = 0b001101
            case "pll 1 clock status":
                function_value = 0b010100
            case "force 1":
                function_value = 0b011111
            case "force 0":
                function_value = 0b100000
            case "clkin3 LOS":
                function_value = 0b000010
            case "clkin1 LOS":
                function_value = 0b000100

        mode_value = 3  # CMOS mode + enable
        config = mode_value + (function_value << 2)
        self.write_byte(addr, config)

    def set_output_channel(self, channel_id: int, high_performance: bool, divider: int, driver_mode: str, driver_impedance: int):
        """
        设置输出通道的频率(通过divider),相位和模式
        """
        is_pulse_generator = False
        base_addr = 0xC8 + channel_id * 0x0A
        start_up_value = 3 if is_pulse_generator else 0
        high_performance_value = 1 if high_performance else 0
        match driver_mode:
            case "CML":
                driver_mode_value = 0
            case "LVPECL":
                driver_mode_value = 1
            case "LVDS":
                driver_mode_value = 2
            case "CMOS":
                driver_mode_value = 3
        match driver_impedance:
            case 0:
                driver_impedance_value = 0
            case 100:
                driver_impedance_value = 1
            case 50:
                driver_impedance_value = 3
        mode_config = 1 + (start_up_value << 2) + (1 << 4) + (high_performance_value << 7)
        driver_config = driver_impedance_value + (driver_mode_value << 3)
        self.set_byte(base_addr, mode_config)
        self.set_byte(base_addr + 1, divider % 256)
        self.set_byte(base_addr + 2, divider // 256)
        self.set_byte(base_addr + 8, driver_config)
        # print(f"setting channel {channel_id}: {hex(mode_config)}, {hex(driver_config)}")

    def init_for_das(self, use_external_clk: bool = True):
        print(f"使用外部时钟={use_external_clk}")
        input_enable = 0x08 if use_external_clk else 0x02
        input_priority = 0x87 if use_external_clk else 0x8d
        input_setting = 0x1c if use_external_clk else 0x0c

        # 1. soft reset
        self.soft_reset()
        # 2. 配置各寄存器
        self.set_byte(0x0001, 0x08)  # mute output drivers
        # 设置输入/输出
        self.set_byte(0x0003, 0x2f)  # select VCO > 2.5G
        self.set_byte(0x0004, 0x7f)  # enable all output channels
        # self.set_byte(0x0005, 0x0a)  # enable CLKIN1,3. 1 for on-card 10M input, 3 for SSMC 10M input
        self.set_byte(0x0005, input_enable)  # enable CLKIN3 only
        # 将other controls中的参数设为最佳
        self.set_byte(0x009F, 0x4d)
        self.set_byte(0x00A0, 0xdf)
        self.set_byte(0x00A5, 0x06)
        self.set_byte(0x00A8, 0x06)
        self.set_byte(0x00B0, 0x04)
        # 设置PLL2参数
        self.set_byte(0x0033, 0x01)  # R2低八位=1
        self.set_byte(0x0034, 0x00)  # R1高四位
        self.set_byte(0x0035, 0x1e)  # N2低八位=30
        self.set_byte(0x0036, 0x00)  # N2高四位
        self.set_byte(0x0032, 0x01)  # disable frequency doubler
        # 设置PLL1参数
        self.set_byte(0x0014, input_priority)  # 输入时钟优先级: 3 > 1 > 0 > 2
        self.set_byte(0x0028, 0x2f)  # 设置PLL1锁定检测,使用计数器,持续2^15周期
        # self.set_byte(0x001C, 0x01)  # CLK0预分频
        self.set_byte(0x001D, 0x01)  # CLK1预分频
        # self.set_byte(0x001E, 0x01)  # CLK2预分频
        self.set_byte(0x001F, 0x01)  # CLK3预分频
        self.set_byte(0x0020, 0x0A)  # OSCIN预分频
        self.set_byte(0x0021, 0x0a)  # R1低八位=10
        self.set_byte(0x0022, 0x00)  # R2高八位
        self.set_byte(0x0026, 0x64)  # N1低八位=100
        self.set_byte(0x0027, 0x00)  # N2高八位
        self.set_byte(0x0029, input_setting)  # 参考时钟源设置
        # SYSREF control
        self.set_byte(0x005C, 0xe8)  # SYSREF setpoint 低八位
        self.set_byte(0x005D, 0x03)  # SYSREF setpoint 高四位
        self.set_byte(0x005A, 0x01)  # pulse generator mode = 1 pulse
        # 设置input buffers(CLKINx & OSCIN)
        self.set_byte(0x000A, 0x04)  # disable input buffer for CLKIN0
        self.set_byte(0x000B, 0x07)  # enable internal 100 Ω termination & ac coupling input mode for CLKIN1
        self.set_byte(0x000C, 0x04)  # disable input buffer for CLKIN2
        self.set_byte(0x000D, 0x07)  # enable internal 100 Ω termination & ac coupling input mode for CLKIN3
        self.set_byte(0x000E, 0x07)  # enable internal 100 Ω termination & ac coupling input mode for OSCIN
        # 设置GPIx
        self.set_byte(0x0046, 0x00)
        self.set_byte(0x0047, 0x00)
        self.set_byte(0x0048, 0x00)
        self.set_byte(0x0049, 0x10)  # 设置功能为pulse generator request
        # 设置GPOx
        self.set_gpo(3, "clkin1 LOS")
        self.set_gpo(4, "clkin3 LOS")
        # 设置输出通道,包括分频系数,output buffers
        # self.set_output_channel(2, True, 300, "LVPECL", 100)  # -> debug, 10MHz
        # self.set_output_channel(3, True, 12 * 16, "LVPECL", 100)  # -> debug, 15.625MHz

        self.set_output_channel(4, True, 3, "LVPECL", 100)  # -> ADC, 1000MHz, DCLK
        self.set_output_channel(5, False, 12 * 16, "LVDS", 0)  # -> ADC, 15.625MHz, SYSREF clock

        self.set_output_channel(0, True, 12, "LVDS", 100)  # -> FPGA, 250MHz, MGT(ref) clock
        self.set_output_channel(6, True, 12 * 16, "LVDS", 100)  # -> FPGA, 15.625MHz, SYSREF clock
        self.set_output_channel(7, False, 12, "LVDS", 0)  # -> FPGA, 250MHz, core clock # unused in our clocking scheme

        time.sleep(0.1)
        # 3. restart dividers/FSMs
        self.set_byte(0x0001, 0x0a)
        self.set_byte(0x0001, 0x08)
        time.sleep(0.1)
        # 4. reseed request
        self.set_byte(0x0001, 0x88)
        time.sleep(1.0)
        status_byte = self.read_byte(self.STATUS)
        pll_locked = is_bit_set(status_byte, 3)
        sysref_locked = is_bit_set(status_byte, 2)
        print(f"input setting: {hex(self.read_byte(0x0005))}, {hex(self.read_byte(0x0014))}, {hex(self.read_byte(0x0029))}")
        return pll_locked and sysref_locked


if __name__ == '__main__':
    device_file = os.path.join(get_device_paths()[0], "user")
    hmc7044 = Hmc7044Driver(device_file, device_file, 0x4_0000)
    hmc7044.show_info()
    hmc7044.init_for_das()
    hmc7044.show_info()
