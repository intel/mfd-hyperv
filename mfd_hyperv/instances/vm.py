# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Vm class."""
import logging
from dataclasses import asdict
from time import sleep
from typing import Dict, Union, List, TYPE_CHECKING

from mfd_common_libs import add_logging_level, log_levels
from mfd_connect import RPyCConnection, Connection
from mfd_hyperv.attributes.vm_params import VMParams
from mfd_hyperv.exceptions import HyperVException
from mfd_hyperv.hypervisor import VMProcessorAttributes
from mfd_network_adapter import NetworkAdapterOwner
from mfd_typing import MACAddress
from mfd_typing.network_interface import InterfaceType

if TYPE_CHECKING:
    from mfd_hyperv import HyperV
    from mfd_hyperv.instances.vm_network_interface import VMNetworkInterface


logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class VM:
    """VM class."""

    def __init__(
        self,
        connection: "Connection",
        vm_params: VMParams,
        owner: NetworkAdapterOwner = None,
        hyperv: "HyperV" = None,
        connection_timeout: int = None,
    ):
        """VM constructor."""
        self.connection = connection
        self.guest = NetworkAdapterOwner(connection=connection)
        self.attributes = {}
        self.owner = owner
        self._hyperv = None
        self.hyperv = hyperv

        self.connection_timeout = connection_timeout
        self._propagate_params(vm_params)

    def __str__(self) -> str:
        return f"{self.name}"

    @property
    def hyperv(self) -> "HyperV":
        """Hyperv property representing host's hyperv object.

        :raises: HyperVException when this property is empty
        """
        if not self._hyperv:
            raise HyperVException(
                "VM has no access to HyperV object and cannot call this method. Create binding between objects"
            )
        return self._hyperv

    @property
    def interfaces(self) -> List["VMNetworkInterface"]:
        """Hyperv property representing VM interfaces.

        :raises: HyperVException when this property is empty
        """
        if not self._hyperv:
            raise HyperVException(
                "VM has no access to HyperV object and cannot call this method. Create binding between objects"
            )
        return [nic for nic in self._hyperv.vm_network_interface_manager.vm_interfaces if nic.vm == self]

    @hyperv.setter
    def hyperv(self, value: "HyperV") -> None:
        """Hyperv property setter."""
        self._hyperv = value

    def _propagate_params(self, params: VMParams) -> None:
        """Add VMParams as attributes of virtual machine object."""
        for key, value in asdict(params).items():
            setattr(self, key, value)

    def get_attributes(self) -> Dict[str, str]:
        """Get Virtual machine attributes from host (hypervisor)."""
        self.attributes = self.hyperv.hypervisor.get_vm_attributes(self.name)
        return self.attributes

    def start(self, timeout: int = 300) -> None:
        """Start VM from host (hypervisor) and wait for it to be functional.

        :param timeout: time given for VM to reach functional state
        """
        self.hyperv.hypervisor.start_vm(self.name)
        self.hyperv.hypervisor.wait_vm_functional(self.name, self.mng_ip, timeout)
        self.connection = RPyCConnection(self.mng_ip, connection_timeout=self.connection_timeout)

    def stop(self, timeout: int = 300) -> None:
        """Stop VM from host (hypervisor).

        :param timeout: time given for VM to reach "not running" state
        """
        try:
            self.connection.shutdown_platform()
            self.hyperv.hypervisor.wait_vm_stopped(self.name, timeout)
            sleep(timeout / 20)
        except EOFError:
            pass

    def restart(self, timeout: int = 300) -> None:
        """Restart VM by stopping and starting again.

        :param timeout: time given for VM to reach functional state
        """
        self.stop(timeout)
        self.start(timeout)

    def reboot(self, timeout: int = 300) -> None:
        """Reboot from guest and wait for it to be functional.

        :param timeout: time given for VM to reach functional state
        """
        try:
            self.connection.restart_platform()
            sleep(timeout / 20)
        except EOFError:
            pass
        self.wait_functional(timeout)

    def wait_functional(self, timeout: int = 300) -> None:
        """Wait untill this VM can be pinged.

        :param timeout: time given for VM to reach functional state
        """
        self.hyperv.hypervisor.wait_vm_functional(self.name, self.mng_ip, timeout)

    def get_vm_interfaces(self) -> Dict[str, str]:
        """Return dictionary of VM Network interfaces."""
        return self.hyperv.vm_network_interface_manager.get_vm_interfaces(self.name)

    def get_processor_attributes(self) -> Dict[str, str]:
        """Return dictionary of VMProcessorAttributes."""
        return self.hyperv.vm_network_interface_manager.get_vm_interfaces(self.name)

    def set_processor_attributes(
        self, attribute: Union[VMProcessorAttributes, str], value: Union[str, int, bool]
    ) -> None:
        """Set specified VMProcessorAttributes to specified value."""
        if self.get_attributes()["State"] == "Off":
            self.hyperv.vm_network_interface_manager.get_vm_interfaces(self.name, attribute, value)
            return

        self.stop()
        self.hyperv.vm_network_interface_manager.set_vm_processor_attribute(self.name, attribute, value)
        self.start()

    def _get_ifaces_from_vm(self) -> Dict[str, str]:
        """Get interfaces from VM.

        Use cached data if available.
        """
        if self.hyperv.vm_network_interface_manager.all_vnics_attributes.get(self.name) is not None:
            logger.log(level=log_levels.MODULE_DEBUG, msg="Getting cached interfaces")
            return self.hyperv.vm_network_interface_manager.all_vnics_attributes[self.name]
        else:
            logger.log(level=log_levels.MODULE_DEBUG, msg="Retrieving Vm interfaces seen from Hypervisor")
            return self.get_vm_interfaces()

    def _check_vnic_correct_matching(self, created_vm_interfaces: List["VMNetworkInterface"]) -> None:
        """Check if matching was successful, if not raise Exception.

        :param created_vm_interfaces: list of vnics after matching VM interfaces witt VM Guest OS interfaces
        """
        all_have_iface = all(hasattr(vnic, "interface") for vnic in created_vm_interfaces)
        if not all_have_iface:
            raise Exception(f"VM {self} nics couldn't be matched with interfaces on VM guest os")
        sriov_have_vf = all(hasattr(vnic.interface, "vf") for vnic in created_vm_interfaces if vnic.sriov)
        if not sriov_have_vf:
            logger.warning("VM interfaces that were not matched with Virtual Function interface")
            for iface in [nic.interface for nic in created_vm_interfaces if nic.sriov]:
                logger.log(level=log_levels.MODULE_DEBUG, msg=iface.name)
            raise Exception(f"VM {self} SRIOV nics couldn't be matched with Virtual Functions nics on VM guest os.")

    def match_interfaces(self) -> List["VMNetworkInterface"]:
        """Match vm interfaces with interfaces seen from host.

        In addition, match virtual functions with normal adapters.
        """
        logger.log(level=log_levels.MODULE_DEBUG, msg="Get VM interfaces seen from Hypervisor")
        from_host_vm_interfaces = self._get_ifaces_from_vm()
        logger.log(level=log_levels.MODULE_DEBUG, msg="Get interfaces seen from VM guest")
        from_vm_interfaces = self.guest.get_interfaces()
        created_vm_interfaces = [
            iface for iface in self.hyperv.vm_network_interface_manager.vm_interfaces if iface.vm == self
        ]

        # matching will be performed using macaddress
        for iface in created_vm_interfaces:
            for vm_iface_info in from_host_vm_interfaces:
                if iface.interface_name.lower() == vm_iface_info["name"]:
                    iface.mac = MACAddress(vm_iface_info["macaddress"])

        for iface in created_vm_interfaces:
            for vm_iface in from_vm_interfaces:
                # match from-host and from-vm interfaces
                if iface.mac == vm_iface.mac_address and vm_iface.interface_type in [
                    InterfaceType.VMNIC,
                    InterfaceType.VMBUS,
                ]:
                    iface.interface = vm_iface
                    vm_iface.owner = iface.vm.guest

                # match Vfs
                for other_vm_iface in from_vm_interfaces:
                    if vm_iface == other_vm_iface:
                        continue
                    if (
                        vm_iface.mac_address == other_vm_iface.mac_address
                        and other_vm_iface.interface_type == InterfaceType.VF
                    ):
                        vm_iface.vf = other_vm_iface
                        vm_iface.vf.owner = iface.vm.guest

        self._check_vnic_correct_matching(created_vm_interfaces)
        return created_vm_interfaces
