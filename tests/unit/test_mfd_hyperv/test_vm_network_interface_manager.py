# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Tests for `mfd_hyperv` vm network interface manager submodule."""
from textwrap import dedent

import pytest
from mfd_common_libs import log_levels
from mfd_connect import LocalConnection
from mfd_connect.base import ConnectionCompletedProcess
from mfd_typing import OSName

from mfd_hyperv.exceptions import HyperVExecutionException
from mfd_hyperv.vm_network_interface_manager import VMNetworkInterfaceManager, UNTAGGED_VLAN


class TestVMNetworkInterfaceManager:
    @pytest.fixture()
    def vmni_manager(self, mocker):
        conn = mocker.create_autospec(LocalConnection)
        conn.get_os_name.return_value = OSName.WINDOWS

        vmni_manager = VMNetworkInterfaceManager(connection=conn)
        return vmni_manager

    def test_create_vm_network_interface(self, vmni_manager, mocker):
        mocker.patch(
            "mfd_hyperv.vm_network_interface_manager.VMNetworkInterfaceManager._generate_name", return_value="x"
        )
        vmni_manager.connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout="output", stderr="stderr"
        )

        mocker.patch("mfd_hyperv.vm_network_interface_manager.VMNetworkInterfaceManager.set_vm_interface_attribute")
        mocker.patch("mfd_hyperv.instances.vm_network_interface.VMNetworkInterface.get_attributes")

        vmni_manager.create_vm_network_interface("vm_name", "vs_name", True, True)

        vmni_manager.connection.execute_powershell.assert_called_with(
            command='Add-VMNetworkAdapter -SwitchName "vs_name" -VMName "vm_name" -Name "x"', expected_return_codes={}
        )

        assert len(vmni_manager.vm_interfaces) == 1

    def test_remove_vm_interface(self, vmni_manager, mocker):
        vmni_manager.vm_interfaces = [
            mocker.Mock(interface_name="x"),
            mocker.Mock(interface_name="y"),
        ]

        vmni_manager.connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout="output", stderr="stderr"
        )

        vmni_manager.remove_vm_interface("x", "vm_name")

        vmni_manager.connection.execute_powershell.assert_called_with(
            command='Remove-VMNetworkAdapter -VMName vm_name -Name "x"', expected_return_codes={}
        )

        assert len(vmni_manager.vm_interfaces) == 1
        assert vmni_manager.vm_interfaces[0].interface_name == "y"

    def test_connect_vm_interface(self, vmni_manager):
        vmni_manager.connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout="output", stderr="stderr"
        )

        vmni_manager.connect_vm_interface("iname", "vm_name", "vswitch_name")

        cmd = 'Connect-VMNetworkAdapter -VMName vm_name -Name "iname" -SwitchName "*vswitch_name*"'
        vmni_manager.connection.execute_powershell.assert_called_with(cmd, expected_return_codes={})

    def test_disconnect_vm_interface(self, vmni_manager):
        vmni_manager.connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout="output", stderr="stderr"
        )

        vmni_manager.disconnect_vm_interface("iname", "vm_name")

        vmni_manager.connection.execute_powershell.assert_called_with(
            command="Disconnect-VMNetworkAdapter -VMName vm_name -Name iname", expected_return_codes={}
        )

    def test_set_vm_interface_attribute(self, vmni_manager):
        vmni_manager.connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout="output", stderr="stderr"
        )

        vmni_manager.set_vm_interface_attribute("iname", "vm_name", "attr", "val")

        vmni_manager.connection.execute_powershell.assert_called_with(
            command='Set-VMNetworkAdapter -Name "iname" -VMName vm_name -attr val', expected_return_codes={}
        )

    def test_get_vm_interface_attributes(self, vmni_manager):
        out = """
            Name : vm001_vnic_001
            Status : {ok}
            IPAddresses : {169.254.168.197, fe80::fd4a:a46a:2c05:90b}
        """
        vmni_manager.connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout=out, stderr="stderr"
        )

        res = vmni_manager.get_vm_interface_attributes("vm_name")

        vmni_manager.connection.execute_powershell.assert_called_with(
            command="Get-VMNetworkAdapter -Name * -VMName vm_name | select * | fl", expected_return_codes={}
        )

        assert res[0]["status"] == "{ok}"
        assert res[0]["name"] == "vm001_vnic_001"
        assert res[0]["ipaddresses"] == "{169.254.168.197, fe80::fd4a:a46a:2c05:90b}"

    def test_get_vm_interfaces(self, vmni_manager):
        out = """
            Name : mng
        """
        vmni_manager.connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout=out, stderr="stderr"
        )

        res = vmni_manager.get_vm_interfaces("vm_name")

        vmni_manager.connection.execute_powershell.assert_called_with(
            command="Get-VMNetworkAdapter -VMName vm_name | select * | fl", expected_return_codes={}
        )

        assert len(res) == 1
        assert res[0]["name"] == "mng"

    def test_get_vlan_id_for_vswitch_access_mode(self, vmni_manager):
        output1 = dedent(
            """
        VMNetworkAdapter1
        """
        )
        output2 = dedent(
            """
            Name                          : VMNetworkAdapter1
            OperationMode                 : Access
            AccessVlanId                  : 10
            """
        )
        vmni_manager.connection.execute_powershell.side_effect = [
            ConnectionCompletedProcess(return_code=0, args="command", stdout=output1, stderr="stderr"),
            ConnectionCompletedProcess(return_code=0, args="command", stdout=output2, stderr="stderr"),
        ]
        vlan_id = vmni_manager.get_vlan_id_for_vswitch("managementvSwitch")
        assert vlan_id == 10

    def test_get_host_os_interfaces(self, vmni_manager):
        output = dedent(
            """
            Name : HostAdapter1
            Status : {ok}
            IPAddresses : {192.168.1.1, fe80::1}
            """
        )
        vmni_manager.connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout=output, stderr="stderr"
        )

        res = vmni_manager.get_host_os_interfaces()

        vmni_manager.connection.execute_powershell.assert_called_with(
            command="Get-VMNetworkAdapter -ManagementOS | select * | fl", expected_return_codes={}
        )

        assert len(res) == 1
        assert res[0]["name"] == "hostadapter1"
        assert res[0]["status"] == "{ok}"
        assert res[0]["ipaddresses"] == "{192.168.1.1, fe80::1}"

    def test_update_host_vnic_attributes(self, vmni_manager, mocker):
        output = dedent(
            """
            Name : HostAdapter1
            Status : {ok}
            IPAddresses : {192.168.1.1, fe80::1}
            """
        )
        vmni_manager.connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout=output, stderr="stderr"
        )

        vmni_manager.vm_interfaces = [mocker.Mock(interface_name="HostAdapter1", attributes=None)]

        vmni_manager.update_host_vnic_attributes("HostAdapter1")

        vmni_manager.connection.execute_powershell.assert_called_with(
            command="Get-VMNetworkAdapter -ManagementOS -Name HostAdapter1 | select * | fl", expected_return_codes={}
        )

        assert vmni_manager.vm_interfaces[0].attributes["name"] == "hostadapter1"

    def test_get_vm_interface_attached_to_vswitch(self, vmni_manager):
        output = "VMNetworkAdapter1"
        vmni_manager.connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout=output, stderr="stderr"
        )

        res = vmni_manager.get_vm_interface_attached_to_vswitch("managementvSwitch")

        vmni_manager.connection.execute_powershell.assert_called_with(
            "(Get-VMNetworkAdapter -ManagementOS | ? { $_.SwitchName -eq 'managementvSwitch'}).Name",
            custom_exception=HyperVExecutionException,
        )

        assert res == "VMNetworkAdapter1"

    def test_get_vm_interface_attached_to_vswitch_error(self, vmni_manager):
        vmni_manager.connection.execute_powershell.side_effect = HyperVExecutionException(
            returncode=1, cmd="", output="", stderr="Error message"
        )
        with pytest.raises(HyperVExecutionException):
            vmni_manager.get_vm_interface_attached_to_vswitch("managementvSwitch")

    def test_get_vlan_id_for_vswitch_auto_mode(self, vmni_manager, caplog):
        caplog.set_level(log_levels.MODULE_DEBUG)
        output1 = dedent(
            """
        VMNetworkAdapter1
        """
        )
        output2 = dedent(
            """
            Name                          : VMNetworkAdapter1
            Id                            : 1
            InterfaceDescription          : "Virtual Ethernet Adapter for VM Network Adapter 1"
            MacAddress                    : 00-11-22-33-44-55-66-77
            VlanId                        : 10
            OperationMode                 : Auto
            """
        )
        vmni_manager.connection.execute_powershell.side_effect = [
            ConnectionCompletedProcess(return_code=0, args="command", stdout=output1, stderr="stderr"),
            ConnectionCompletedProcess(return_code=0, args="command", stdout=output2, stderr="stderr"),
        ]
        vlan_id = vmni_manager.get_vlan_id_for_vswitch("managementvSwitch")
        assert UNTAGGED_VLAN == vlan_id
        assert "Unsupported VLAN mode (Auto) detected" in caplog.messages[1]

    def test_get_vlan_id_for_vswitch_untagged_mode(self, vmni_manager):
        output1 = dedent(
            """
            VMNetworkAdapter1
            """
        )
        output2 = dedent(
            """
            Name                          : VMNetworkAdapter1
            OperationMode                 : Untagged
            """
        )
        vmni_manager.connection.execute_powershell.side_effect = [
            ConnectionCompletedProcess(return_code=0, args="command", stdout=output1, stderr="stderr"),
            ConnectionCompletedProcess(return_code=0, args="command", stdout=output2, stderr="stderr"),
        ]

        vlan_id = vmni_manager.get_vlan_id_for_vswitch("managementvSwitch")

        assert vlan_id == 0
