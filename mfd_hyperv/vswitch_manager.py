# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Main module."""
import logging
import re
import time
from typing import TYPE_CHECKING, Union, Dict, List, Optional

from mfd_common_libs import os_supported, add_logging_level, log_levels, TimeoutCounter
from mfd_common_libs.log_levels import MODULE_DEBUG
from mfd_connect.util.powershell_utils import parse_powershell_list
from mfd_network_adapter.network_interface.windows import WindowsNetworkInterface
from mfd_typing import OSName

from mfd_hyperv.attributes.vswitchattributes import VSwitchAttributes
from mfd_hyperv.exceptions import HyperVExecutionException, HyperVException
from mfd_hyperv.helpers import standardise_value
from mfd_hyperv.instances.vswitch import VSwitch

if TYPE_CHECKING:
    from mfd_connect import Connection

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class VSwitchManager:
    """Module for VSwitch Manager."""

    mng_vswitch_name = "managementvSwitch"
    vswitch_name_prefix = "VSWITCH"
    vswitch_name_counter = 1

    @os_supported(OSName.WINDOWS)
    def __init__(self, *, connection: "Connection"):
        """Class constructor.

        :param connection: connection instance of MFD connect class.
        """
        self.connection = connection
        self.vswitches = []

    def create_vswitch(
        self,
        interface_names: List[str],
        vswitch_name: str = vswitch_name_prefix,
        enable_iov: bool = False,
        enable_teaming: bool = False,
        mng: bool = False,
        interfaces: Optional[List[WindowsNetworkInterface]] = None,
    ) -> VSwitch:
        """Create vSwitch.

        :param vswitch_name: Name of virtual switch
        :param interface_names: list of names of network interface that vswitch will be created on
        :param enable_iov: is vswitch Sriov enabled
        :param enable_teaming: is teaming enabled (in case of multiple ports)
        :param mng: whether this vswitch is mng or not
        :param interfaces:interfaces objects that vswitch is connected to
        :return: created vswitch
        """
        interface_names = ", ".join([f"'{item}'" for item in interface_names])
        final_vswitch_name = vswitch_name if mng else self._generate_name(vswitch_name, enable_teaming)

        logger.log(level=MODULE_DEBUG, msg=f"Creating vSwitch {vswitch_name} on adapter {interface_names}")
        cmd = (
            'powershell.exe "New-VMSwitch'
            f" -Name '{final_vswitch_name}' -NetAdapterName {interface_names} -AllowManagementOS $true"
            f' -EnableIov ${enable_iov}"'
        )
        if enable_teaming:
            cmd = cmd[:-1]
            cmd += ' -EnableEmbeddedTeaming $true"'

        self.connection.start_process(cmd, shell=True)
        self.wait_vswitch_present(final_vswitch_name, timeout=120, interval=2)

        vs = VSwitch(final_vswitch_name, interface_names, enable_iov, enable_teaming, self.connection, interfaces)

        if not mng:
            self.vswitches.append(vs)
        return vs

    def _generate_name(self, vswitch_name: str, enable_teaming: bool) -> str:
        """Create unified vswitch name.

        :param vswitch_name: name of Virtual Machine adapter belongs to
        :param enable_teaming: if temaming is enabled
        """
        name = f"{vswitch_name}_{self.vswitch_name_counter:02}{'_T' if enable_teaming else ''}"
        self.vswitch_name_counter += 1
        return name

    def create_mng_vswitch(self) -> VSwitch:
        """Create management vSwitch."""
        if self.is_vswitch_present(self.mng_vswitch_name):
            return VSwitch(
                interface_name=self.mng_vswitch_name,
                host_adapter_names=[],
                connection=self.connection,
            )

        cmd = (
            f"Get-NetIPAddress | Where-Object -Property IPAddress -EQ {self.connection._ip} | "
            f"Where-Object -Property AddressFamily -EQ 'IPv4' | select -ExpandProperty InterfaceAlias"
        )
        interface_name = self.connection.execute_powershell(cmd, expected_return_codes={0}).stdout.strip()
        return self.create_vswitch([interface_name], self.mng_vswitch_name, mng=True)

    def remove_vswitch(self, interface_name: str) -> None:
        """Remove vswitch identified by its 'interface_name'.

        :param interface_name: Virtual Switch interface name
        """
        logger.log(level=MODULE_DEBUG, msg=f"Removing {interface_name}...")
        self.connection.execute_powershell(
            f"Remove-VMSwitch {interface_name} -Force", custom_exception=HyperVExecutionException
        )
        logger.log(level=MODULE_DEBUG, msg=f"Successfully removed {interface_name}")

        # cleanup bindings
        vswitch = [vs for vs in self.vswitches if vs.interface_name == interface_name]
        if not vswitch:
            return

        vswitch = vswitch[0]
        self.vswitches.remove(vswitch)

    def get_vswitch_mapping(self) -> dict[str, str]:
        """Get a list of Hyper-V vSwitches and the adapters they are mapped to.

        return: Dictionary where key are names of vswitches, values are Friendly names of an interfaces connect to
                (NetAdapterInterfaceDescription field from powershell output)
        """
        outcome = self.connection.execute_powershell("Get-VMSwitch | fl", expected_return_codes=None)
        if outcome.return_code:
            return {}
        output = parse_powershell_list(outcome.stdout)
        # SET vSwitch adapter, has NetAdapterInterfaceDescription = Teamed-Interface.
        # But for mapping, there is a needed, that description have to be 1st pf member of the team, that is why,
        # there is [0] element used.
        for line in output:
            if line["EmbeddedTeamingEnabled"] == "True":
                line["NetAdapterInterfaceDescription"] = (
                    line["NetAdapterInterfaceDescriptions"].replace("{", "").replace("}", "").split(",")[0]
                )
        return dict((line["Name"], line["NetAdapterInterfaceDescription"]) for line in output)

    def get_vswitch_attributes(self, interface_name: str) -> Dict[str, str]:
        """Return vSwitch attributes in form of dictionary.

        :param interface_name: Virtual Switch interface name
        :raises: HyperVException  when information about vswitch cannot be retrieved
        :return: dictionary with vswitch attributes
        """
        logger.log(level=MODULE_DEBUG, msg=f"Retrieving {interface_name} attributes...")
        result = self.connection.execute_powershell(
            f"Get-VMSwitch {interface_name} | select * | fl", expected_return_codes={}
        )
        if result.return_code:
            raise HyperVException(f"Couldn't get information about vSwitch {interface_name}")

        return parse_powershell_list(result.stdout.lower())[0]

    def set_vswitch_attribute(
        self, interface_name: str, attribute: Union[VSwitchAttributes, str], value: Union[str, int, bool]
    ) -> None:
        """Set attribute on VSwitch.

        :param interface_name: Virtual Switch interface_name
        :param attribute: Attribute to be set on vSwitch
        :param value: Value of set attribute
        :return: value of set attribute
        """
        if isinstance(attribute, VSwitchAttributes):
            attribute = attribute.value

        value = standardise_value(value)
        logger.log(level=MODULE_DEBUG, msg=f"Setting new value {value} of {attribute} on {interface_name}")

        command = f"Set-VMSwitch -Name {interface_name} -{attribute} {value}"
        self.connection.execute_powershell(command, custom_exception=HyperVExecutionException)

    def remove_tested_vswitches(self) -> None:
        """Remove all tested vswitches."""
        logger.log(level=MODULE_DEBUG, msg=f"Removing all tested (non-{self.mng_vswitch_name}) vSwitches...")

        self.connection.execute_powershell(
            "Get-VMSwitch | Where-Object {$_.Name -ne "
            f'"{self.mng_vswitch_name}"'
            "} | Remove-VMSwitch -force -Confirm:$false",
            custom_exception=HyperVExecutionException,
        )

        logger.log(level=MODULE_DEBUG, msg="Successfully removed all tested vSwitches")

        # cleanup bindings
        for vswitch in self.vswitches:
            if not vswitch._interfaces:
                continue
            for interface in vswitch.interfaces:
                interface.vswitch = None
        self.vswitches.clear()

    def is_vswitch_present(self, interface_name: str) -> bool:
        """Check if given virtual switch is present.

        :param interface_name: Virtual Switch interface_name
        :return: whether vswitch is present or not
        """
        logger.log(level=MODULE_DEBUG, msg=f"Checking if {interface_name} exists...")
        out = self.connection.execute_powershell(
            "Get-VMSwitch | select -expandproperty Name", custom_exception=HyperVExecutionException
        )

        result = re.findall(rf"\b{interface_name}\b", out.stdout)
        return interface_name in result

    def wait_vswitch_present(self, vswitch_name: str, timeout: int = 60, interval: int = 10) -> None:
        """Wait for timeout duration for vswitch to appear present.

        :param vswitch_name: Name of vSwitch
        :param interval: sleep duration between retries
        :param timeout: maximum time of waiting for vswitch to appear
        :raises: HyperVException when specified vswitch is not present among other vswitches
        :return: whether vswitch is present or not
        """
        timeout_reached = TimeoutCounter(timeout)
        while not timeout_reached:
            try:
                if self.is_vswitch_present(vswitch_name):
                    logger.log(level=MODULE_DEBUG, msg=f"Successfully created vSwitch {vswitch_name}")
                    return
            except (EOFError, OSError):
                logger.log(level=MODULE_DEBUG, msg=f"Waiting for vSwitch '{vswitch_name}' object.")
            time.sleep(interval)
        else:
            raise HyperVException(f"Timeout expired. Cannot find vswitch {vswitch_name}")

    def rename_vswitch(self, interface_name: str, new_name: str) -> None:
        """Rename given vSwitch.

        :param interface_name: Virtual Switch interface_name
        :param new_name: new vSwitch interface_name
        """
        logger.log(level=MODULE_DEBUG, msg=f"Renaming vSwitch {interface_name} to {new_name}...")

        self.connection.execute_powershell(
            f'Rename-VMSwitch "{interface_name}" -NewName "{new_name}"',
            custom_exception=HyperVExecutionException,
        )

        out = self.get_vswitch_attributes(interface_name=new_name)

        if out["name"] == new_name:
            logger.log(level=MODULE_DEBUG, msg=f"Successfully renamed vSwitch {interface_name} to {new_name}")
        else:
            raise HyperVException(f"Could not rename vSwitch {interface_name} to {new_name}")
