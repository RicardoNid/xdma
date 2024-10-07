# -*- coding: utf-8 -*-
# @Time    : 2024/6/19 18:42
# @Author  : ltr
# @Site    : ${SITE}
# @File    : AxiDmaDriver.py
# @Software: PyCharm 
# @Comment :

import time
from dataclasses import dataclass

from XdmaWindowsDeviceFile import *
from XdmaWindowsDeviceFile import *

DESCRIPTOR_SIZE = 32
DESCRIPTOR_GAP = 64


@dataclass
class SgDescriptor:
    next_descriptor_pointer: int
    buffer_address: int
    buffer_length: int
    start_of_frame: int = 1  # by default, a descriptor describe a packet
    end_of_frame: int = 1
    next_descriptor_pointer_msb: int = 0
    buffer_address_msb: int = 0
    transferred_bytes: int = 0
    dma_internal_error: int = 0
    dma_slave_error: int = 0
    dma_decode_error: int = 0
    completed: int = 0

    def __post_init__(self):
        assert self.next_descriptor_pointer % 64 == 0, "bad descriptor alignment to 16-words "
        assert 0 <= self.buffer_length, "bad buffer length"
        assert self.buffer_length < (1 << 26), "bad buffer length >= 64MB"

    def to_bytes(self):
        control = self.buffer_length
        control += self.end_of_frame << 26
        control += self.start_of_frame << 27
        status = self.transferred_bytes
        status += self.dma_internal_error << 28
        status += self.dma_slave_error << 29
        status += self.dma_decode_error << 30
        status += self.completed << 31
        bytes = np.zeros(8, dtype=np.uint32)
        bytes[0] = self.next_descriptor_pointer
        bytes[1] = self.next_descriptor_pointer_msb
        bytes[2] = self.buffer_address
        bytes[3] = self.buffer_address_msb
        bytes[6] = control
        bytes[7] = status
        return bytes

    @classmethod
    def from_bytes(cls, bytes: np.ndarray):
        control = bytes[6]
        end_of_frame = (control >> 26) & 0x1
        start_of_frame = (control >> 27) & 0x1
        buffer_length = control & 0x3FFFFFF
        status = bytes[7]
        transferred_bytes = status & 0x3FFFFFF
        dma_internal_error = (status >> 28) & 0x1
        dma_slave_error = (status >> 29) & 0x1
        dma_decode_error = (status >> 30) & 0x1
        completed = (status >> 31) & 0x1
        ret = SgDescriptor(bytes[0], bytes[2], buffer_length, start_of_frame, end_of_frame, bytes[1], bytes[3],
                           transferred_bytes, dma_internal_error, dma_slave_error, dma_decode_error, completed)

        return ret

    def show_info(self):
        print(f"transfer {self.buffer_length} bytes from/to {self.buffer_address}, next descriptor @ {self.next_descriptor_pointer}")

    def show_status(self):
        error = ""
        if self.dma_internal_error:
            error = "dma_internal_error"
        elif self.dma_internal_error:
            error = "dma_internal_error"
        elif self.dma_decode_error:
            error = "dma_decode_error"
        else:
            error = "none"
        print(f"{self.transferred_bytes} bytes transferred, completed = {self.completed == 1}, error = {error}")


class AxiDmaDevice(XdmaWindowsDeviceFile):
    # register list
    # M2SS
    MM2S_DMACR = 0x00
    MM2S_DMASR = 0x04
    # for scatter-gather
    MM2S_CURDESC = 0x08
    MM2S_CURDESC_MSB = 0x0C
    MM2S_TAILDESC = 0x10
    MM2S_TAILDESC_MSB = 0x14
    # for direct register
    MM2S_SA = 0x18
    MM2S_DA = 0x1C
    MM2S_LENGTH = 0x28
    # SG control
    SG_CTL = 0x2C
    # S2MM
    S2MM_DMACR = 0x30
    S2MM_DMASR = 0x34
    # for scatter-gather
    S2MM_CURDESC = 0x38
    S2MM_CURDESC_MSB = 0x3C
    S2MM_TAILDESC = 0x40
    S2MM_TAILDESC_MSB = 0x44
    # for direct register
    S2MM_DA = 0x48
    S2MM_DA_MSB = 0x4C
    S2MM_LENGTH = 0x58

    # TODO: get length maximum

    def __init__(self, read_device_file_path, write_device_file_path, base_address):
        super().__init__(read_device_file_path, write_device_file_path, base_address)

    def is_m2ss_enabled(self):
        return self._read_register(0x00) != 0x0000_0000

    def is_s2mm_enabled(self):
        return self._read_register(0x30) != 0x0000_0000

    def is_sg_enabled(self):
        return self.read_register_field(self.S2MM_DMASR, 3, 1) == 1 or self.read_register_field(self.MM2S_DMASR, 3, 1) == 1

    def show_info(self):
        print("\nAXI DMA info:")
        print(f"\ts2mm enabled: {self.is_s2mm_enabled()}")
        print(f"\tm2ss_enabled: {self.is_m2ss_enabled()}")
        print(f"\tusing Scatter Gather: {self.is_sg_enabled()}")
        self.show_s2mm_info()
        self.show_mm2s_info()

    def show_channel_info(self, base_address: int = 0):
        def get_control(bit: int):
            return self.read_register_field(base_address, bit, 1) == 1

        def get_status(bit: int):
            return self.read_register_field(base_address + 0x04, bit, 1) == 1

        print(
            f"\treset: {get_control(2)}, running: {get_control(0)}, halted: {get_status(0)}, idle: {get_status(1)}, keyhole:{get_control(3)}, cyclic: {get_control(4)}")
        if self.is_sg_enabled():
            print(f"\tsg_internal_error: {get_status(8)}, sg_slave_error: {get_status(9)}, sg_decode_error: {get_status(10)}")
        else:
            print(f"\tdma_internal_error: {get_status(4)}, dma_slave_error: {get_status(5)}, dma_decode_error: {get_status(6)}")

    def show_s2mm_info(self):
        print(f"\nS2MM channel info:")
        self.show_channel_info(self.S2MM_DMACR)

    def show_mm2s_info(self):
        print(f"\nMM2S channel info:")
        self.show_channel_info(self.MM2S_DMACR)

    def reset(self):
        if self.is_m2ss_enabled():
            self.write_register_field(self.MM2S_DMACR, 2, 1, 1)
        elif self.is_s2mm_enabled():
            self.write_register_field(self.S2MM_DMACR, 2, 1, 1)

    def do_direct_s2mm_operation(self, addr: int, length: int):
        # 1. set S2MM_DMACR.RS = 1
        self.write_register_field(self.S2MM_DMACR, 0, 1, 1)
        # 2. enable interrupt if desired
        # 3. write destination address to  S2MM_DA
        low = addr & 0xFFFFFFFF
        high = (addr >> 32) & 0xFFFFFFFF
        self._write_register(self.S2MM_DA, low)
        if high != 0:
            self._write_register(self.S2MM_DA_MSB, high)
        # 4. write length to S2MM_LENGTH, this operation will start DMA data transfer
        self._write_register(self.S2MM_LENGTH, length)
        # 5. read S2MM_LENGTH
        time.sleep(1)
        # 6. read S2MM_DMACR.RS
        # print(f"S2MM_DMACR.RS = {self.read_register_field(self.S2MM_DMACR, 0, 1)}")
        # print(f"S2MM_DMACR.Halted = {self.read_register_field(self.S2MM_DMASR, 0, 1)}")
        # print(f"S2MM_DMACR.Idle = {self.read_register_field(self.S2MM_DMASR, 1, 1)}")
        print(f"S2MM_LENGTH = {self._read_register(self.S2MM_LENGTH) >> 10}KB ")
        print(f"S2MM_DA = {self._read_register(self.S2MM_DA)} ")

    # TODO: sg_enabled
    def do_s2mm_reset(self):
        self.write_register_field(self.S2MM_DMACR, 2, 1, 1)

    def do_sg_s2mm_operation(self, bd_start, bd_end, cyclic: bool = False):
        # 1. set starting descriptor
        assert bd_start % 64 == 0, "bad alignment"
        self.write_register_field(self.S2MM_CURDESC, 6, 26, bd_start // 64)  # this register is RO when S2MM_DMACR.RS = 1
        # 2. set S2MM_DMACR.RS = 1
        self.write_register_field(self.S2MM_DMACR, 0, 1, 1)
        cyclic_value = 1 if cyclic else 0
        self.write_register_field(self.S2MM_DMACR, 4, 1, cyclic_value, strict=True)
        # 3. enable interrupt if desired
        # 4. set tail descriptor, this operation will start data transfer
        assert bd_end % 64 == 0, "bad alignment"
        if cyclic:
            self.write_register_field(self.S2MM_TAILDESC, 6, 26, bd_end // 64 + 64)  # this register is RO when S2MM_DMACR.RS = 1
        else:
            self.write_register_field(self.S2MM_TAILDESC, 6, 26, bd_end // 64)  # this register is RO when S2MM_DMACR.RS = 1

    def do_direct_mm2s_operation(self, addr: int, length: int):
        pass

    def do_sg_m2ss_operation(self, bd_start, bd_end, cyclic: bool = False):
        pass
