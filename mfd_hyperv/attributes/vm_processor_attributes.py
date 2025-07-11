# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""VMProcessorAttributes class."""
from enum import Enum


class VMProcessorAttributes(str, Enum):
    """Enum for VM processor attributes."""

    def __str__(self) -> str:
        return str.__str__(self)

    Count: str = "count"
    HWThreadCountPerCore: str = "hwthreadcountpercore"
