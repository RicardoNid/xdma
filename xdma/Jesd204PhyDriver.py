# -*- coding: utf-8 -*-
# @Time    : 2024/6/20 7:32
# @Author  : ltr
# @Site    : ${SITE}
# @File    : Jesd204Device.py
# @Software: PyCharm 
# @Comment :

from xdma.XdmaWindowsDeviceFile import *


class Jesd204Phy_Pll(Register32):
    address = 0x080
    field_widths = [1, 1, 1, 1, 1]

    def __init__(self, qpll1_unlock=1, qpll0_unlock=1, cpll_unlock=1, rx_reset_in_progress=1, tx_reset_in_progress=1):
        self.qpll1_unlock = qpll1_unlock
        self.qpll0_unlock = qpll0_unlock
        self.cpll_unlock = cpll_unlock
        self.rx_reset_in_progress = rx_reset_in_progress
        self.tx_reset_in_progress = tx_reset_in_progress


class Jesd204PhyDriver(XdmaWindowsDeviceFile):
    PLL_STATUS = 0x080
    RXLINERATE = 0x90
    RXREFCLK = 0x98
    RXPLL = 0x0A0

    def __init__(self, read_device_file_path, write_device_file_path, base_address):
        super().__init__(read_device_file_path, write_device_file_path, base_address)

    def show_info(self):
        print("\nJESD204C PHY IP status:")
        status_pll = Jesd204Phy_Pll()
        self.read_register32(status_pll)

        # IP config
        print(f"\tqpll0 locked: {status_pll.qpll0_unlock == 0}")
        print(f"\tqpll1 locked: {status_pll.qpll1_unlock == 0}")
        print(f"\tcpll locked: {status_pll.cpll_unlock == 0}")
        print(f"\trx reset in progress: {status_pll.rx_reset_in_progress == 1}")
        print(f"\ttx reset in progress: {status_pll.tx_reset_in_progress == 1}")

        rxpll = self.read_register_field(self.RXPLL, 0, 2)
        pll_type = 'unknown'
        match rxpll:
            case 0:
                pll_type = 'CPLL'
            case 2:
                pll_type = 'QPLL1'
            case 3:
                pll_type = 'QPLL0'
        print(f"\tRX pll type: {pll_type}")
        rx_linerate = self.read_register_field(self.RXLINERATE, 0, 32)
        print(f"\tRX line rate: {rx_linerate / 1000_000} GHz")
        rx_refclk = self.read_register_field(self.RXREFCLK, 0, 32)
        print(f"\tRX refclk frequency: {rx_refclk / 1000} MHz")
