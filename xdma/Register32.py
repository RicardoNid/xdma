# -*- coding: utf-8 -*-
# @Time    : 2024/10/01 11:01
# @Author  : Administrator
# @Site    : ${SITE}
# @File    : Register32.py
# @Software: PyCharm 
# @Comment : 
class Register32:
    address: int
    field_widths: list[int]

    def to_value(self):
        value = 0
        shift = 0
        for (field_name, width) in zip(self.__dict__.keys(), self.field_widths):
            value += (getattr(self, field_name) << shift)
            shift += width
        return value

    def from_value(self, value):
        for field_name, width in zip(self.__dict__.keys(), self.field_widths):
            field_value = value % (1 << width)
            setattr(self, field_name, field_value)
            value >>= width
