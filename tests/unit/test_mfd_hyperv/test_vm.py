# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Tests for `mfd_hyperv` vm."""

import pytest
from mfd_connect import LocalConnection
from mfd_typing import MACAddress, OSName
from mfd_typing.network_interface import InterfaceType

from mfd_hyperv import HyperV
from mfd_hyperv.attributes.vm_params import VMParams
from mfd_hyperv.instances.vm import VM


class TestVM:
    @pytest.fixture()
    def vm(self, mocker):
        vm_params = VMParams(
            name="vm_name",
            cpu_count=4,
            hw_threads_per_core=0,
            memory=4096,
            generation=2,
            vm_dir_path="path",
            diff_disk_path="diff_disk_path",
            mng_interface_name="mng",
            mng_mac_address=MACAddress("00:00:00:00:00:00"),
            mng_ip="1.1.1.1",
            vswitch_name="vswitch",
        )

        conn = mocker.create_autospec(LocalConnection)
        conn.get_os_name.return_value = OSName.WINDOWS
        vm = VM(connection=conn, vm_params=vm_params, owner=mocker.Mock(), hyperv=HyperV(connection=conn))
        mocker.stopall()
        return vm

    def test_object(self, vm):
        vm_params = VMParams(
            name="vm_name",
            cpu_count=4,
            hw_threads_per_core=0,
            memory=4096,
            generation=2,
            vm_dir_path="path",
            diff_disk_path="diff_disk_path",
            mng_interface_name="mng",
            mng_mac_address=MACAddress("00:00:00:00:00:00"),
            mng_ip="1.1.1.1",
            vswitch_name="vswitch",
        )

        vm_dict = vm.vm_params.__dict__

        assert vm_dict == vm_params.__dict__
        assert vm.mng_ip == vm_params.mng_ip
        assert vm.name == vm_params.name

    def test_get_attributes(self, vm, mocker):
        mocker.patch("mfd_hyperv.hypervisor.HypervHypervisor.get_vm_attributes", return_value="x")
        assert vm.get_attributes() == "x"

    def test_start(self, vm, mocker):
        mocker.patch("mfd_hyperv.hypervisor.HypervHypervisor.start_vm", return_value="x")
        mocker.patch("mfd_hyperv.hypervisor.HypervHypervisor.wait_vm_functional", return_value="x")
        mocker.patch("mfd_hyperv.instances.vm.RPyCConnection")

        vm.start()

    def test_match_interfaces(self, vm, mocker):
        from_host_vm_interfaces = [
            {"name": "x", "macaddress": "00:00:00:00:00:01"},
            {"name": "y", "macaddress": "00:00:00:00:00:02"},
        ]
        vm.hyperv.vm_network_interface_manager.all_vnics_attributes = {}
        mocker.patch("mfd_hyperv.instances.vm.VM.get_vm_interfaces", return_value=from_host_vm_interfaces)

        iface1 = mocker.Mock()
        iface1.mac_address = MACAddress("00:00:00:00:00:01")
        iface1.interface_type = InterfaceType.VMNIC
        iface2 = mocker.Mock()
        iface2.mac_address = MACAddress("00:00:00:00:00:02")
        iface2.interface_type = InterfaceType.VF
        iface3 = mocker.Mock()
        iface3.mac_address = MACAddress("00:00:00:00:00:01")
        iface3.interface_type = InterfaceType.VF
        iface4 = mocker.Mock()
        iface4.mac_address = MACAddress("00:00:00:00:00:02")
        iface4.interface_type = InterfaceType.VMNIC
        from_vm_interfaces = [iface1, iface2, iface3, iface4]
        vm.guest = mocker.Mock()
        vm.guest.get_interfaces.return_value = from_vm_interfaces

        vm_iface1 = mocker.Mock()
        vm_iface1.interface_name = "x"
        vm_iface1.vm = vm
        vm_iface2 = mocker.Mock()
        vm_iface2.interface_name = "y"
        vm_iface2.vm = vm

        created_vm_interfaces = [vm_iface1, vm_iface2]
        vm.hyperv.vm_network_interface_manager.vm_interfaces = created_vm_interfaces

        result = vm.match_interfaces()

        assert result[0].interface.vf == iface3
        assert result[1].interface.vf == iface2

    def test_stop(self, vm, mocker):
        mocker.patch("mfd_hyperv.instances.vm.RPyCConnection.shutdown_platform", return_value="x")
        mocker.patch("mfd_hyperv.hypervisor.HypervHypervisor.wait_vm_stopped", return_value="x")
        sleeper = mocker.patch("mfd_hyperv.instances.vm.sleep", return_value=None)

        vm.stop(300)
        vm.hyperv.hypervisor.wait_vm_stopped.assert_called_once_with("vm_name", 300)
        vm.connection.shutdown_platform.assert_called_once()
        sleeper.assert_called_once()

    def test_stop_eoferror(self, vm, mocker):
        mocker.patch("mfd_hyperv.instances.vm.RPyCConnection.shutdown_platform", return_value="x")
        mocker.patch("mfd_hyperv.hypervisor.HypervHypervisor.wait_vm_stopped", return_value="x")
        sleeper = mocker.patch("mfd_hyperv.instances.vm.sleep", return_value=None)

        vm.connection.shutdown_platform.side_effect = EOFError
        vm.stop(timeout=300)
        vm.connection.shutdown_platform.assert_called_once()
        vm.hyperv.hypervisor.wait_vm_stopped.assert_not_called()
        sleeper.assert_not_called()

    def test_reboot(self, vm, mocker):
        mocker.patch("mfd_hyperv.instances.vm.RPyCConnection.restart_platform", return_value="x")
        sleeper = mocker.patch("mfd_hyperv.instances.vm.sleep", return_value="x")

        vm.wait_functional = mocker.Mock()

        vm.reboot(300)
        vm.connection.restart_platform.assert_called_once()
        sleeper.assert_called_once()
        vm.wait_functional.assert_called_once()

    def test_reboot_eoferror(self, vm, mocker):
        mocker.patch("mfd_hyperv.instances.vm.RPyCConnection.restart_platform", return_value="x")
        sleeper = mocker.patch("mfd_hyperv.instances.vm.sleep", return_value="x")

        vm.wait_functional = mocker.Mock()
        vm.connection.restart_platform.side_effect = EOFError

        vm.reboot(300)
        vm.connection.restart_platform.assert_called_once()
        sleeper.assert_not_called()
        vm.wait_functional.assert_called_once()
