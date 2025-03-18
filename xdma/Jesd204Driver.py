# -*- coding: utf-8 -*-
# @Time    : 2024/6/20 7:32
# @Author  : ltr
# @Site    : ${SITE}
# @File    : Jesd204Device.py
# @Software: PyCharm 
# @Comment :

from xdma.XdmaDeviceFile import *


class Jesd204Driver(XdmaDeviceFile):
    VERSION = 0x000
    RESET = 0x004
    ILA_SUPPORT = 0x008
    SCRAMBLING = 0x00C
    SYSREF_HANDLING = 0x010
    TEST_MODES = 0x018
    LINK_ERROR_STATUS = 0x01C

    OCTETS_PER_FRAME = 0x020
    FRAMES_PER_MULTIFRAME = 0x024
    LANE_IN_USE = 0x028
    SUBCLASS_MODE = 0x02C

    RX_BUFFER_DELAY = 0x30
    ERROR_REPORTING = 0x034  # 控制error reporting策略
    SYNC_STATUS = 0x038
    DEBUG_STATUS = 0x03C

    def __init__(self, read_device_file_path, write_device_file_path, base_address):
        super().__init__(read_device_file_path, write_device_file_path, base_address)

    def soft_reset(self):
        self.write_register_field(self.RESET, 0, 1, 1)
        time.sleep(1.0)
        assert not self.check_register_bit(self.RESET, 1), "reset in progress"

    def show_info(self):
        print("\nJESD204B status:")
        print(f"\n\tself-clearing reset in progress: {is_bit_set(self._read_register(self.RESET), 0)}")
        print(f"\tfixed reset set: {is_bit_set(self._read_register(self.RESET), 1)}")
        print(f"\twatchdog enabled: {not is_bit_set(self._read_register(self.RESET), 16)}")
        version = self._read_register(self.VERSION)
        major = version >> 24
        minor = (version >> 16) & 0xF
        revision = (version >> 8) & 0xF
        print(f"\n\tJESD204B IP version: {major}.{minor}.{revision}")
        print(f"\tILA support enabled: {is_bit_set(self._read_register(self.ILA_SUPPORT), 0)}")
        print(f"\tSYSREF Required on Re-Sync: {is_bit_set(self._read_register(self.SYSREF_HANDLING), 16)}")
        print(f"\tSYSREF Always: {is_bit_set(self._read_register(self.SYSREF_HANDLING), 0)}")

        print(f"\n\tscrambling enabled: {is_bit_set(self._read_register(self.SCRAMBLING), 0)}")
        print(f"\toctets per frame(F): {get_bits(self._read_register(self.OCTETS_PER_FRAME), 0, 8) + 1}")
        print(f"\tframes per multiframe(K): {get_bits(self._read_register(self.FRAMES_PER_MULTIFRAME), 0, 8) + 1}")
        lane_in_use_value = get_bits(self._read_register(self.LANE_IN_USE), 0, 8)
        lane_in_use = []
        for lane_id in range(8):
            if lane_in_use_value % 2 == 1:
                lane_in_use.append(lane_id)
            lane_in_use_value = lane_in_use_value >> 1
        print(f"\tlane in use(L): {len(lane_in_use)}({lane_in_use})")
        print(f"\tsubclass: {get_bits(self._read_register(self.SUBCLASS_MODE), 0, 2)}")

        print(f"\n\tRX Buffer Delay: {get_bits(self._read_register(self.RX_BUFFER_DELAY), 0, 10)}")
        print(f"\tA SYSREF event has been captured: {is_bit_set(self._read_register(self.SYNC_STATUS), 16)}")
        print(f"\tLink Sync achieved: {is_bit_set(self._read_register(self.SYNC_STATUS), 0)}")

        link_error_status = self._read_register(self.LINK_ERROR_STATUS)
        link_debug_status = self._read_register(self.DEBUG_STATUS)
        print(f"\tLane Alignment Error Detected Alarm: {is_bit_set(link_error_status, 31)}")
        print(f"\tSYSREF LMFC Alarm: {is_bit_set(link_error_status, 30)}")
        print(f"\tRX Buffer Overflow Alarm: {is_bit_set(link_error_status, 29)}")
        for lane_id in lane_in_use:
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
        self.write_register_field(self.RESET, 16, 1, 0)  # enable watchdog, reset register is self-clearing
        self.write_register_field(self.ILA_SUPPORT, 0, 1, 1, strict=True)
        self.write_register_field(self.SCRAMBLING, 0, 1, 1, strict=True)
        self.write_register_field(self.LANE_IN_USE, 0, 8, 0xf, strict=True)
        self.write_register_field(self.SUBCLASS_MODE, 0, 2, 1, strict=True)
        # self.soft_reset()  # FIXME: this makes the ILA support value cleared
