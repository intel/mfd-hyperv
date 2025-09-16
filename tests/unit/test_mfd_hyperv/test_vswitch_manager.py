# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Tests for `mfd_hyperv` vswitch manager submodule."""

from textwrap import dedent

import pytest
from mfd_connect import LocalConnection
from mfd_connect.base import ConnectionCompletedProcess
from mfd_typing import OSName

from mfd_hyperv.exceptions import HyperVExecutionException, HyperVException
from mfd_hyperv.instances.vswitch import VSwitch
from mfd_hyperv.vswitch_manager import VSwitchManager


class TestVswitchManager:
    @pytest.fixture()
    def vswitch_manager(self, mocker):
        conn = mocker.create_autospec(LocalConnection)
        conn.get_os_name.return_value = OSName.WINDOWS

        vswitch_manager = VSwitchManager(connection=conn)
        mocker.stopall()
        return vswitch_manager

    @pytest.fixture()
    def vswitch_manager_2_vswitches(self, mocker):
        conn = mocker.create_autospec(LocalConnection)
        conn.get_os_name.return_value = OSName.WINDOWS

        vswitch_manager = VSwitchManager(connection=conn)
        mocker.stopall()

        mocked1 = mocker.Mock()
        mocked2 = mocker.Mock()

        mocker.patch("mfd_hyperv.vswitch_manager.VSwitchManager.wait_vswitch_present", return_value=None)
        mocker.patch("mfd_hyperv.vswitch_manager.time.sleep")

        vswitch_manager.create_vswitch(["interface1"], "vs_name1", False, False, False, [mocked1])
        vswitch_manager.create_vswitch(["interface2"], "vs_name2", True, False, False, [mocked2])

        return vswitch_manager

    def test_create_vswitch_teaming_sriov(self, vswitch_manager, mocker):
        mocker.patch("mfd_hyperv.vswitch_manager.VSwitchManager._generate_name", return_value="final_name")
        cmd = (
            "powershell.exe \"New-VMSwitch -Name 'final_name' -NetAdapterName "
            "'interface1', 'interface2' -AllowManagementOS $true -EnableIov $True "
            '-EnableEmbeddedTeaming $true"'
        )

        mocker.patch("mfd_hyperv.vswitch_manager.VSwitchManager.wait_vswitch_present", return_value=None)
        mocker.patch("mfd_hyperv.vswitch_manager.time.sleep")
        mocked = mocker.Mock()

        vs = vswitch_manager.create_vswitch(["interface1", "interface2"], "vs_name", True, True, False, [mocked])
        tested = VSwitch("final_name", "'interface1', 'interface2'", True, True, vswitch_manager.connection, [mocked])

        vswitch_manager.connection.start_process.assert_called_once_with(cmd, shell=True)

        assert len(vswitch_manager.vswitches) == 1
        assert vs.__dict__ == tested.__dict__

    def test_create_vswitch_sriov(self, vswitch_manager, mocker):
        mocker.patch("mfd_hyperv.vswitch_manager.VSwitchManager._generate_name", return_value="final_name")
        cmd = (
            "powershell.exe \"New-VMSwitch -Name 'final_name' -NetAdapterName "
            "'interface' -AllowManagementOS $true -EnableIov $True\""
        )

        mocker.patch("mfd_hyperv.vswitch_manager.VSwitchManager.wait_vswitch_present", return_value=None)
        mocker.patch("mfd_hyperv.vswitch_manager.time.sleep")
        mocked = mocker.Mock()

        vs = vswitch_manager.create_vswitch(["interface"], "vs_name", True, False, False, [mocked])
        tested = VSwitch("final_name", "'interface'", True, False, vswitch_manager.connection, [mocked])

        vswitch_manager.connection.start_process.assert_called_once_with(cmd, shell=True)

        assert len(vswitch_manager.vswitches) == 1
        assert vs.__dict__ == tested.__dict__

    def test_create_vswitch(self, vswitch_manager, mocker):
        mocker.patch("mfd_hyperv.vswitch_manager.VSwitchManager._generate_name", return_value="final_name")
        cmd = (
            "powershell.exe \"New-VMSwitch -Name 'final_name' -NetAdapterName "
            "'interface' -AllowManagementOS $true -EnableIov $False\""
        )

        mocker.patch("mfd_hyperv.vswitch_manager.VSwitchManager.wait_vswitch_present", return_value=None)
        mocker.patch("mfd_hyperv.vswitch_manager.time.sleep")
        mocked = mocker.Mock()

        vs = vswitch_manager.create_vswitch(["interface"], "vs_name", False, False, False, [mocked])
        tested = VSwitch("final_name", "'interface'", False, False, vswitch_manager.connection, [mocked])

        vswitch_manager.connection.start_process.assert_called_once_with(cmd, shell=True)

        assert len(vswitch_manager.vswitches) == 1
        assert vs.__dict__ == tested.__dict__

    def test_create_vswitch_mng(self, vswitch_manager, mocker):
        mocker.patch("mfd_hyperv.vswitch_manager.VSwitchManager._generate_name", return_value="final_name")
        cmd = (
            "powershell.exe \"New-VMSwitch -Name 'vs_name' -NetAdapterName 'interface' "
            '-AllowManagementOS $true -EnableIov $False"'
        )

        mocker.patch("mfd_hyperv.vswitch_manager.VSwitchManager.wait_vswitch_present", return_value=None)
        mocker.patch("mfd_hyperv.vswitch_manager.time.sleep")
        mocked = mocker.Mock()

        vs = vswitch_manager.create_vswitch(["interface"], "vs_name", False, False, True, [mocked])
        tested = VSwitch("vs_name", "'interface'", False, False, vswitch_manager.connection, [mocked])

        vswitch_manager.connection.start_process.assert_called_once_with(cmd, shell=True)

        assert len(vswitch_manager.vswitches) == 0
        assert vs.__dict__ == tested.__dict__

    def test_remove_vswitch(self, vswitch_manager_2_vswitches, mocker):
        assert len(vswitch_manager_2_vswitches.vswitches) == 2

        vswitch_manager_2_vswitches.remove_vswitch("vs_name2_02")

        vswitch_manager_2_vswitches.connection.execute_powershell.assert_called_once_with(
            "Remove-VMSwitch vs_name2_02 -Force", custom_exception=HyperVExecutionException
        )

        assert len(vswitch_manager_2_vswitches.vswitches) == 1

    def test_generate_name(self, vswitch_manager):
        assert vswitch_manager._generate_name("aaa", True) == "aaa_01_T"
        assert vswitch_manager._generate_name("aaa", False) == "aaa_02"

    def test_generate_name_more(self, vswitch_manager_2_vswitches):
        assert vswitch_manager_2_vswitches._generate_name("aaa", True) == "aaa_03_T"
        assert vswitch_manager_2_vswitches._generate_name("aaa", False) == "aaa_04"

    def test_create_mng_vswitch_present(self, vswitch_manager, mocker):
        mocker.patch("mfd_hyperv.vswitch_manager.VSwitchManager.is_vswitch_present", return_value=True)
        vs = vswitch_manager.create_mng_vswitch()

        expected_vs = VSwitch(
            interface_name="managementvSwitch", host_adapter_names=[], connection=vswitch_manager.connection
        )

        assert vs.__dict__ == expected_vs.__dict__

    def test_create_mng_vswitch(self, vswitch_manager, mocker):
        mocker.patch("mfd_hyperv.vswitch_manager.VSwitchManager.is_vswitch_present", return_value=False)

        vswitch_manager.connection._ip = "ip_addr"
        vswitch_manager.connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout="iname", stderr="stderr"
        )

        mocker.patch("mfd_hyperv.vswitch_manager.VSwitchManager.wait_vswitch_present", return_value=None)
        mocker.patch("mfd_hyperv.vswitch_manager.time.sleep")

        vs = vswitch_manager.create_mng_vswitch()

        cmd = (
            "Get-NetIPAddress | Where-Object -Property IPAddress -EQ ip_addr | "
            "Where-Object -Property AddressFamily -EQ 'IPv4' | select -ExpandProperty InterfaceAlias"
        )
        vswitch_manager.connection.execute_powershell.assert_called_with(cmd, expected_return_codes={0})

        expected_vs = VSwitch("managementvSwitch", "'iname'", False, False, vswitch_manager.connection)

        assert vs.__dict__ == expected_vs.__dict__

    def test_get_vswitch_attributes(self, vswitch_manager, mocker):
        out = """
            Name                                             : managementvSwitch
            Id                                               : 98094e00-0df1-485b-875c-9a00d9af2f75
            Notes                                            :
            Extensions                                       : {Microsoft Windows Filtering Platform, Microsoft NDIS Capture}
            BandwidthReservationMode                         : Absolute
            PacketDirectEnabled                              : False
            EmbeddedTeamingEnabled                           : False
            AllowNetLbfoTeams                                : False
            IovEnabled                                       : False
            SwitchType                                       : External
            AllowManagementOS                                : True
            NetAdapterInterfaceDescription                   : Intel(R) Ethernet Controller X550
            NetAdapterInterfaceDescriptions                  : {Intel(R) Ethernet Controller X550}
            NetAdapterInterfaceGuid                          : {889a6b6b-9b94-48cc-929a-ed4b7ec5d3de}
            IovSupport                                       : True
            IovSupportReasons                                :
            AvailableIPSecSA                                 : 2048
            NumberIPSecSAAllocated                           : 0
            AvailableVMQueues                                : 31
            NumberVmqAllocated                               : 1
            IovQueuePairCount                                : 127
            IovQueuePairsInUse                               : 8
            IovVirtualFunctionCount                          : 0
            IovVirtualFunctionsInUse                         : 0
            PacketDirectInUse                                : False
            DefaultQueueVrssEnabledRequested                 : True
            DefaultQueueVrssEnabled                          : True
            DefaultQueueVmmqEnabledRequested                 : True
            DefaultQueueVmmqEnabled                          : True
            DefaultQueueVrssMaxQueuePairsRequested           : 16
            DefaultQueueVrssMaxQueuePairs                    : 4
            DefaultQueueVrssMinQueuePairsRequested           : 1
            DefaultQueueVrssMinQueuePairs                    : 1
            DefaultQueueVrssQueueSchedulingModeRequested     : StaticVrss
            DefaultQueueVrssQueueSchedulingMode              : StaticVrss
            DefaultQueueVrssExcludePrimaryProcessorRequested : False
            DefaultQueueVrssExcludePrimaryProcessor          : False
            SoftwareRscEnabled                               : True
            RscOffloadEnabled                                : False
            BandwidthPercentage                              : 10
            DefaultFlowMinimumBandwidthAbsolute              : 1000000000
            DefaultFlowMinimumBandwidthWeight                : 0
            CimSession                                       : CimSession: .
            ComputerName                                     : AMVAL-216-025
            IsDeleted                                        : False
            DefaultQueueVmmqQueuePairs                       : 4
            DefaultQueueVmmqQueuePairsRequested              : 16
        """  # noqa: E501

        vswitch_manager.connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout=out, stderr="stderr"
        )

        result = vswitch_manager.get_vswitch_attributes("managementvSwitch")

        vswitch_manager.connection.execute_powershell.assert_called_with(
            "Get-VMSwitch managementvSwitch | select * | fl", expected_return_codes={}
        )

        assert result["defaultqueuevmmqqueuepairsrequested"] == "16"
        assert result["iovsupportreasons"] == ""
        assert result["extensions"] == "{microsoft windows filtering platform, microsoft ndis capture}"

    def test_set_vswitch_attribute(self, vswitch_manager):
        vswitch_manager.set_vswitch_attribute("iname", "key", "value")

        vswitch_manager.connection.execute_powershell.assert_called_with(
            "Set-VMSwitch -Name iname -key value", custom_exception=HyperVExecutionException
        )

    def test_remove_tested_vswitches(self, vswitch_manager_2_vswitches):
        vswitch_manager_2_vswitches.remove_tested_vswitches()

        cmd = (
            "Get-VMSwitch | Where-Object {$_.Name -ne "
            '"managementvSwitch"'
            "} | Remove-VMSwitch -force -Confirm:$false"
        )
        vswitch_manager_2_vswitches.connection.execute_powershell.assert_called_with(
            cmd, custom_exception=HyperVExecutionException
        )

        assert len(vswitch_manager_2_vswitches.vswitches) == 0

    def test_is_vswitch_present(self, vswitch_manager):
        out = """
            managementvSwitch
        """

        vswitch_manager.connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout=out, stderr="stderr"
        )

        assert vswitch_manager.is_vswitch_present("managementvSwitch")

        assert not vswitch_manager.is_vswitch_present("aasdfd")

    def test_wait_vswitch_present(self, vswitch_manager, mocker):
        mocker.patch("mfd_hyperv.vswitch_manager.TimeoutCounter", return_value=False)
        mocker.patch("mfd_hyperv.vswitch_manager.VSwitchManager.is_vswitch_present", return_value=True)

        vswitch_manager.wait_vswitch_present("managementvSwitch")

    def test_wait_vswitch_present_failed(self, vswitch_manager, mocker):
        mocker.patch("mfd_hyperv.vswitch_manager.TimeoutCounter", return_value=True)

        with pytest.raises(HyperVException, match="Timeout expired. Cannot find vswitch managementvSwitch"):
            vswitch_manager.wait_vswitch_present("managementvSwitch")

    def test_rename_vswitch(self, vswitch_manager, mocker):
        attrs = {"name": "vswitch_new_name"}
        mocker.patch("mfd_hyperv.vswitch_manager.VSwitchManager.get_vswitch_attributes", return_value=attrs)
        vswitch_manager.rename_vswitch("vs_01", "vswitch_new_name")

        cmd = 'Rename-VMSwitch "vs_01" -NewName "vswitch_new_name"'
        vswitch_manager.connection.execute_powershell.assert_called_with(cmd, custom_exception=HyperVExecutionException)

    def test_get_vswitch_mapping_one_vswitch_found(self, vswitch_manager):
        out = dedent(
            """
        Name                                             : managementvSwitch
        Id                                               : bbaaa964-2ff4-4904-b4da-121a937c6041
        Notes                                            : 
        Extensions                                       : {Microsoft Windows Filtering Platform, Microsoft NDIS Capture}
        BandwidthReservationMode                         : Absolute
        PacketDirectEnabled                              : False
        EmbeddedTeamingEnabled                           : False
        AllowNetLbfoTeams                                : False
        IovEnabled                                       : False
        SwitchType                                       : External
        AllowManagementOS                                : True
        NetAdapterInterfaceDescription                   : Intel(R) Ethernet Controller X550
        NetAdapterInterfaceDescriptions                  : {Intel(R) Ethernet Controller X550}
        NetAdapterInterfaceGuid                          : {bd4d0811-a156-4cb3-9381-a899064196df}
        IovSupport                                       : True
        IovSupportReasons                                : 
        AvailableIPSecSA                                 : 2048
        NumberIPSecSAAllocated                           : 0
        AvailableVMQueues                                : 31
        NumberVmqAllocated                               : 1
        IovQueuePairCount                                : 127
        IovQueuePairsInUse                               : 8
        IovVirtualFunctionCount                          : 0
        IovVirtualFunctionsInUse                         : 0
        PacketDirectInUse                                : False
        DefaultQueueVrssEnabledRequested                 : True
        DefaultQueueVrssEnabled                          : True
        DefaultQueueVmmqEnabledRequested                 : True
        DefaultQueueVmmqEnabled                          : True
        DefaultQueueVrssMaxQueuePairsRequested           : 16
        DefaultQueueVrssMaxQueuePairs                    : 4
        DefaultQueueVrssMinQueuePairsRequested           : 1
        DefaultQueueVrssMinQueuePairs                    : 1
        DefaultQueueVrssQueueSchedulingModeRequested     : StaticVrss
        DefaultQueueVrssQueueSchedulingMode              : StaticVrss
        DefaultQueueVrssExcludePrimaryProcessorRequested : False
        DefaultQueueVrssExcludePrimaryProcessor          : False
        SoftwareRscEnabled                               : True
        RscOffloadEnabled                                : False
        BandwidthPercentage                              : 10
        DefaultFlowMinimumBandwidthAbsolute              : 1000000000
        DefaultFlowMinimumBandwidthWeight                : 0
        CimSession                                       : CimSession: .
        ComputerName                                     : JASON-55-013
        IsDeleted                                        : False
        DefaultQueueVmmqQueuePairs                       : 4
        DefaultQueueVmmqQueuePairsRequested              : 16
        """  # noqa: E501, W605, W291
        )
        vswitch_manager.connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout=out, stderr=""
        )
        assert {"managementvSwitch": "Intel(R) Ethernet Controller X550"} == vswitch_manager.get_vswitch_mapping()

    def test_get_vswitch_mapping_no_vswitches(self, vswitch_manager):
        vswitch_manager.connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout="", stderr=""
        )
        assert {} == vswitch_manager.get_vswitch_mapping()

    def test_get_vswitch_mapping_error(self, vswitch_manager):
        vswitch_manager.connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=1, args="command", stdout="", stderr=""
        )
        assert {} == vswitch_manager.get_vswitch_mapping()
