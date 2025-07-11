# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Tests for `mfd_hyperv` hypervisor submodule."""

from pathlib import Path

import pytest
from mfd_connect import LocalConnection
from mfd_connect.base import ConnectionCompletedProcess
from mfd_ping import PingResult
from mfd_typing import OSName, MACAddress
from netaddr import IPAddress

from mfd_hyperv.attributes.vm_params import VMParams
from mfd_hyperv.exceptions import HyperVException, HyperVExecutionException
from mfd_hyperv.hypervisor import HypervHypervisor


class TestHypervisor:
    @pytest.fixture()
    def hypervisor(self, mocker):
        conn = mocker.create_autospec(LocalConnection)
        conn.get_os_name.return_value = OSName.WINDOWS

        hypervisor = HypervHypervisor(connection=conn)
        mocker.stopall()
        return hypervisor

    @pytest.fixture()
    def hypervisor_with_2_vms(self, mocker, hypervisor):
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

        output = """
                    VMName      : Base_W19_VM001
                    IPAddresses : {10.91.218.16, fe80::6994:9bd4:d0aa:ff4d}
                    MacAddress  : 525A005BDA10
                """

        hypervisor._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout=output, stderr="stderr"
        )

        mocker.patch("mfd_hyperv.hypervisor.HypervHypervisor.start_vm", return_value=None)
        mocker.patch("mfd_hyperv.hypervisor.RPyCConnection", autospec=True)
        mocker.patch("mfd_hyperv.instances.vm.NetworkAdapterOwner", autospec=True)

        for i in range(2):
            vm_params.name = f"vm_name_{i}"
            hypervisor.create_vm(vm_params)

        return hypervisor

    def test_is_hyperv_enabled(self, hypervisor):
        out_positive = """
            FeatureName      : Microsoft-Hyper-V
            DisplayName      : Hyper-V
            Description      : Hyper-V
            RestartRequired  : Possible
            State            : Enabled
        """

        out_negative = """
            FeatureName      : Microsoft-Hyper-V
            DisplayName      : Hyper-V
            Description      : Hyper-V
            RestartRequired  : Possible
            State            : Disabled
        """
        hypervisor._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout=out_positive, stderr="stderr"
        )
        assert hypervisor.is_hyperv_enabled()

        hypervisor._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout=out_negative, stderr="stderr"
        )
        assert not hypervisor.is_hyperv_enabled()

    def test_create_vm(self, mocker, hypervisor):
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
        output = """
            VMName      : Base_W19_VM001
            IPAddresses : {10.91.218.16, fe80::6994:9bd4:d0aa:ff4d}
            MacAddress  : 525A005BDA10
        """

        hypervisor._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout=output, stderr="stderr"
        )

        mocker.patch("mfd_hyperv.hypervisor.HypervHypervisor.start_vm", return_value=None)
        mocker.patch("mfd_hyperv.hypervisor.RPyCConnection", autospec=True)
        mocker.patch("mfd_hyperv.hypervisor.VM", autospec=True)

        hypervisor.create_vm(vm_params, dynamic_mng_ip=True)
        assert len(hypervisor.vms) == 1

    def test_remove_vm_all(self, hypervisor_with_2_vms):
        hypervisor_with_2_vms._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout="stdout", stderr="stderr"
        )

        hypervisor_with_2_vms.remove_vm()
        assert len(hypervisor_with_2_vms.vms) == 0

    def test_remove_vm_single(self, hypervisor_with_2_vms):
        hypervisor_with_2_vms._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout="stdout", stderr="stderr"
        )

        hypervisor_with_2_vms.remove_vm("vm_name_0")
        assert len(hypervisor_with_2_vms.vms) == 1
        assert hypervisor_with_2_vms.vms[0].name == "vm_name_1"

    def test_start_vm(self, hypervisor):
        hypervisor._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout="stdout", stderr="stderr"
        )
        hypervisor.start_vm()

        hypervisor._connection.execute_powershell.assert_called_once_with(
            "Start-VM *",
            expected_return_codes={},
        )

        hypervisor.start_vm("vm")

        hypervisor._connection.execute_powershell.assert_called_with(
            "Start-VM vm",
            expected_return_codes={},
        )

    def test_stop_vm(self, hypervisor):
        hypervisor._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout="stdout", stderr="stderr"
        )
        hypervisor.stop_vm()

        hypervisor._connection.execute_powershell.assert_called_once_with(
            "Stop-VM *",
            expected_return_codes={},
        )

        hypervisor.stop_vm("vm")

        hypervisor._connection.execute_powershell.assert_called_with(
            "Stop-VM vm",
            expected_return_codes={},
        )

    def test_vm_connectivity_test(self, hypervisor, mocker):
        mocker.patch("mfd_hyperv.hypervisor.time.sleep")
        mocker.patch("mfd_hyperv.hypervisor.TimeoutCounter", return_value=True)
        mocker.patch("mfd_ping.windows.WindowsPing.stop", return_value=PingResult(4, 0))
        assert hypervisor._vm_connectivity_test(mocker.create_autospec(IPAddress))

        mocker.patch("mfd_ping.windows.WindowsPing.stop", return_value=PingResult(0, 4))
        assert not hypervisor._vm_connectivity_test(mocker.create_autospec(IPAddress))

    def test_wait_vm_functional(self, hypervisor, mocker):
        mocker.patch("mfd_hyperv.hypervisor.TimeoutCounter", return_value=False)
        mocker.patch("mfd_hyperv.hypervisor.HypervHypervisor._vm_connectivity_test", return_value=True)
        mocker.patch("mfd_hyperv.hypervisor.HypervHypervisor.get_vm_state", return_value="Running")

        hypervisor.wait_vm_functional(mocker.Mock(), mocker.Mock())

    def test_wait_vm_stopped(self, hypervisor, mocker):
        mocker.patch("mfd_hyperv.hypervisor.TimeoutCounter", return_value=False)
        mocker.patch("mfd_hyperv.hypervisor.HypervHypervisor.get_vm_state", return_value="Off")

        hypervisor.wait_vm_stopped(mocker.Mock())

    def test_get_vm_state(self, hypervisor, mocker):
        out_positive = """
                   FeatureName      : Microsoft-Hyper-V
                   DisplayName      : Hyper-V
                   Description      : Hyper-V
                   RestartRequired  : Possible
                   State            : Enabled
               """

        out_negative = """
                   FeatureName      : Microsoft-Hyper-V
                   DisplayName      : Hyper-V
                   Description      : Hyper-V
                   RestartRequired  : Possible
                   State            : Disabled
               """

        hypervisor._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout=out_positive, stderr="stderr"
        )
        assert hypervisor.get_vm_state(mocker.Mock()) == "Enabled"

        hypervisor._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout=out_negative, stderr="stderr"
        )
        assert hypervisor.get_vm_state(mocker.Mock()) == "Disabled"

    def test_restart_vm(self, hypervisor):
        hypervisor._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout="stdout", stderr="stderr"
        )
        hypervisor.restart_vm()

        hypervisor._connection.execute_powershell.assert_called_once_with(
            "Restart-VM * -force -confirm:$false",
            expected_return_codes={},
        )

        hypervisor._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout="stdout", stderr="stderr"
        )
        hypervisor.restart_vm("name")

        hypervisor._connection.execute_powershell.assert_called_with(
            "Restart-VM name -force -confirm:$false",
            expected_return_codes={},
        )

    def test_clear_vm_locations(self, hypervisor, mocker):
        output = {
            "D:": 124321432,
            "E:": 435435436,
        }

        mocker.patch("mfd_hyperv.hypervisor.HypervHypervisor._get_disks_free_space", return_value=output)

        hypervisor._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout="stdout", stderr="stderr"
        )

        hypervisor.clear_vm_locations()

        calls = [
            mocker.call("Remove-Item -Recurse -Force E:\\VMs\\*"),
            mocker.call("Remove-Item -Recurse -Force D:\\VMs\\*"),
        ]

        hypervisor._connection.execute_powershell.assert_has_calls(calls, any_order=True)

    def test_get_vm_attributes(self, hypervisor):
        output = """
            Name             : Base_R92_VM001
            State            : Running
            CpuUsage         : 0
            MemoryAssigned   : 4294967296
            MemoryDemand     : 2705326080
            MemoryStatus     :
            Uptime           : 00:03:47.9220000
            Status           : Operating normally
            ReplicationState : Disabled
            Generation       : 2
        """

        hypervisor._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout=output, stderr="stderr"
        )

        expected_obj = {
            "Name": "Base_R92_VM001",
            "State": "Running",
            "CpuUsage": "0",
            "MemoryAssigned": "4294967296",
            "MemoryDemand": "2705326080",
            "MemoryStatus": "",
            "Uptime": "00:03:47.9220000",
            "Status": "Operating normally",
            "ReplicationState": "Disabled",
            "Generation": "2",
        }

        assert hypervisor.get_vm_attributes("test") == expected_obj
        hypervisor._connection.execute_powershell.assert_called_once_with(
            "Get-VM test | select * | fl",
            expected_return_codes={},
        )

    def test_get_vm_processor_attributes(self, hypervisor):
        output = """
            ResourcePoolName                             : Primordial
            Count                                        : 2
            CompatibilityForMigrationEnabled             : False
            CompatibilityForMigrationMode                : MinimumFeatureSet
            CompatibilityForOlderOperatingSystemsEnabled : False
            HwThreadCountPerCore                         : 0
            ExposeVirtualizationExtensions               : False
            EnablePerfmonPmu                             : False
            EnablePerfmonLbr                             : False
            EnablePerfmonPebs                            : False
            EnablePerfmonIpt                             : False
            EnableLegacyApicMode                         : False
            ApicMode                                     : Default
            AllowACountMCount                            : True
            CpuBrandString                               :
            PerfCpuFreqCapMhz                            : 0
            Maximum                                      : 100
            Reserve                                      : 0
            RelativeWeight                               : 100
            MaximumCountPerNumaNode                      : 36
            MaximumCountPerNumaSocket                    : 1
            EnableHostResourceProtection                 : False
            OperationalStatus                            : {Ok, HostResourceProtectionDisabled}
            StatusDescription                            : {OK, Host resource protection is disabled.}
            Name                                         : Processor
            Id                                           : Microsoft:4711AB94-4AED-40B8-B3A0-9388049571AB\b637f346-6a0e-4dec-af52-b
                                                           d70cb80a21d\0
            VMId                                         : 4711ab94-4aed-40b8-b3a0-9388049571ab
            VMName                                       : Base_R92_VM001
            VMSnapshotId                                 : 00000000-0000-0000-0000-000000000000
            VMSnapshotName                               :
            CimSession                                   : CimSession: .
            ComputerName                                 : AMVAL-216-025
            IsDeleted                                    : False
            VMCheckpointId                               : 00000000-0000-0000-0000-000000000000
            VMCheckpointName                             :
        """  # noqa: E501

        hypervisor._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout=output, stderr="stderr"
        )

        assert len(hypervisor.get_vm_processor_attributes("name").keys()) == 35

        hypervisor._connection.execute_powershell.assert_called_once_with(
            "Get-VMProcessor -VMName name | select * | fl",
            expected_return_codes={},
        )

    def test_set_vm_processor_attribute(self, hypervisor, mocker):
        hypervisor._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout="output", stderr="stderr"
        )

        hypervisor.set_vm_processor_attribute("name", mocker.Mock(), mocker.Mock())

        hypervisor._connection.execute_powershell.assert_called()

    def test_get_disks_free_space(self, hypervisor, mocker):
        output = """
            Caption DriveType    FreeSpace         Size
            ------- ---------    ---------         ----
            C:       3          37575798784    64317550592
            D:       3          110013030400   254060523520
            Z:       4          1874351206400  7433549180928
        """

        hypervisor._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout=output, stderr="stderr"
        )

        expected_obj = {
            "D:\\": {"free": "110013030400", "total": "254060523520"},
            "C:\\": {"free": "37575798784", "total": "64317550592"},
        }

        assert hypervisor._get_disks_free_space() == expected_obj

    def test_get_disks_free_space_failing(self, hypervisor):
        output = """
            Caption DriveType    FreeSpace         Size
            ------- ---------    ---------         ----
            Z:       4          1874351206400  7433549180928
        """

        hypervisor._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout=output, stderr="stderr"
        )

        with pytest.raises(HyperVException, match="Expected partition was not found."):
            hypervisor._get_disks_free_space()

    def test_get_disk_paths_with_enough_space(self, hypervisor, mocker):
        disks = {"emu": {"free": "110013030400", "total": "254060523520"}}
        mocker.patch("mfd_hyperv.hypervisor.HypervHypervisor._get_disks_free_space", return_value=disks)

        hypervisor._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout="output", stderr="stderr"
        )

        hypervisor._connection.path = Path

        assert hypervisor.get_disk_paths_with_enough_space(1234) == str(Path(r"emu/VMs"))

    def test_get_disk_paths_with_enough_space_failing(self, hypervisor, mocker):
        disks = {"D:\\": {"free": "110013030400", "total": "254060523520"}}
        mocker.patch("mfd_hyperv.hypervisor.HypervHypervisor._get_disks_free_space", return_value=disks)

        hypervisor._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout="output", stderr="stderr"
        )

        with pytest.raises(HyperVException, match="No disk that has enough space"):
            hypervisor.get_disk_paths_with_enough_space(210013030400)

    def test_copy_vm_image_no_zip(self, hypervisor, mocker):
        hypervisor._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout="output", stderr="stderr"
        )

        mocker.patch("time.sleep")
        hypervisor._connection.path.return_value = Path("D:\\dst\\img.vhdx")
        mocker.patch("mfd_connect.util.rpc_copy_utils._check_paths")
        mocker.patch("mfd_connect.util.rpc_copy_utils.copy")

        assert hypervisor.copy_vm_image("img.vhdx", "D:\\dst", r"C:\\src") == Path("D:\\dst\\img.vhdx")

    def test_copy_vm_image_zip(self, hypervisor, mocker):
        hypervisor._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout="output", stderr="stderr"
        )

        mocker.patch("time.sleep")
        hypervisor._connection.path.return_value = Path("D:\\dst\\img.vhdx")
        mocker.patch("pathlib.Path.exists", return_value=True)

        assert hypervisor.copy_vm_image("img.vhdx", "D:\\dst", r"C:\\src") == Path("D:\\dst\\img.vhdx")

    def test_copy_vm_image_zip_windows_16(self, hypervisor, mocker):
        hypervisor._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout="output", stderr="stderr"
        )

        mocker.patch("time.sleep")
        hypervisor._connection.path.return_value = Path("D:\\dst\\img.vhdx")
        mocker.patch("pathlib.Path.exists", return_value=True)
        hypervisor._connection.get_system_info().os_name = "Windows 2016"

        assert hypervisor.copy_vm_image("img.vhdx", "D:\\dst", r"C:\\src") == Path("D:\\dst\\img.vhdx")

    def test_get_file_metadata(self, hypervisor, mocker):
        outputs = [
            """
            Directory: D:\VM-Template


            Name           : Base_R88.vhdx
            Length         : 19990052864
            CreationTime   : 7/21/2023 3:49:16 PM
            LastWriteTime  : 7/7/2023 7:44:33 AM
            LastAccessTime : 7/21/2023 3:52:19 PM
            Mode           : -a----
            LinkType       :
            Target         : {}
            VersionInfo    : File:             D:\VM-Template\Base_R88.vhdx
                             InternalName:
                             OriginalFilename:
                             FileVersion:
                             FileDescription:
                             Product:
                             ProductVersion:
                             Debug:            False
                             Patched:          False
                             PreRelease:       False
                             PrivateBuild:     False
                             SpecialBuild:     False
                             Language:
            """,  # noqa: E501, W291, W605, W293
            """
            Directory: fdsfdssfsf

             Name : Base_W19.vhdx
             if ($_ -is [System.IO.DirectoryInfo]) { return '' }
             if ($_.Attributes -band [System.IO.FileAttributes]::Offline)
             {
                 return '({0})' -f $_.Length
             }
             return $_.Length : 19990052864
             CreationTime                                                            : 7/6/2023 9:41:18 AM
             LastWriteTime                                                           : 7/7/2023 7:44:33 AM
             LastAccessTime                                                          : 8/1/2023 10:19:44 PM
             Mode                                                                    : -a----
             LinkType                                                                : 
             Target                                                                  :
             VersionInfo                                                             : File:             gfdgdgggf
                                                                                    InternalName:
                                                                                    OriginalFilename:
                                                                                    FileVersion:
                                                                                    FileDescription:
                                                                                    Product:
                                                                                    ProductVersion:
                                                                                    Debug:            False
                                                                                    Patched:          False
                                                                                    PreRelease:       False
                                                                                    PrivateBuild:     False
                                                                                    SpecialBuild:     False
                                                                                    Language:
            """,  # noqa: E501, W291, W605, W293
            """
            Directory: fdsfdsf

            Name : Base_W19.vhdx
                 if ($_ -is [System.IO.DirectoryInfo]) { return '' }
                 if ($_.Attributes -band [System.IO.FileAttributes]::Offline)
                 {
                     return '({0})' -f $_.Length
                 }
                 return $_.Length
                 :
                  19990052864
                 CreationTime : 7/6/2023 9:41:18 AM
                 LastWriteTime
                 : 
                 7/7/2023 7:44:33 AM
                 LastAccessTime : 8/1/2023 10:19:44 PM
                 Mode : -a----
                 LinkType :
                 Target :
                 VersionInfo : File:             \\src\img.vhdx
            """,  # noqa: E501, W291, W605, W293
        ]
        expected_value = {"lwt": "7/7/2023 7:44:33 AM", "length": "19990052864"}

        for output in outputs:
            hypervisor._connection.execute_powershell.return_value = ConnectionCompletedProcess(
                return_code=0, args="command", stdout=output, stderr="stderr"
            )

            assert hypervisor._get_file_metadata(mocker.Mock()) == expected_value

    def test_get_file_metadata_fail(self, hypervisor, mocker):
        hypervisor._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout="", stderr="stderr"
        )

        with pytest.raises(HyperVException):
            hypervisor._get_file_metadata(mocker.Mock())

    def test_is_same_metadata(self, hypervisor):
        file1_metadata = {"lwt": "7/7/2023 7:44:33 AM", "length": "19990052864"}

        file2_metadatas = [
            # the same
            {"lwt": "7/7/2023 7:44:33 AM", "length": "19990052864"},
            # 12 hour later
            {"lwt": "7/7/2023 7:44:33 PM", "length": "19990052864"},
            # 300 seconds later
            {"lwt": "7/7/2023 7:49:33 AM", "length": "19990052864"},
            # 300 seconds earlier
            {"lwt": "7/7/2023 7:39:33 AM", "length": "19990052864"},
            # 301 seconds later
            {"lwt": "7/7/2023 7:49:34 AM", "length": "19990052864"},
            # 301 seconds earlier
            {"lwt": "7/7/2023 7:39:32 AM", "length": "19990052864"},
            # different size
            {"lwt": "7/7/2023 7:44:33 AM", "length": "1"},
        ]

        expected_results = [True, False, True, True, False, False, False]
        metadata_pairs = map(lambda file2_metadata: (file1_metadata, file2_metadata), file2_metadatas)

        for pair, expected_result in zip(metadata_pairs, expected_results):
            f1_metadata, f2_metadata = pair
            assert hypervisor._is_same_metadata(f1_metadata, f2_metadata) == expected_result

    def test_is_latest_image(self, hypervisor, mocker):
        mocker.patch("pathlib.Path.exists", return_value=False)

        mocker.patch("mfd_hyperv.hypervisor.HypervHypervisor._get_file_metadata")
        mocker.patch("mfd_hyperv.hypervisor.HypervHypervisor._is_same_metadata", return_value=True)
        assert hypervisor.is_latest_image(mocker.Mock(), r"C:\\src")

    def test_is_latest_image_non_existent(self, hypervisor, mocker):
        hypervisor._connection.path.return_value = Path("D:\\dst\\img.vhdx")
        mocker.patch("pathlib.Path.exists", return_value=False)

        assert hypervisor.is_latest_image(mocker.Mock(), r"C:\\src")

    def test_get_vm_template_image_present_latest(self, hypervisor, mocker):
        disks = {"emu": {"free": "110013030400", "total": "254060523520"}}
        mocker.patch("mfd_hyperv.hypervisor.HypervHypervisor._get_disks_free_space", return_value=disks)
        hypervisor._connection.path.return_value = Path("dst\\img.vhdx")
        mocker.patch("pathlib.Path.exists", return_value=False)

        output = r"""
            emu\VM-Template\Base_R86.vhdx
            emu\VM-Template\Base_R92.vhdx
            emu\VM-Template\Base_W19.vhdx
            emu\VM-Template\Base_W22.vhdx
        """

        hypervisor._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout=output, stderr="stderr"
        )
        hypervisor._connection.path = Path

        mocker.patch("mfd_hyperv.hypervisor.HypervHypervisor.is_latest_image", return_value=True)
        mocker.patch("mfd_connect.util.rpc_copy_utils._check_paths")

        assert hypervisor.get_vm_template("Base_R86", r"C:\\src") == str(Path(r"emu/VM-Template/Base_R86.vhdx"))

    def test_get_vm_template_image_present_not_latest(self, hypervisor, mocker):
        disks = {"emu": {"free": "110013030400", "total": "254060523520"}}
        mocker.patch("mfd_hyperv.hypervisor.HypervHypervisor._get_disks_free_space", return_value=disks)
        hypervisor._connection.path.return_value = Path("dst\\img.vhdx")
        mocker.patch("pathlib.Path.exists", return_value=False)

        output = r"""
            emu\VM-Template\Base_R86.vhdx
            emu\VM-Template\Base_R92.vhdx
            emu\VM-Template\Base_W19.vhdx
            emu\VM-Template\Base_W22.vhdx
        """

        hypervisor._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout=output, stderr="stderr"
        )
        hypervisor._connection.path = Path

        mocker.patch("mfd_hyperv.hypervisor.HypervHypervisor.is_latest_image", return_value=False)
        mocker.patch("mfd_connect.util.rpc_copy_utils._check_paths")

        mocker.patch(
            "mfd_hyperv.hypervisor.HypervHypervisor.copy_vm_image",
            return_value=str(Path(r"emu/VM-Template/Base_R86.vhdx")),
        )

        assert hypervisor.get_vm_template("Base_R86", r"C:\\src") == str(Path(r"emu/VM-Template/Base_R86.vhdx"))

    def test_get_vm_template_image_not_present_need_copy(self, hypervisor, mocker):
        disks = {"D:\\": {"free": "110013030400", "total": "254060523520"}}
        mocker.patch("mfd_hyperv.hypervisor.HypervHypervisor._get_disks_free_space", return_value=disks)
        hypervisor._connection.path.return_value = Path("D:\\dst\\img.vhdx")
        mocker.patch("pathlib.Path.exists", return_value=False)

        output = """
            D:\\VM-Template\\Base_R86.vhdx
            D:\\VM-Template\\Base_R92.vhdx
            D:\\VM-Template\\Base_W19.vhdx
            D:\\VM-Template\\Base_W22.vhdx
        """

        hypervisor._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout=output, stderr="stderr"
        )
        hypervisor._connection.path = Path

        mocker.patch(
            "mfd_hyperv.hypervisor.HypervHypervisor.copy_vm_image", return_value="D:\\VM-Template\\Base_R99.vhdx"
        )

        assert hypervisor.get_vm_template("Base_R99", r"C:\\src") == "D:\\VM-Template\\Base_R99.vhdx"

    def test_create_differencing_disk(self, hypervisor, mocker):
        hypervisor._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout="output", stderr="stderr"
        )

        hypervisor._connection.path.return_value = Path("D:\\dst\\img.vhdx")
        mocker.patch("pathlib.Path.exists", return_value=True)

        hypervisor.create_differencing_disk(mocker.Mock(), "C:\\", "img,vhdx")

    def test_create_differencing_disk_failed(self, hypervisor, mocker):
        hypervisor._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout="output", stderr="stderr"
        )

        hypervisor._connection.path.return_value = Path("D:\\dst\\img.vhdx")
        mocker.patch("pathlib.Path.exists", return_value=False)

        with pytest.raises(HyperVException, match="Command execution succeed but disk doesn't exist "):
            hypervisor.create_differencing_disk(mocker.Mock(), "C:\\", "img,vhdx")

    def test_remove_differencing_disk(self, hypervisor):
        hypervisor._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout="output", stderr="stderr"
        )

        hypervisor.remove_differencing_disk("tst")

        hypervisor._connection.execute_powershell.assert_called_once_with(
            "Remove-Item tst", custom_exception=HyperVExecutionException
        )

    def test_get_hyperv_vm_ips(self, hypervisor, mocker):
        ip_data = """
            1.1.1.1
            1.1.1.1

            [hv]
            1.2.1.2
            1.2.1.3
            1.3.1.2
        """
        hypervisor._connection.path.return_value = Path("D:\\")
        mocker.patch("pathlib.Path.read_text", return_value=ip_data)
        hypervisor._connection._ip = "1.2.1.1"
        mocker.patch("mfd_hyperv.hypervisor.HypervHypervisor._get_mng_mask", return_value=16)

        expected_items = [IPAddress("1.2.1.2"), IPAddress("1.2.1.3")]
        assert hypervisor.get_hyperv_vm_ips(r"C:\\src\file.txt") == expected_items

    def test_get_mng_mask(self, hypervisor):
        output = """
            Ethernet adapter vEthernet (VSWITCH_02):

               Connection-specific DNS Suffix  . :
               Link-local IPv6 Address . . . . . : fdsfsfs
               IPv4 Address. . . . . . . . . . . : 1.112.1.1
               Subnet Mask . . . . . . . . . . . : 255.0.0.0
               Default Gateway . . . . . . . . . :

            Ethernet adapter vEthernet (managementvSwitch):

               Connection-specific DNS Suffix  . : www.com
               Link-local IPv6 Address . . . . . : fdsfsfs
               IPv4 Address. . . . . . . . . . . : 1.2.1.1
               Subnet Mask . . . . . . . . . . . : 255.255.0.0
               Default Gateway . . . . . . . . . : fdsf
        """

        hypervisor._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout=output, stderr="stderr"
        )

        hypervisor._connection._ip = "1.2.1.1"

        assert hypervisor._get_mng_mask() == 16

    def test_get_free_ips(self, hypervisor, mocker):
        mocker.patch("mfd_hyperv.hypervisor.TimeoutCounter", return_value=False)
        mocker.patch("mfd_hyperv.hypervisor.HypervHypervisor._vm_connectivity_test", return_value=False)

        expected_items = [IPAddress("1.2.1.2"), IPAddress("1.2.1.3")]
        result = hypervisor.get_free_ips(expected_items, 2)
        assert all([item in result for item in expected_items])

    def test_format_mac(self, hypervisor):
        data = [("1.1.1.1", "FF:FF:FF", "ff:ff:ff:01:01:01"), ("1.255.255.255", "FF:FF:FF", "ff:ff:ff:ff:ff:ff")]

        for ip, prefix, result in data:
            assert hypervisor.format_mac(ip, prefix) == result

    def test_wait_vm_mng_ips(self, hypervisor, mocker):
        mocker.patch("mfd_hyperv.hypervisor.time.sleep")
        mocker.patch("mfd_hyperv.hypervisor.TimeoutCounter", return_value=False)

        output_positive = """
            VMName      : Base_W19_VM001
            IPAddresses : {10.91.218.16, fe80::6994:9bd4:d0aa:ff4d}
            MacAddress  : 525A005BDA10
        """

        output_negative = """
            VMName      : Base_W19_VM001
            IPAddresses : {fe80::6994:9bd4:d0aa:ff4d}
            MacAddress  : 525A005BDA10
        """

        hypervisor._connection.execute_powershell.side_effect = [
            ConnectionCompletedProcess(return_code=0, args="command", stdout=output_negative, stderr="stderr"),
            ConnectionCompletedProcess(return_code=0, args="command", stdout=output_positive, stderr="stderr"),
        ]

        hypervisor._wait_vm_mng_ips("Base_R92_ps_VM001")

        assert hypervisor._connection.execute_powershell.call_count == 2

    def test_wait_vm_mng_ips_failed(self, hypervisor, mocker):
        mocker.patch("mfd_hyperv.hypervisor.TimeoutCounter", return_value=True)

        with pytest.raises(HyperVException, match="Problem with setting IP on mng adapter on one of VMs"):
            hypervisor._wait_vm_mng_ips("Base_R92_ps_VM001")

    def test_remove_folder_contents(self, hypervisor, mocker):
        hypervisor._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout="output", stderr="stderr"
        )
        dir_path = mocker.Mock()
        hypervisor._remove_folder_contents(dir_path)

        hypervisor._connection.execute_powershell.assert_called_once_with(
            "get-childitem -Recurse | remove-item -recurse -confirm:$false",
            cwd=dir_path,
        )

    def test_is_folder_empty(self, hypervisor, mocker):
        hypervisor._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout="output", stderr="stderr"
        )
        path = mocker.Mock()
        hypervisor._is_folder_empty(path)

        hypervisor._connection.execute_powershell.assert_called_once_with(
            "Get-ChildItem | select -ExpandProperty fullname", cwd=path, expected_return_codes={}
        )

    def testget_file_size(self, hypervisor, mocker):
        hypervisor._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout="213", stderr="stderr"
        )
        path = mocker.Mock()
        assert hypervisor.get_file_size(path) == 213

        hypervisor._connection.execute_powershell.assert_called_once_with(
            f"(Get-Item -Path {path}).Length", custom_exception=HyperVExecutionException
        )
