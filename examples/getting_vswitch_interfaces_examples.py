# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Example for get VLAN ID for switches, for mapping vswitches interfaces etc."""
import logging

from mfd_common_libs import add_logging_level, log_levels
from mfd_connect import RPyCConnection

from mfd_hyperv.vm_network_interface_manager import VMNetworkInterfaceManager
from mfd_hyperv.vswitch_manager import VSwitchManager

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)

conn = RPyCConnection(ip="10.10.10.10")

vswitch_mng = VMNetworkInterfaceManager(connection=conn)
print(vswitch_mng.get_vm_interface_attached_to_vswitch("managementvSwitch"))
print(vswitch_mng.get_vlan_id_for_vswitch("managementvSwitch"))

vswitch_mng = VSwitchManager(connection=conn)
print(vswitch_mng.get_vswitch_mapping())
