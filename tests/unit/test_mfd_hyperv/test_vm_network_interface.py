# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Tests for `mfd_hyperv` vm network interface."""
from textwrap import dedent

import pytest
from mfd_connect import LocalConnection
from mfd_connect.util.powershell_utils import parse_powershell_list
from mfd_typing import OSName

from mfd_hyperv.instances.vm_network_interface import VMNetworkInterface


class TestVNetworkInterface:
    @pytest.fixture()
    def vmnic(self, mocker):
        conn = mocker.create_autospec(LocalConnection)
        conn.get_os_name.return_value = OSName.WINDOWS
        vmnic = VMNetworkInterface(
            connection=conn,
            interface_name="ifname",
            vm_name="vmname",
            vswitch_name="vswitch_name",
            sriov=True,
            vmq=True,
            vm=mocker.Mock(),
            vswitch=mocker.Mock(),
        )
        mocker.stopall()
        return vmnic

    def test_set_and_verify_attribute(self, vmnic, mocker):
        mocker.patch("mfd_hyperv.vm_network_interface_manager.VMNetworkInterfaceManager.set_vm_interface_attribute")
        mocker.patch("time.sleep")

        attrs = [{"test": "val", "name": "ifname"}]
        vmnic.vm.hyperv.vm_network_interface_manager.get_vm_interface_attributes.return_value = attrs

        vmnic.set_and_verify_attribute("test", "val")

    def test_connect_to_vswitch(self, vmnic, mocker):
        vswitch = mocker.Mock()
        vmnic.connect_to_vswitch(vswitch)

        assert vmnic.vswitch == vswitch

    def test_get_vlan_id(self, vmnic):
        output = dedent(
            """

            OperationMode             : Access
            AccessVlanId              : 21
            NativeVlanId              : 0
            AllowedVlanIdList         : {}
            AllowedVlanIdListString   :
            PrivateVlanMode           : 0
            PrimaryVlanId             : 0
            SecondaryVlanId           : 0
            SecondaryVlanIdList       :
            SecondaryVlanIdListString :
            ParentAdapter             : VMNetworkAdapter (Name = 'VM001_vnic_002', VMName = 'Base_W19_VM001') [VMId = '649efb9b-effe-463b-937d-df9a2fcb68a7']
            IsTemplate                : False
            CimSession                : CimSession: .
            ComputerName              : AMVAL-216-025
            IsDeleted                 : False

            """  # noqa: E501
        )
        vmnic.vm.hyperv.vm_network_interface_manager.get_vm_interface_vlan.return_value = parse_powershell_list(
            output
        )[0]
        assert vmnic.get_vlan_id() == "21"

    def test_get_rdma_status(self, vmnic):
        output = dedent(
            """

            RdmaWeight    : 100
            ParentAdapter : VMNetworkAdapter (Name = 'VM001_vnic_002', VMName = 'Base_W19_VM001') [VMId = '649efb9b-effe-463b-937d-df9a2fcb68a7']
            IsTemplate    : False
            CimSession    : CimSession: .
            ComputerName  : AMVAL-216-025
            IsDeleted     : False

            """  # noqa: E501
        )

        vmnic.vm.hyperv.vm_network_interface_manager.get_vm_interface_rdma.return_value = parse_powershell_list(
            output
        )[0]
        assert vmnic.get_rdma_status()
