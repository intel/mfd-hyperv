# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Tests for `hw_qos` package."""

from textwrap import dedent

import pytest

from mfd_connect import LocalConnection
from mfd_connect.base import ConnectionCompletedProcess
from mfd_typing import OSName

from mfd_hyperv.hw_qos import HWQoS
from mfd_hyperv.exceptions import HyperVExecutionException, HyperVException
from tests.unit.test_mfd_hyperv.const import out_list_queue, out_queue_offload, out_get_all_info


class TestMfdHypervHWQos:
    @pytest.fixture()
    def hyperv_qos(self, mocker):
        conn = mocker.create_autospec(LocalConnection)
        conn.get_os_name.return_value = OSName.WINDOWS

        hyperv = HWQoS(connection=conn)
        mocker.stopall()
        return hyperv

    def test_create_scheduler_queue(self, hyperv_qos):
        hyperv_qos._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout="", stderr="stderr"
        )
        hyperv_qos.create_scheduler_queue(
            vswitch_name="sw0", limit=True, tx_max="500", tx_reserve="0", rx_max="0", sq_id="5", sq_name="SQ1"
        )
        hyperv_qos._connection.execute_powershell.assert_called_once_with(
            'vfpctrl /switch sw0 /add-queue "5 SQ1 true 500 0 0"',
            custom_exception=HyperVExecutionException,
        )

    def test_update_scheduler_queue(self, hyperv_qos):
        hyperv_qos._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout="", stderr="stderr"
        )
        hyperv_qos.update_scheduler_queue(
            vswitch_name="sw0", limit=True, tx_max="500", tx_reserve="0", rx_max="0", sq_id="5"
        )
        hyperv_qos._connection.execute_powershell.assert_called_once_with(
            'vfpctrl /switch sw0 /set-queue-config "true 500 0 0" /queue "5"',
            custom_exception=HyperVExecutionException,
        )

    def test_delete_scheduler_queue(self, hyperv_qos):
        hyperv_qos._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout="", stderr="stderr"
        )
        hyperv_qos.delete_scheduler_queue(vswitch_name="sw0", sq_id="5")
        hyperv_qos._connection.execute_powershell.assert_called_once_with(
            'vfpctrl /switch sw0 /remove-queue /queue "5"', custom_exception=HyperVExecutionException
        )

    def test_get_qos_config(self, hyperv_qos):
        hyperv_qos._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout="", stderr="stderr"
        )
        hyperv_qos.get_qos_config(vswitch_name="sw0")
        hyperv_qos._connection.execute_powershell.assert_called_once_with(
            "vfpctrl /switch sw0 /get-qos-config", custom_exception=HyperVExecutionException
        )

    def test_get_qos_config_parse_output(self, hyperv_qos):
        command_output = """
         ITEM LIST
        ===========

        SWITCH QOS CONFIG
        Enable Hardware Caps: FALSE
        Enable Hardware Reservations: FALSE
        Enable Software Reservations: TRUE
        Flags: 0x00
        Command get-qos-config succeeded!
        """
        expected_result = {"hw_caps": False, "hw_reserv": False, "sw_reserv": True, "flags": "0x00"}
        hyperv_qos._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout=command_output, stderr="stderr"
        )
        assert hyperv_qos.get_qos_config(vswitch_name="sw0") == expected_result

    def test_set_qos_config(self, hyperv_qos):
        hyperv_qos._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout="", stderr="stderr"
        )
        hyperv_qos.set_qos_config(vswitch_name="sw0", hw_caps=False, hw_reserv=True, sw_reserv=True, flags="0")
        hyperv_qos._connection.execute_powershell.assert_called_once_with(
            'vfpctrl /switch sw0 /set-qos-config "false true true 0"',
            custom_exception=HyperVExecutionException,
        )

    def test_disassociate_scheduler_queues_with_vport(self, hyperv_qos):
        hyperv_qos._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout="", stderr="stderr"
        )
        hyperv_qos.disassociate_scheduler_queues_with_vport(
            vswitch_name="sw0", vport="AF4F56A0-802D-4629-88D4-7ECBDB019AE3"
        )
        hyperv_qos._connection.execute_powershell.assert_called_once_with(
            "vfpctrl /switch sw0 /port AF4F56A0-802D-4629-88D4-7ECBDB019AE3 /clear-port-queue",
            custom_exception=HyperVExecutionException,
        )

    def test_list_scheduler_queues_with_vport(self, hyperv_qos):
        hyperv_qos._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout="", stderr="stderr"
        )
        hyperv_qos.list_scheduler_queues_with_vport(vswitch_name="sw0", vport="AF4F56A0-802D-4629-88D4-7ECBDB019AE3")
        hyperv_qos._connection.execute_powershell.assert_called_once_with(
            "vfpctrl /switch sw0 /port AF4F56A0-802D-4629-88D4-7ECBDB019AE3 /get-port-queue",
            custom_exception=HyperVExecutionException,
        )

    def test_list_scheduler_queues_with_vport_parse_output(self, hyperv_qos):
        command_output = """
         ITEM LIST
        ===========


    QOS QUEUE: 2
      Friendly name : SQ1
      Enforce intra-host limit: TRUE
      Transmit Limit: 1000
      Transmit Reservation: 0
      Receive Limit: 0
      Transmit Queue Depth: 200 packets
      Receive Queue Depth: 50 packets
      Transmit Burst Size: 50 ms
      Receive Burst Size: 50 ms
      Reservation UnderUtilized watermark: 85%
      Reservation OverUtilized watermark: 95%
      Reservation Headroom: 10%
      Reservation Rampup time: 500 ms
      Reservation Min rate: 10 Mbps

      Current Transmit Info:
        Rate: 1000
        Throttled Packets: 0
        Dropped Packets: 0
      Current Receive Info:
        Rate: DISABLED
        Throttled Packets: 0
        Dropped Packets: 0

    QOS QUEUE: 4
      Friendly name : SQ1
      Enforce intra-host limit: TRUE
      Transmit Limit: 1000
      Transmit Reservation: 0
      Receive Limit: 0
      Transmit Queue Depth: 200 packets
      Receive Queue Depth: 50 packets
      Transmit Burst Size: 50 ms
      Receive Burst Size: 50 ms
      Reservation UnderUtilized watermark: 85%
      Reservation OverUtilized watermark: 95%
      Reservation Headroom: 10%
      Reservation Rampup time: 500 ms
      Reservation Min rate: 10 Mbps

      Current Transmit Info:
        Rate: 1000
        Throttled Packets: 0
        Dropped Packets: 0
      Current Receive Info:
        Rate: DISABLED
        Throttled Packets: 0
        Dropped Packets: 0


  Port: AF4F56A0-802D-4629-88D4-7ECBDB019AE3
    Friendly Name: vSwitch000_External
    ID: 1
Command get-port-queue succeeded!
        """
        expected_result = ["2", "4"]
        hyperv_qos._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout=command_output, stderr="stderr"
        )
        assert (
            hyperv_qos.list_scheduler_queues_with_vport(
                vswitch_name="sw0", vport="AF4F56A0-802D-4629-88D4-7ECBDB019AE3"
            )
            == expected_result
        )

    def test_associate_scheduler_queues_with_vport(self, hyperv_qos, mocker):
        hyperv_qos._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout="", stderr="stderr"
        )
        hyperv_qos.associate_scheduler_queues_with_vport(
            vswitch_name="sw0", vport="AF4F56A0-802D-4629-88D4-7ECBDB019AE3", sq_id="5", lid=1, lname="layer1"
        )
        expected_cmds = [
            "vfpctrl /switch sw0 /port AF4F56A0-802D-4629-88D4-7ECBDB019AE3 /enable-port",
            "vfpctrl /switch sw0 /port AF4F56A0-802D-4629-88D4-7ECBDB019AE3 /unblock-port",
            "vfpctrl /switch sw0 /port AF4F56A0-802D-4629-88D4-7ECBDB019AE3 " "/add-layer '1 layer1 stateless 100 1'",
            "vfpctrl /switch sw0 /port AF4F56A0-802D-4629-88D4-7ECBDB019AE3 /set-port-queue 5",
        ]
        calls = [mocker.call(command=call, custom_exception=HyperVExecutionException) for call in expected_cmds]
        hyperv_qos._connection.execute_powershell.assert_has_calls(calls)

    def test_get_vmswitch_port_name_no_match(self, hyperv_qos):
        hyperv_qos._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout="", stderr="stderr"
        )
        with pytest.raises(
            HyperVException,
            match="Couldn't find VM Switch port name for Switch Friendly name: "
            "vSwitch00 and VM name: vm00-2019 in output: ",
        ):
            hyperv_qos.get_vmswitch_port_name("vSwitch00", "vm00-2019")

    def test_get_vmswitch_port_name(self, hyperv_qos):
        output = dedent(
            """\
        Port name             : 924950C2-4D3F-47E2-A7BA-C0E322C51C66
        Port Friendly name    : Dynamic Ethernet Switch Port
        Switch name           : 5D81E4BB-3056-4BA3-A7A5-469AEAFB366D
        Switch Friendly name  : vSwitch00
        PortId                : 3
        VMQ Weight            : 100
        VMQ Usage             : 1
        SR-IOV Weight         : 0
        SR-IOV Usage          : 0
        Port type:            : Synthetic
         Port is Initialized.
         MAC Learning is Disabled.
        NIC name           : FFAAQQ66-AA1234-7890-F342-7894AD45ER12--33E0CC89-3DB0-4A5A-7845-123456789ABC
        NIC Friendly name  : Network Adapter
        MTU                : 1500
        MAC address        : AA-BB-CC-DD-EE-FF
        VM name            : vm00-2019
        VM ID              : 11223344-1122-4455-6655-ABCDEF123456
            """
        )
        hyperv_qos._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout=output, stderr="stderr"
        )
        assert hyperv_qos.get_vmswitch_port_name("vSwitch00", "vm00-2019") == "924950C2-4D3F-47E2-A7BA-C0E322C51C66"

    def test_get_vmswitch_port_name_multiple_vm(self, hyperv_qos):
        output = dedent(
            """\
        Port name             : 88888888-4D3F-47E2-A7BA-000000000000
        Port Friendly name    : Dynamic Ethernet Switch Port
        Switch name           : 5D81E4BB-3056-4BA3-A7A5-469AEAFB366D
        Switch Friendly name  : vSwitch01
        PortId                : 3
        VMQ Weight            : 100
        VMQ Usage             : 1
        SR-IOV Weight         : 0
        SR-IOV Usage          : 0
        Port type:            : Synthetic
         Port is Initialized.
         MAC Learning is Disabled.
        NIC name           : FFAAQQ66-AA1234-7890-F342-7894AD45ER12--33E0CC89-3DB0-4A5A-7845-123456789ABC
        NIC Friendly name  : Network Adapter
        MTU                : 1500
        MAC address        : AA-BB-CC-DD-EE-FF
        VM name            : vm01-2019
        VM ID              : 11223344-1122-4455-6655-ABCDEF123456
        Port name             : 924950C2-4D3F-47E2-A7BA-C0E322C51C66
        Port Friendly name    : Dynamic Ethernet Switch Port
        Switch name           : 5D81E4BB-3056-4BA3-A7A5-469AEAFB366D
        Switch Friendly name  : vSwitch00
        PortId                : 3
        VMQ Weight            : 100
        VMQ Usage             : 1
        SR-IOV Weight         : 0
        SR-IOV Usage          : 0
        Port type:            : Synthetic
         Port is Initialized.
         MAC Learning is Disabled.
        NIC name           : FFAAQQ66-AA1234-7890-F342-7894AD45ER12--33E0CC89-3DB0-4A5A-7845-123456789ABC
        NIC Friendly name  : Network Adapter
        MTU                : 1500
        MAC address        : AA-BB-CC-DD-EE-FF
        VM name            : vm00-2019
        VM ID              : 11223344-1122-4455-6655-ABCDEF123456
            """
        )
        hyperv_qos._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout=output, stderr="stderr"
        )
        assert hyperv_qos.get_vmswitch_port_name("vSwitch00", "vm00-2019") == "924950C2-4D3F-47E2-A7BA-C0E322C51C66"

    def test_is_scheduler_queues_created_true(self, mocker, hyperv_qos):
        hyperv_qos.list_queue = mocker.Mock(return_value=out_list_queue)
        hyperv_qos.get_queue_all_info = mocker.Mock(return_value=out_get_all_info)
        hyperv_qos.get_queue_offload_info = mocker.Mock(return_value=out_queue_offload)
        out = hyperv_qos.is_scheduler_queues_created(
            vswitch_name="sample_vswitch", sq_id=2, sq_name="SQ2", tx_max="10000"
        )
        assert out

    def test_is_scheduler_queues_created_false(self, mocker, hyperv_qos):
        hyperv_qos.list_queue = mocker.Mock(return_value="output")
        hyperv_qos.get_queue_all_info = mocker.Mock(return_value="out_get_all_info")
        hyperv_qos.get_queue_offload_info = mocker.Mock(return_value="offload_result")
        out = hyperv_qos.is_scheduler_queues_created(
            vswitch_name="sample_vswitch", sq_id=2, sq_name="SQ2", tx_max="10000"
        )
        assert not out

    def test_list_queue(self, hyperv_qos):
        expected_output = "list queue output"
        hyperv_qos._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout=expected_output, stderr="stderr"
        )
        result = hyperv_qos.list_queue(vswitch_name="sw0")
        assert result == expected_output
        hyperv_qos._connection.execute_powershell.assert_called_once_with(
            "vfpctrl /switch sw0 /list-queue", custom_exception=HyperVExecutionException
        )

    def test_get_queue_all_info(self, hyperv_qos):
        expected_output = "get all queue info output"
        hyperv_qos._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout=expected_output, stderr="stderr"
        )
        result = hyperv_qos.get_queue_all_info(vswitch_name="sw0")
        assert result == expected_output
        hyperv_qos._connection.execute_powershell.assert_called_once_with(
            'vfpctrl /switch sw0 /get-queue-info "all"', custom_exception=HyperVExecutionException
        )

    def test_get_queue_offload_info(self, hyperv_qos):
        expected_output = "get queue offload info output"
        hyperv_qos._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout=expected_output, stderr="stderr"
        )
        result = hyperv_qos.get_queue_offload_info(vswitch_name="sw0", sq_id=2)
        assert result == expected_output
        hyperv_qos._connection.execute_powershell.assert_called_once_with(
            'vfpctrl /switch sw0 /get-queue-info "offload" /queue "2"', custom_exception=HyperVExecutionException
        )
