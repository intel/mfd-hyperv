# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Main module."""

import logging
import re

from typing import TYPE_CHECKING
from mfd_common_libs import log_levels, add_logging_level

from mfd_hyperv.exceptions import HyperVExecutionException, HyperVException

if TYPE_CHECKING:
    from mfd_connect import Connection

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class HWQoS:
    """Class for Hyper-V Hardware QoS Offload functionality."""

    def __init__(self, connection: "Connection") -> None:
        """
        Class constructor.

        :param connection: connection instance.
        """
        self._connection = connection

    def create_scheduler_queue(
        self, vswitch_name: str, sq_id: str, sq_name: str, limit: bool, tx_max: str, tx_reserve: str, rx_max: str
    ) -> None:
        """
        Create scheduler queue.

        :param vswitch_name: name of the virtual switch.
        :param sq_id: ID for new scheduler queue.
        :param sq_name: name for new scheduler queue.
        :param limit: determine if enforcing infra-host limits.
        :param tx_max: transmit limit.
        :param tx_reserve: transmit reservation.
        :param rx_max: receive limit.
        :raises HyperVExecutionException: when command execution fails.
        """
        limit = str(limit).lower()
        cmd = (
            f"vfpctrl /switch {vswitch_name} /add-queue " f'"{sq_id} {sq_name} {limit} {tx_max} {tx_reserve} {rx_max}"'
        )
        self._connection.execute_powershell(command=cmd, custom_exception=HyperVExecutionException)

    def update_scheduler_queue(
        self, vswitch_name: str, limit: bool, tx_max: str, tx_reserve: str, rx_max: str, sq_id: str
    ) -> None:
        """
        Update existing scheduler queue.

        :param vswitch_name: name of the virtual switch.
        :param limit: determine if enforcing infra-host limits.
        :param tx_max: queue configuration value which determines transmit limit.
        :param tx_reserve: transmit reservation.
        :param rx_max: receive limit.
        :param sq_id: ID of existing scheduler queue.
        :raises HyperVExecutionException: when command execution fails.
        """
        limit = str(limit).lower()
        cmd = (
            f"vfpctrl /switch {vswitch_name} /set-queue-config "
            f'"{limit} {tx_max} {tx_reserve} {rx_max}" /queue "{sq_id}"'
        )
        self._connection.execute_powershell(command=cmd, custom_exception=HyperVExecutionException)

    def delete_scheduler_queue(self, vswitch_name: str, sq_id: str) -> None:
        """
        Delete existing scheduler queue.

        :param vswitch_name: name of the virtual switch.
        :param sq_id: ID of existing scheduler queue.
        :raises HyperVExecutionException: when command execution fails.
        """
        cmd = f'vfpctrl /switch {vswitch_name} /remove-queue /queue "{sq_id}"'
        self._connection.execute_powershell(command=cmd, custom_exception=HyperVExecutionException)

    def get_qos_config(self, vswitch_name: str) -> dict[str, str | bool]:
        """
        Get current QoS configuration for the vSwitch.

        :param vswitch_name: name of the virtual switch.
        :return: config from parsed command output, for example:
        {'hw_caps': False, 'hw_reserv': False, 'sw_reserv': True, flags: 0x0}
        :raises HyperVExecutionException: when command execution fails.
        """
        cmd = f"vfpctrl /switch {vswitch_name} /get-qos-config"
        result = self._connection.execute_powershell(command=cmd, custom_exception=HyperVExecutionException)

        pattern = (
            r"Caps:+\s(?P<hw_caps>\S+)[\s\S]*?"
            r"Hardware Reservations:+\s(?P<hw_reserv>\S+)[\s\S]*?"
            r"Software Reservations:+\s(?P<sw_reserv>\S+)[\s\S]*?"
            r"Flags:+\s(?P<flags>\S+)"
        )
        parsed_config = {}
        matches = re.finditer(pattern, result.stdout)
        params = ["hw_caps", "hw_reserv", "sw_reserv", "flags"]

        for match in matches:
            for param in params:
                if param == "flags":
                    parsed_config[param] = match.group(param)
                else:
                    parsed_config[param] = True if match.group(param) == "TRUE" else False

        return parsed_config

    def set_qos_config(self, vswitch_name: str, hw_caps: bool, hw_reserv: bool, sw_reserv: bool, flags: str) -> None:
        """
        Set QoS configuration on the vSwitch.

        :param vswitch_name: name of the virtual switch.
        :param hw_caps: determine if enable hardware caps.
        :param hw_reserv: determine if enable hardware reservations.
        :param sw_reserv: determine if enable software reservations.
        :param flags: flags.
        :raises HyperVExecutionException: when command execution fails.
        """
        hw_caps = str(hw_caps).lower()
        hw_reserv = str(hw_reserv).lower()
        sw_reserv = str(sw_reserv).lower()
        cmd = f'vfpctrl /switch {vswitch_name} /set-qos-config "{hw_caps} {hw_reserv} {sw_reserv} {flags}"'
        self._connection.execute_powershell(command=cmd, custom_exception=HyperVExecutionException)

    def disassociate_scheduler_queues_with_vport(self, vswitch_name: str, vport: str) -> None:
        """
        Disassociate scheduler queues with virtual port.

        :param vswitch_name: name of the virtual switch.
        :param vport: virtual port.
        :raises HyperVExecutionException: when command execution fails.
        """
        cmd = f"vfpctrl /switch {vswitch_name} /port {vport} /clear-port-queue"
        self._connection.execute_powershell(command=cmd, custom_exception=HyperVExecutionException)

    def list_scheduler_queues_with_vport(self, vswitch_name: str, vport: str) -> list[str]:
        """
        List scheduler queues associated with virtual port.

        :param vswitch_name: name of the virtual switch.
        :param vport: virtual port.
        :return: list of SQ IDs associated with given port, eg. ["1", "5", "2"]
        :raises HyperVExecutionException: when command execution fails.
        """
        cmd = f"vfpctrl /switch {vswitch_name} /port {vport} /get-port-queue"
        result = self._connection.execute_powershell(command=cmd, custom_exception=HyperVExecutionException)
        pattern = r"(?<=QOS QUEUE: ).*"
        return re.findall(pattern, result.stdout)

    def associate_scheduler_queues_with_vport(
        self, vswitch_name: str, vport: str, sq_id: str, lid: int, lname: str
    ) -> None:
        """
        Associate scheduler queues with virtual port.

        :param vswitch_name: name of the virtual switch.
        :param vport: virtual port.
        :param sq_id: ID of existing scheduler queue.
        :param lid: layer ID
        :param lname: layer name
        :raises HyperVExecutionException: when any command execution fails.
        """
        base_cmd = f"vfpctrl /switch {vswitch_name} /port {vport}"
        params = [
            "/enable-port",
            "/unblock-port",
            f"/add-layer '{lid} {lname} stateless 100 1'",
            f"/set-port-queue {sq_id}",
        ]
        for param in params:
            cmd = f"{base_cmd} {param}"
            self._connection.execute_powershell(command=cmd, custom_exception=HyperVExecutionException)

    def get_vmswitch_port_name(self, switch_friendly_name: str, vm_name: str) -> str:
        """
        Get vmswitch port name.

        :param switch_friendly_name: switch friendly name.
        :param vm_name: vm name.
        :return: vmswitch port name.
        :raises HyperVExecutionException: when command execution fails.
        :raises HyperVException: when no vmswitch port name found.
        """
        cmd = "vfpctrl /list-vmswitch-port"

        result = self._connection.execute_powershell(command=cmd, custom_exception=HyperVExecutionException)

        pattern = (
            r"Port\sname\s+:+\s(?P<port_name>\S+)[\s\S]*?"
            r"Switch\sFriendly\sname\s+:+\s(?P<friendly_name>\S+)[\s\S]*?"
            r"VM\sname\s+:+\s(?P<vm_name>\S+)"
        )

        matches = re.finditer(pattern, result.stdout)

        for match in matches:
            if match.group("friendly_name") == switch_friendly_name and match.group("vm_name") == vm_name:
                return match.group("port_name")

        raise HyperVException(
            f"Couldn't find VM Switch port name for Switch Friendly name: {switch_friendly_name} and "
            f"VM name: {vm_name} in output: {result.stdout}"
        )

    def is_scheduler_queues_created(self, vswitch_name: str, sq_id: int, sq_name: str, tx_max: str) -> bool:
        """
        Verify that scheduler queues with provided name was created.

        :param vswitch_name: name of vswitch.
        :param sq_id: scheduler queues for verification.
        :param sq_name: name of scheduler queues.
        :param tx_max: transmit limit value
        :return: True if SQ found, False otherwise.
        :raises HyperVExecutionException: when command execution fails.
        """
        pattern = (
            r"(?<=QOS QUEUE: )(?P<sq_id>.*)\s+"
            r"Friendly\sname\s+:+\s(?P<friendly_name>\S+)[\s\S]*?\s+.+"
            r"Transmit\sLimit:+\s(?P<tx_max>\S+)"
        )

        listed_queue = self.list_queue(vswitch_name=vswitch_name)
        all_info = self.get_queue_all_info(vswitch_name=vswitch_name)
        offload_info = self.get_queue_offload_info(vswitch_name=vswitch_name, sq_id=sq_id)

        for result in [listed_queue, all_info, offload_info]:
            matches = re.finditer(pattern, result)
            for match in matches:
                if (
                    match.group("friendly_name") == sq_name
                    and match.group("sq_id") == str(sq_id)
                    and match.group("tx_max") == str(tx_max)
                ):
                    is_scheduler_queues_created = True
                    break
            else:
                is_scheduler_queues_created = False

        return is_scheduler_queues_created

    def list_queue(self, vswitch_name: str) -> str:
        """
        List quested scheduler queues on a vswitch.

        :param vswitch_name: name of vswitch.
        :return: output from command.
        :raises HyperVExecutionException: when command execution fails.
        """
        cmd = f"vfpctrl /switch {vswitch_name} /list-queue"
        return self._connection.execute_powershell(command=cmd, custom_exception=HyperVExecutionException).stdout

    def get_queue_all_info(self, vswitch_name: str) -> str:
        """
        List quested scheduler queues on a vswitch.

        :param vswitch_name: name of vswitch.
        :return: output from command.
        :raises HyperVExecutionException: when command execution fails.
        """
        cmd = f'vfpctrl /switch {vswitch_name} /get-queue-info "all"'

        return self._connection.execute_powershell(command=cmd, custom_exception=HyperVExecutionException).stdout

    def get_queue_offload_info(self, vswitch_name: str, sq_id: int) -> str:
        """
        List quested scheduler queues on a vswitch.

        :param vswitch_name: name of vswitch.
        :param sq_id: number of scheduler queues.
        :return: output from command.
        :raises HyperVExecutionException: when command execution fails.
        """
        cmd = f'vfpctrl /switch {vswitch_name} /get-queue-info "offload" /queue "{sq_id}"'

        return self._connection.execute_powershell(command=cmd, custom_exception=HyperVExecutionException).stdout
