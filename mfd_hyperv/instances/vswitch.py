# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Vswitch class."""
import time
from typing import Union, Dict, List, Optional

from mfd_connect import Connection
from mfd_network_adapter import NetworkInterface
from mfd_network_adapter.network_adapter_owner.exceptions import NetworkAdapterIncorrectData
from mfd_network_adapter.network_interface.windows import WindowsNetworkInterface

from mfd_hyperv.attributes.vswitchattributes import VSwitchAttributes
from mfd_hyperv.exceptions import HyperVException
from mfd_hyperv.helpers import standardise_value


class VSwitch:
    """VSwitch class.

    Hyper-V vSwitch has different names in the OS.

    interface_name - name of VSwitch in Hyper-V
    name - name of adapter seen by OS
    """

    def __init__(
        self,
        interface_name: str,
        host_adapter_names: List,
        enable_iov: bool = False,
        enable_teaming: bool = False,
        connection: Optional["Connection"] = None,
        host_adapters: Optional[List[NetworkInterface]] = None,
    ):
        """Class constructor.

        :param interface_name: name of vswitch seen by hyperv
        :param host_adapter_names: names of interfaces that vswitch is created on (1 if normal vswitch, many if teaming)
        :param enable_iov: is vswitch Sriov enabled
        :param enable_teaming: is teaming enabled (in case of multiple ports)
        :param connection: connection instance of MFD connect class.
        :params host_adapters: adapters from config that vswitch is attached to.
        """
        self.interface_name = interface_name
        self.host_adapter_names = host_adapter_names
        self.name = f"vEthernet ({interface_name})"
        self.enable_iov = enable_iov
        self.enable_teaming = enable_teaming
        self.connection = connection

        self.attributes = None
        self._interfaces = None
        self.interfaces = host_adapters  # list of interfaces seen from host that vswitch is created on
        self.interface = None  # vswitch seen as interface from host
        self.owner = None

        if host_adapters:
            self.interfaces_binding()
            time.sleep(3)

            adapter_absent = True
            while adapter_absent:
                try:
                    self.interface = self.owner.get_interface(interface_name=self.name)
                    adapter_absent = False
                except NetworkAdapterIncorrectData:
                    pass

    def __str__(self):
        return f"{self.interface_name} ({[iface.name for iface in self.interfaces]})"

    @property
    def interfaces(self) -> Optional[List[WindowsNetworkInterface]]:
        """Interfaces property representing list of interfaces that vswitch is created on.

        :raises: HyperVException when this property is empty
        """
        if not self._interfaces:
            raise HyperVException(
                "VSwitch has no access to interfaces it is created with. Create binding between objects"
            )
        return self._interfaces

    @interfaces.setter
    def interfaces(self, value: Optional[List[WindowsNetworkInterface]]) -> None:
        """Interfaces property setter."""
        self._interfaces = value

    def interfaces_binding(self) -> None:
        """Create bindings between vswitch and network interfaces objects."""
        for interface in self.interfaces:
            interface.vswitch = self
        self.owner = self.interfaces[0].owner

    def get_attributes(self) -> Dict[str, str]:
        """Return vSwitch attributes in form of dictionary.

        :return: dictionary with vswitch attributes
        """
        self.attributes = self.owner.hyperv.vswitch_manager.get_vswitch_attributes(self.interface_name)
        return self.attributes

    def set_and_verify_attribute(
        self, attribute: Union[VSwitchAttributes, str], value: Union[str, int, bool], sleep_duration: int = 1
    ) -> bool:
        """Set specified vswitch attribute to specified value and check if results where applied in the OS.

        :param attribute: attribute to set
        :param value: new value
        :param sleep_duration: sleep_duration between setting value and reading it
        :returns: whether the set value was also read after it was set
        """
        # some attributes are responsible for 1 functionality but 2 different names are used for setting and getting
        # keys are attributes used for setting
        # values are attributes that are used for getting
        mapping = {"enablerscoffload": "rscoffloadenabled", "enablesoftwarersc": "softwarerscenabled"}

        self.owner.hyperv.vswitch_manager.set_vswitch_attribute(self.interface_name, attribute, value)
        time.sleep(sleep_duration)
        read_value = self.owner.hyperv.vswitch_manager.get_vswitch_attributes(self.interface_name)[
            mapping.get(attribute, attribute)
        ]
        return standardise_value(value) == standardise_value(read_value)

    def remove(self) -> None:
        """Remove vswitch identified by its 'interface_name'."""
        for vnic in self.owner.hyperv.vm_network_interface_manager.vm_interfaces:
            if vnic._vswitch == self:
                vnic.disconnect_from_vswitch()

        self.owner.hyperv.vswitch_manager.remove_vswitch(self.interface_name)
        if self.interfaces:
            for interface in self.interfaces:
                interface.vswitch = None

    def rename(self, new_name: str) -> None:
        """Rename vswitch with a specified name.

        :param new_name: new vSwitch name
        """
        self.owner.hyperv.vswitch_manager.rename_vswitch(self.interface_name, new_name)

        self.interface_name = new_name
        self.name = f"vEthernet ({new_name})"
