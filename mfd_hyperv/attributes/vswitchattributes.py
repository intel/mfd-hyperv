# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""VSwitchAttributes class."""
from enum import Enum


class VSwitchAttributes(str, Enum):
    """Enum of attributes that can be set on vSwitch."""

    def __str__(self) -> str:
        return str.__str__(self)

    DefaultQueueVmmqEnabled: str = "defaultqueuevmmqenabled"
    DefaultQueueVmmqQueuePairs: str = "defaultqueuevmmqqueuepairs"
    EmbeddedTeamingEnabled: str = "embeddedteamingenabled"
    EnableSoftwareRsc: str = "enablesoftwarersc"
    EnableRscOffload: str = "enablerscoffload"
    IovEnabled: str = "iovenabled"
    IovQueuePairsInUse: str = "iovqueuepairsinuse"
    IovSupport: str = "iovsupport"
    IovVirtualFunctionCount: str = "iovvirtualfunctioncount"
    IovVirtualFunctionsInUse: str = "iovvirtualfunctionsinuse"
    NumberVmqAllocated: str = "numbervmqallocated"
    RscOffloadEnabled: str = "rscoffloadenabled"
    SoftwareRscEnabled: str = "softwarerscenabled"
    SwitchType: str = "switchtype"
