# -*- coding: utf-8 -*-
# @Time    : 2024/6/20 7:32
# @Author  : ltr
# @Site    : ${SITE}
# @File    : Jesd204Device.py
# @Software: PyCharm 
# @Comment :
from email.policy import strict

from xdma.XdmaWindowsDeviceFile import *


class Jesd204_Config(Register32):
    address = 0x0004
    field_widths = [4, 12, 1, 1, 1]

    def __init__(self, lanes=0, is_tx=0, is_64b66b=0, fec_included=0):
        self.lanes = lanes
        self.reserved_0 = 0
        self.is_tx = is_tx
        self.is_64b66b = is_64b66b
        self.fec_included = fec_included


class Jesd204_ResetStatus(Register32):
    address = 0x0020
    field_widths = [1, 1, 2, 1, 1, 1, 1, 8, 8, 8]

    def __init__(self, reset=0, reset_type=0, external_reset_state=0, register_reset_state=0, gt_powergood_busy=0,
                 gt_reset_busy=0, gt_pma_reset_busy=0,
                 gt_mst_reset_busy=0):
        self.reset = reset
        self.reset_type = reset_type
        self.reserved_0 = 0
        self.external_reset_state = external_reset_state
        self.register_reset_state = register_reset_state
        self.gt_powergood_busy = gt_powergood_busy
        self.gt_reset_busy = gt_reset_busy
        self.reserved_1 = 0
        self.gt_pma_reset_busy = gt_pma_reset_busy
        self.gt_mst_reset_busy = gt_mst_reset_busy


class Jesd204_8B10BConfig(Register32):
    address = 0x003C
    field_widths = [8, 5, 3, 1, 1, 1, 1, 4, 8]

    def __init__(self, F=2, K=16, scrambling=1, ila_support=1, error_report=0, error_counter=0, ila_multiframe=4):
        self.F = F - 1
        self.K = K - 1
        self.reserved_0 = 0
        self.scrambling = scrambling
        self.ila_support = ila_support
        self.error_report = error_report
        self.error_counter = error_counter
        self.reserved_1 = 0
        self.ila_multiframe = ila_multiframe - 1


class Jesd204_SysrefConfig(Register32):
    address = 0x0050
    field_widths = [1, 1, 6, 3, 5, 4]

    def __init__(self, always=0, required=0, tolerance=0, delay=0):
        self.always = always
        self.required = required
        self.reserved_0 = 0
        self.tolerance = tolerance
        self.reserved_1 = 0
        self.delay = delay


class Jesd204CDriver(XdmaWindowsDeviceFile):
    """

    TODO: currently, this driver is for 8B10B rx only
    """
    VERSION = 0x000  # FIXME: version = 0.0.0?
    CONFIG = 0x004
    RESET = 0x020
    CTRL_SUB_CLASS = 0x034
    STAT_RX_ERR = 0x058
    STAT_RX_DEBUG = 0x05C
    STAT_STATUS = 0x060

    def __init__(self, read_device_file_path, write_device_file_path, base_address):
        super().__init__(read_device_file_path, write_device_file_path, base_address)

    # def exists(self):

    def soft_reset(self):
        self.write_register_field(self.RESET, 1, 1, 0, strict=False)  # set reset type
        self.write_register_field(self.RESET, 0, 1, 1, strict=False)
        self.write_register_field(self.RESET, 0, 1, 0, strict=False)  # release
        time.sleep(1.0)
        # assert not self.check_register_bit(self.RESET, 0), "reset in progress"

    def show_info(self):
        print("\nJESD204C IP status:")
        config_ip = Jesd204_Config()
        self.read_register32(config_ip)
        config_8b10b = Jesd204_8B10BConfig()
        self.read_register32(config_8b10b)
        config_sysref = Jesd204_SysrefConfig()
        self.read_register32(config_sysref)
        status_reset = Jesd204_ResetStatus()
        self.read_register32(status_reset)

        lane_in_use = config_ip.lanes
        # IP config
        print(f"\tdirection: {'tx' if (config_ip.is_tx == 1) else 'rx'}")
        print(f"\tlane in use: {lane_in_use}")
        print(f"\tfec: {'64B66B' if (config_ip.is_64b66b == 1) else '8B10B'}")
        print(f"\tfec included: {config_ip.fec_included == 1}")
        # reset status
        print(f"\n\treset type: {'include PLL' if (status_reset.reset_type == 0) else 'datapath only'}")
        print(f"\treset in progress: {status_reset.reset == 1}")
        print(f"\ttx/rx_core_reset asserted: {status_reset.external_reset_state == 1}")
        print(f"\ttx/rx_reset asserted: {status_reset.register_reset_state == 1}")
        print(f"\tgt_powergood done: {status_reset.gt_powergood_busy == 0}")
        print(f"\tgt_reset done: {status_reset.gt_reset_busy == 0}")
        # link parameters
        print(f"\n\tscrambling enabled: {config_8b10b.scrambling == 1}")
        print(f"\toctets per frame(F): {config_8b10b.F + 1}")
        print(f"\tframes per multiframe(K): {config_8b10b.K + 1}")
        print(f"\tILA multiframe: {config_8b10b.ila_multiframe + 1}")
        print(f"\tILA support enabled: {config_8b10b.ila_support == 1}")
        print(f"\tsubclass: {self.read_register_field(self.CTRL_SUB_CLASS, 0, 2)}")
        print(f"\n\tSYSREF Required on Re-Sync: {config_sysref.required == 1}")
        print(f"\tSYSREF Always: {config_sysref.always == 1}")
        # overall link status
        status = self._read_register(self.STAT_STATUS)
        print(f"\n\tinterrupt pending: {is_bit_set(status, 0)}")
        print(f"\tSYSREF captured: {is_bit_set(status, 1)}")
        print(f"\tSYSREF error: {is_bit_set(status, 2)}")
        print(f"\tbuffer overflow error: {is_bit_set(status, 10)}")
        print(f"\t8B10B signaled SYNC has been achieved: {is_bit_set(status, 12)}")
        print(f"\t8B10B Code Group Sync achieved: {is_bit_set(status, 13)}")
        print(f"\t8B10B RX started: {is_bit_set(status, 14)}")
        print(f"\t8B10B alignment error: {is_bit_set(status, 15)}")
        # lane status
        link_error_status = self._read_register(self.STAT_RX_ERR)
        link_debug_status = self._read_register(self.STAT_RX_DEBUG)

        for lane_id in range(lane_in_use):
            error_status = get_bits(link_error_status, lane_id * 3, (lane_id + 1) * 3)
            debug_status = get_bits(link_debug_status, lane_id * 4, (lane_id + 1) * 4)
            print(f"\n\tlane {lane_id}: "
                  f"\n\t\tUnexpected K-character(s) received: {is_bit_set(error_status, 2)}"
                  f"\n\t\tDisparity Error(s) received: {is_bit_set(error_status, 1)}"
                  f"\n\t\tNot in Table Error(s) received: {is_bit_set(error_status, 0)}"
                  f"\n\t\tStart of Data was Detected: {is_bit_set(debug_status, 3)}"
                  f"\n\t\tStart of ILA was Detected: {is_bit_set(debug_status, 2)}"
                  f"\n\t\tLane has Code Group Sync: {is_bit_set(debug_status, 1)}"
                  f"\n\t\tLane is currently receiving K28.5's (BC alignment characters): {is_bit_set(debug_status, 0)}")

    def init_for_das(self):
        # set link parameters
        config = Jesd204_8B10BConfig(K=32, F=1, scrambling=1)
        self.write_register32(config)
        self.soft_reset() # make parameters take effect
        # verify
        time.sleep(0.5)
        status = self._read_register(self.STAT_STATUS)
        started = is_bit_set(status, 14)
        return started
