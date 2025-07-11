# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""VMNetworkInterface class."""
import time
from typing import Union, Dict, Optional

from mfd_connect import Connection

from mfd_hyperv.attributes.vm_network_interface_attributes import VMNetworkInterfaceAttributes
from mfd_hyperv.exceptions import HyperVException
from mfd_hyperv.helpers import standardise_value
from mfd_hyperv.instances.vm import VM
from mfd_hyperv.instances.vswitch import VSwitch


class VMNetworkInterface:
    """VMNetworkInterface class."""

    def __init__(
        self,
        interface_name: str,
        vm_name: str,
        vswitch_name: str,
        sriov: bool = False,
        vmq: bool = True,
        connection: Optional["Connection"] = None,
        vm: VM = None,
        vswitch: VSwitch = None,
    ):
        """Virtual Machine Interface constructor.

        Representation of VM Interface seen from Hypervisor.
        """
        self.interface_name = interface_name  # seen from hypervisor
        self.vm_name = vm_name
        self.vswitch_name = vswitch_name
        self.sriov = sriov
        self.vmq = vmq
        self.connection = connection  # connection from host

        self._vm = None
        self.vm = vm
        self._vswitch = None
        self.vswitch = vswitch
        self.interface = None  # interface seen from guest
        self.attributes = None
        self.vlan_id = None
        self.rdma_enabled = None

    def __str__(self):
        vf_name = ""
        if self.sriov:
            vf_name = f" / VF: {self.interface.vf.name}"
        return f"{self.interface_name} ({self.interface.name}{vf_name})"

    @property
    def vswitch(self) -> VSwitch:
        """Vswitch property.

        :raises: HyperVException when this property is empty
        """
        if not self._vswitch:
            raise HyperVException(
                "VM Network Interface has no access to its vswitch objects and cannot call its method."
                "Create binding between objects."
            )
        return self._vswitch

    @vswitch.setter
    def vswitch(self, value: VSwitch) -> None:
        """Vswitch property setter."""
        self._vswitch = value

    @property
    def vm(self) -> VM:
        """VM property.

        :raises: HyperVException when this property is empty
        """
        if not self._vm:
            raise HyperVException(
                "VM Network Interface has no access to VM object and cannot call its methods."
                "Create binding between objects."
            )
        return self._vm

    @vm.setter
    def vm(self, value: VM) -> None:
        """VM property setter."""
        self._vm = value

    def set_and_verify_attribute(
        self,
        attribute: Union[VMNetworkInterfaceAttributes, str],
        value: Union[str, int, bool],
        sleep_duration: int = 1,
    ) -> bool:
        """Set specified vm interface attribute to specified value and check if results where applied in the OS.

        :param attribute: attribute to set
        :param value: new value
        :param sleep_duration: sleep_duration between setting value and reading it
        """
        self.vm.hyperv.vm_network_interface_manager.set_vm_interface_attribute(
            self.interface_name, self.vm.name, attribute, value
        )
        time.sleep(sleep_duration)

        vm_nics_attrs = self.vm.hyperv.vm_network_interface_manager.get_vm_interface_attributes(self.vm.name)
        read_value = next(item for item in vm_nics_attrs if item["name"] == self.interface_name.lower())[attribute]
        return standardise_value(value) == standardise_value(read_value)

    def get_attributes(self, refresh_data: bool = False) -> Dict[str, Dict[str, str]]:
        """Return VM Network Interface attributes in form of dictionary.

        :return: dictionary with VM Network Interface attributes
        """
        if refresh_data or self.vm.name not in self.vm.hyperv.vm_network_interface_manager.all_vnics_attributes:
            self.vm.hyperv.vm_network_interface_manager.all_vnics_attributes[self.vm.name] = (
                self.vm.hyperv.vm_network_interface_manager.get_vm_interface_attributes(self.vm.name)
            )
        self.attributes = next(
            item
            for item in self.vm.hyperv.vm_network_interface_manager.all_vnics_attributes[self.vm.name]
            if item["name"] == self.interface_name.lower()
        )
        return self.attributes

    def disconnect_from_vswitch(self) -> None:
        """Disconnect from vswitch."""
        if not self.vswitch:
            return
        self.vm.hyperv.vm_network_interface_manager.disconnect_vm_interface(self.interface_name, self.vm.name)
        self.vswitch = None
        self.vswitch_name = None

    def connect_to_vswitch(self, vswitch: VSwitch) -> None:
        """Connect vm network Interface to virtual switch.

        :param vswitch: virtual switch that vm adapter will be connected to
        """
        self.vm.hyperv.vm_network_interface_manager.connect_vm_interface(
            self.interface_name, self.vm.name, vswitch.interface_name
        )
        self.vswitch = vswitch
        self.vswitch_name = vswitch.interface_name

    def remove(self) -> None:
        """Remove vm network interface."""
        self.vm.hyperv.vm_network_interface_manager.remove_vm_interface(self.interface_name, self.vm.name)

    def get_vlan_info(self) -> Dict[str, str]:
        """Get information about VM adapter VLAN."""
        return self.vm.hyperv.vm_network_interface_manager.get_vm_interface_vlan(
            vm_name=self.vm.name, interface_name=self.interface_name
        )

    def get_vlan_id(self) -> str:
        """Get adapter VLAN ID."""
        return self.get_vlan_info()["AccessVlanId"]

    def set_vlan(
        self,
        state: str,
        vlan_type: str,
        vlan_id: Union[str, int],
    ) -> None:
        """Set VLAN on VM nadapter.

        :param state: one of ["access", "trunk", "promiscuous", "isolated", "untagged"]
        :param vlan_type one of ["vlanid", "nativevlanid", "primaryvlanid"]
        :param vlan_id: VLAN ID
        """
        self.vm.hyperv.vm_network_interface_manager.set_vm_interface_vlan(
            state=state, vm_name=self.vm.name, interface_name=self.interface_name, vlan_type=vlan_type, vlan_id=vlan_id
        )
        self.vlan_id = int(vlan_id)

    def get_rdma_status(self) -> bool:
        """Get adapter RDMA ststus."""
        return self.get_rdma_info()["RdmaWeight"] == "100"

    def get_rdma_info(self) -> Dict[str, str]:
        """Get information about VM adapter RDMA."""
        return self.vm.hyperv.vm_network_interface_manager.get_vm_interface_rdma(
            vm_name=self.vm.name, interface_name=self.interface_name
        )

    def set_rdma(
        self,
        state: bool,
    ) -> None:
        """Set RDMA on VM nic.

        :param state: enabled or disabled
        """
        self.vm.stop()

        self.vm.hyperv.vm_network_interface_manager.set_vm_interface_rdma(
            vm_name=self.vm.name,
            interface_name=self.interface_name,
            state=state,
        )
        self.rdma_enabled = state

        self.vm.start()
