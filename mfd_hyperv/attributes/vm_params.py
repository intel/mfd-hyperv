# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""VMParams class."""
from dataclasses import dataclass, fields
from typing import Optional, Union

from mfd_typing import MACAddress
from mfd_typing.dataclass_utils import convert_value_field_to_typehint_type


@dataclass
class VMParams:
    """Configuration for VM.

    name: Name of VM
    cpu_count: Count of CPUs
    hw_threads_per_core: number of virtual SMT threads exposed to the virtual machine
    memory: Memory value in MB
    generation: Generation of VM
    vm_dir_path: Path to directory where VM will be stored
    img_file_name: Name of VM image used for VM
    mng_interface_name: Name of management vSwitch
    mng_mac_address: Mac address for management vSwitch
    vswitch_name: Name of management vSwitch used
    """

    name: str = "vm"
    cpu_count: int = 2
    hw_threads_per_core: int = 0
    memory: int = 2048
    generation: int = 2
    vm_dir_path: Optional[str] = None
    diff_disk_path: Optional[str] = None
    mng_interface_name: str = "mng"
    mng_mac_address: Optional[Union[MACAddress, str]] = None
    mng_ip: Optional[str] = None
    vswitch_name: Optional[str] = None

    def __post_init__(self):
        for field in fields(self):
            convert_value_field_to_typehint_type(self, field)
