# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Hyper-V VMNetworkInterfaceManager."""
import logging
from typing import TYPE_CHECKING, Union, List, Dict, Optional

from mfd_common_libs import os_supported, add_logging_level, log_levels
from mfd_connect.util.powershell_utils import parse_powershell_list
from mfd_typing import OSName

from mfd_hyperv.attributes.vm_network_interface_attributes import VMNetworkInterfaceAttributes
from mfd_hyperv.exceptions import HyperVException, HyperVExecutionException
from mfd_hyperv.instances.vm import VM
from mfd_hyperv.instances.vm_network_interface import VMNetworkInterface
from mfd_hyperv.instances.vswitch import VSwitch

if TYPE_CHECKING:
    from mfd_connect import Connection

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)

UNTAGGED_VLAN = 0


class VMNetworkInterfaceManager:
    """Module for VMNetworkInterfaceManager.

    Wrapper for Powershell cmdlets for operations managing VM adapters from hypervisor host.
    """

    @os_supported(OSName.WINDOWS)
    def __init__(self, connection: "Connection"):
        """Class constructor.

        :param connection: connection instance of MFD connect class.
        """
        self.connection = connection
        self.vm_interfaces = []
        self.vm_adapter_name_counter = 1

        self.all_vnics_attributes = {}

    def create_vm_network_interface(
        self,
        vm_name: str | None = None,
        vswitch_name: str | None = None,
        sriov: bool = False,
        vmq: bool = True,
        get_attributes: bool = False,
        vm: VM | None = None,
        vswitch: VSwitch | None = None,
    ) -> VMNetworkInterface:
        """Add network interface to VM or Host OS.

        :param vm_name: name of Virtual Machine this adapter belongs to (None for Host OS)
        :param vswitch_name: name of vSwitch that this adapter is connected to
        :param sriov: Decided whether adapter should use SRIOV
        :param vmq: Decided whether adapter should use VMQ
        :param get_attributes: retrieve VM interface attributes right after creating it
        :param vm: Virtual machine that VM network interface will be connected to
        :param vswitch: Virtual switch that VM network interface will be connected to
        :raises: HyperVException when VM adapter cannot be added to specified VM or Host OS
        """
        vnic_name = self._generate_name(vm_name if vm_name else "host")
        logger.log(
            level=log_levels.MODULE_DEBUG,
            msg=(
                f"Adding VMNetworkAdapter {vnic_name} to "
                f"{'Host OS' if vm_name is None else f'VM {vm_name}'}. "
                f"VMQ = {vmq}, SRIOV = {sriov}"
            ),
        )
        vswitch_info = f'-SwitchName "{vswitch_name}"' if vswitch_name else ""
        cmd = "-ManagementOS" if vm_name is None else f'-VMName "{vm_name}"'
        command = f'Add-VMNetworkAdapter {vswitch_info} {cmd} -Name "{vnic_name}"'

        result = self.connection.execute_powershell(command=command, expected_return_codes={})

        if result.return_code:
            raise HyperVException(
                f"Couldn't add VM adapter {vnic_name} to {'Host OS' if vm_name is None else f'VM {vm_name}'}"
            )

        vm_interface = VMNetworkInterface(vnic_name, vm_name, vswitch_name, sriov, vmq, self.connection, vm, vswitch)

        sriov_value = 100 if sriov else 0
        vmq_value = 100 if vmq else 0
        self.set_vm_interface_attribute(vnic_name, vm_name, VMNetworkInterfaceAttributes.IovWeight, sriov_value)
        self.set_vm_interface_attribute(vnic_name, vm_name, VMNetworkInterfaceAttributes.VmqWeight, vmq_value)
        if get_attributes:
            vm_interface.get_attributes(True)
        self.vm_interfaces.append(vm_interface)

        return vm_interface

    def remove_vm_interface(
        self,
        vm_interface_name: str,
        vm_name: str,
    ) -> None:
        """Remove network interface from VM.

        :param vm_interface_name: VM adapter which will be removed
        :param vm_name: VM that owns adapter
        :raises: HyperVException when VM adapter cannot be removed
        """
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Remove VMNetworkAdapter {vm_interface_name} of VM {vm_name}")

        command = f'Remove-VMNetworkAdapter -VMName {vm_name} -Name "{vm_interface_name}"'
        result = self.connection.execute_powershell(command=command, expected_return_codes={})
        if result.return_code:
            raise HyperVException(f"Couldn't remove VM {vm_name} adapter {vm_interface_name}")

        vm_interface = [nic for nic in self.vm_interfaces if nic.interface_name == vm_interface_name]
        if vm_interface:
            self.vm_interfaces.remove(vm_interface[0])

    def connect_vm_interface(
        self,
        vm_interface_name: str,
        vm_name: str,
        vswitch_name: str,
    ) -> None:
        """Connect vm adapter to virtual switch.

        :param vm_interface_name: str
        :param vm_name: str
        :param vswitch_name
        :raises: HyperVException when VM adapter cannot be connected to specified vswitch
        """
        logger.log(
            level=log_levels.MODULE_DEBUG,
            msg=f"Connecting VM {vm_name} adapter {vm_interface_name} to VMSwitch {vswitch_name}",
        )

        command = (
            f"Connect-VMNetworkAdapter"
            f" -VMName {vm_name}"
            f' -Name "{vm_interface_name}"'
            f' -SwitchName "*{vswitch_name}*"'
        )

        result = self.connection.execute_powershell(command=command, expected_return_codes={})
        if result.return_code:
            raise HyperVException(
                f"Couldn't connect VM {vm_name} adapter {vm_interface_name} to VMSwitch {vswitch_name}"
            )

    def disconnect_vm_interface(self, vm_interface_name: str, vm_name: str) -> None:
        """Disconnect VM Network Interface from vswitch.

        :param vm_interface_name: Virtual Machine Network Interface
        :param vm_name: name of Virtual Machine
        :raises: HyperVException when VM adapter cannot be disconnected from specified vswitch
        """
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Disconnecting VM {vm_name} adapter {vm_interface_name}")

        command = f"Disconnect-VMNetworkAdapter -VMName {vm_name} -Name {vm_interface_name}"
        result = self.connection.execute_powershell(command=command, expected_return_codes={})
        if result.return_code:
            raise HyperVException(f"Couldn't disconnect VM {vm_name} adapter {vm_interface_name}")

    def get_vm_interface_vlan(self, vm_name: str, interface_name: str) -> Dict[str, str]:
        """Get VLAN settings for the traffic through a virtual network adapter.

        :param vm_name: name of VM
        :param interface_name: name of VM network  seen from hypervisor"
        """
        command = f"Get-VMNetworkAdapterVlan -vmname {vm_name} -VMNetworkAdapterName {interface_name} | select * | fl"

        result = self.connection.execute_powershell(command=command, expected_return_codes={})
        if result.return_code:
            raise HyperVException("Couldn't get VMNetworkAdapterVlan.")

        return parse_powershell_list(result.stdout)[0]

    def set_vm_interface_vlan(
        self,
        state: str,
        vm_name: Optional[str] = None,
        interface_name: Optional[str] = None,
        vlan_type: Optional[str] = None,
        vlan_id: Optional[Union[str, int]] = None,
        management_os: bool = False,
    ) -> None:
        """Configure the VLAN settings for the traffic through a virtual network adapter.

        :param state: one of ["access", "trunk", "promiscuous", "isolated", "untagged"]
        :param vm_name: name of VM
        :param interface_name: name of VM network  seen from hypervisor"
        :param vlan_type one of ["vlanid", "nativevlanid", "primaryvlanid"]
        :param vlan_id: VLAN Id
        :param management_os whether to apply settings on virtual switch in the management OS
        """
        assert state.lower() in ["access", "trunk", "promiscuous", "isolated", "untagged"]

        command = "Set-VMNetworkAdapterVlan "
        if management_os:
            command += "-ManagementOS "
        if interface_name and vm_name:
            command += f"-VMName {vm_name} -VMNetworkAdapterName {interface_name} "

        command += f"-{state} "

        if vlan_type and vlan_id:
            assert vlan_type.lower() in ["vlanid", "nativevlanid", "primaryvlanid"]
            command += f"-{vlan_type} {vlan_id}"

        logger.log(
            level=log_levels.MODULE_DEBUG,
            msg="Setting VM adapter VLAN",
        )
        result = self.connection.execute_powershell(command=command, expected_return_codes={})
        if result.return_code:
            raise HyperVException("Couldn't set VMNetworkAdapterVlan.")

    def get_vm_interface_rdma(self, vm_name: str, interface_name: str) -> Dict[str, str]:
        """Get RDMA settings for VM network adapter.

        :param vm_name: name of VM
        :param interface_name: name of VM network  seen from hypervisor"
        """
        command = f"Get-VMNetworkAdapterRDMA -vmname {vm_name} -VMNetworkAdapterName {interface_name} | select * | fl"

        result = self.connection.execute_powershell(command=command, expected_return_codes={})
        if result.return_code:
            raise HyperVException("Couldn't get VMNetworkAdapterRDMA.")

        return parse_powershell_list(result.stdout)[0]

    def set_vm_interface_rdma(self, vm_name: str, interface_name: str, state: bool) -> None:
        """Set RDMA on VM nic.

        :param vm_name: VM name
        :param interface_name: name of VM nic seen by hypervisor
        :param state: expected state of RDMA after operation succeeds
        """
        rdma_weight = "100" if state else "0"
        command = f'Set-VMNetworkAdapterRDMA -VMName "{vm_name}" -Name "{interface_name}" -RdmaWeight {rdma_weight}'

        logger.log(
            level=log_levels.MODULE_DEBUG,
            msg=f"Set RDMA state to {state} on vnic {interface_name} of VM {vm_name}",
        )
        result = self.connection.execute_powershell(command=command, expected_return_codes={})
        if result.return_code:
            raise HyperVException(f"Couldn't set RDMA state to {state} on vnic {interface_name} of VM {vm_name}")

    def set_vm_interface_attribute(
        self,
        vm_interface_name: str,
        vm_name: Union[str, None],
        attribute: Union[VMNetworkInterfaceAttributes, str],
        value: Union[str, int],
    ) -> None:
        """Set attribute on VM (-VMName <vm_name>) or Host (-ManagementOS case) adapter.

        :param vm_interface_name: Virtual Machine Network Interface
        :param vm_name: name of Virtual Machine
        :param attribute: Name  changed attribute
        :param value: new value of changed attribute
        :raises: HyperVException when VM network adapter attributes cannot be set
        """
        if isinstance(attribute, VMNetworkInterfaceAttributes):
            attribute = attribute.value

        logger.log(
            level=log_levels.MODULE_DEBUG,
            msg=f"Setting adapter: {vm_interface_name} attribute: {attribute} to: {value}.",
        )
        cmd = f"-VMName {vm_name}" if vm_name is not None else "-ManagementOS"
        command = f'Set-VMNetworkAdapter -Name "{vm_interface_name}" {cmd} -{attribute} {value}'

        result = self.connection.execute_powershell(command=command, expected_return_codes={})
        if result.return_code:
            raise HyperVException(f"Couldn't set VM: '{vm_name}' adapter attribute: '{attribute}' to '{value}'.")

    def clear_vm_interface_attributes_cache(self, vm_name: str = None) -> None:
        """Clear cached VM nics attributes information of specified VM.

        :param vm_name: name of vm which vnics will have information about their attributes cleared
        """
        if vm_name and vm_name in self.all_vnics_attributes:
            self.all_vnics_attributes[vm_name] = {}
        else:
            self.all_vnics_attributes = {}

    def get_vm_interface_attributes(self, vm_name: str) -> Dict[str, str]:
        """Get attributes of all VM network interface.

        :param vm_name: name of Virtual Machine name
        :raises: HyperVException when vm network adapter attributes cannot be retrieved
        """
        logger.log(level=log_levels.MODULE_DEBUG, msg="Getting VM adapter attributes")

        command = f"Get-VMNetworkAdapter -Name * -VMName {vm_name} | select * | fl"
        result = self.connection.execute_powershell(command=command, expected_return_codes={})
        if result.return_code:
            raise HyperVException(f"Couldn't get VM {vm_name} adapter attributes")

        self.all_vnics_attributes[vm_name] = parse_powershell_list(result.stdout.lower())
        return self.all_vnics_attributes[vm_name]

    def get_vm_interfaces(self, vm_name: str) -> List[Dict[str, str]]:
        """Return dictionary of VM Network interfaces.

        :params vm_name: Name of VM
        :raises: HyperVException when information about VM adapters cannot be retrieved
        :return: list of dictionaries with information about each VM adapter
        """
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Get VM adapters of VM {vm_name}")

        command = f"Get-VMNetworkAdapter -VMName {vm_name} | select * | fl"

        result = self.connection.execute_powershell(command=command, expected_return_codes={})
        if result.return_code:
            raise HyperVException(f"Couldn't get information about VM adapters of VM {vm_name}")

        return parse_powershell_list(result.stdout.lower())

    def _generate_name(self, vm_name: str) -> str:
        """Create unified vn adapter interface name.

        :param vm_name: name of Virtual Machine adapter belongs to
        """
        vm_str = vm_name.split("_")[-1]
        name = f"{vm_str}_vnic_{self.vm_adapter_name_counter:03}"
        self.vm_adapter_name_counter += 1
        return name

    def get_adapters_vf_datapath_active(self) -> bool:
        """Return Vfdatapathactive status of all VM adapters.

        raises: HyperVException if couldn't get VM nics VfDatapathActive
        """
        command = (
            "get-vmnetworkadapter -VMName * | Where-Object IovWeight -EQ '100'"
            " | select -ExpandProperty Vfdatapathactive"
        )

        result = self.connection.execute_powershell(command=command, expected_return_codes={})
        if result.return_code:
            raise HyperVException("Couldn't get VM nics VfDatapathActive")

        results = [item for item in result.stdout.replace(" ", "").splitlines() if item]
        return all(item == "True" for item in results)

    def get_vm_interface_attached_to_vswitch(self, vswitch_name: str) -> str:
        """Get the VMNetworkAdapter name that is attached to the vswitch.

        :param vswitch_name: name of vswitch interface
        :raises: HyperVExecutionException on any Powershell command execution error
        :return: name of interfaces attached to the vswitch_name
        """
        return self.connection.execute_powershell(
            f"(Get-VMNetworkAdapter -ManagementOS | ? {{ $_.SwitchName -eq '{vswitch_name}'}}).Name",
            custom_exception=HyperVExecutionException,
        ).stdout.strip()

    def get_vlan_id_for_vswitch(self, vswitch_name: str) -> int:
        """Get VLAN tagging set for Hyper-V vSwitch. Only access and untagged modes are supported at this point.

        :param vswitch_name: vswitch adapter object
        :raises: HyperVExecutionException on any Powershell command execution error
        :return: vlan number. 0 if untagged
        """
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Get VLAN ID for vswitch ({vswitch_name})...")
        vmnetwork_adapter_name = self.get_vm_interface_attached_to_vswitch(vswitch_name=vswitch_name)
        settings = self.connection.execute_powershell(
            f'Get-VMNetworkAdapterVlan -ManagementOS -VMNetworkAdapterName "{vmnetwork_adapter_name}"',
            custom_exception=HyperVExecutionException,
        ).stdout
        settings = parse_powershell_list(settings)
        if not settings:
            logger.log(level=log_levels.MODULE_DEBUG, msg=f"Could not get VLAN settings for {vswitch_name}")
            # UNTAGGED_VLAN is a safe guess in this situation - if it's impossible to get the VLAN setting,
            # adapter probably doesn't support VLANs or sth is seriously wrong with the OS configuration
            return UNTAGGED_VLAN
        operation_mode = settings[0]["OperationMode"]

        if operation_mode == "Untagged":
            return UNTAGGED_VLAN
        elif operation_mode == "Access":
            return int(settings[0]["AccessVlanId"])

        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Unsupported VLAN mode ({operation_mode}) detected")
        return UNTAGGED_VLAN

    def get_host_os_interfaces(self) -> list[dict[str, str]]:
        """Return dictionary of Host OS Network interfaces.

        :raises: HyperVException when information about Host OS adapters cannot be retrieved
        :return: list of dictionaries with information about each Host OS adapter
        """
        logger.log(level=log_levels.MODULE_DEBUG, msg="Get Host OS adapters")

        command = "Get-VMNetworkAdapter -ManagementOS | select * | fl"

        result = self.connection.execute_powershell(command=command, expected_return_codes={})
        if result.return_code:
            raise HyperVException("Couldn't get information about Host OS adapters")

        return parse_powershell_list(result.stdout.lower())

    def update_host_vnic_attributes(self, vnic_name: str) -> None:
        """Update attributes of a Host OS virtual network interface.

        :param vnic_name: name of the Host OS virtual network interface
        :raises: HyperVException when Host OS network adapter attributes cannot be retrieved
        """
        logger.log(level=log_levels.MODULE_DEBUG, msg="Getting Host OS adapter attributes")

        command = f"Get-VMNetworkAdapter -ManagementOS -Name {vnic_name} | select * | fl"
        result = self.connection.execute_powershell(command=command, expected_return_codes={})
        if result.return_code:
            raise HyperVException(f"Couldn't get Host OS adapter attributes for vNIC {vnic_name}")
        for vnic_interface in self.vm_interfaces:
            if vnic_interface.interface_name == vnic_name:
                vnic_interface.attributes = parse_powershell_list(result.stdout.lower())[0]
