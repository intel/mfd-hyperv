# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Main module."""

from typing import TYPE_CHECKING

from mfd_common_libs import os_supported
from mfd_typing import OSName

from mfd_hyperv.hw_qos import HWQoS
from mfd_hyperv.hypervisor import HypervHypervisor
from mfd_hyperv.vm_network_interface_manager import VMNetworkInterfaceManager
from mfd_hyperv.vswitch_manager import VSwitchManager

if TYPE_CHECKING:
    from mfd_connect import Connection


class HyperV:
    """Module for HyperV."""

    @os_supported(OSName.WINDOWS)
    def __init__(self, *, connection: "Connection"):
        """Class constructor.

        :param connection: connection instance of MFD connect class.
        """
        self.hw_qos = HWQoS(connection)
        self.hypervisor = HypervHypervisor(connection=connection)
        self.vswitch_manager = VSwitchManager(connection=connection)
        self.vm_network_interface_manager = VMNetworkInterfaceManager(connection=connection)
