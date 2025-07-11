# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Hyper-V hypervisor.

Contents:
-VMParams
    dataclass for parameters required for Virtual Machine creation

-VMProcessorAttributes
    enum class with set of most used setting names of VMProcessor

-VM
    representation of single Hyper-V Virtual Machine (guest) which manages operations executed on the guest

-HypervHypervisor
    representation of Hypervisor containing API for Powershell cmdlets that manage Virtual Machines on the Host
"""

import logging
import random
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Union, List, Optional, TYPE_CHECKING

from mfd_common_libs import os_supported, add_logging_level, log_levels, TimeoutCounter
from mfd_connect import Connection, RPyCConnection
from mfd_connect.util.powershell_utils import parse_powershell_list
from mfd_connect.util.rpc_copy_utils import copy
from mfd_network_adapter import NetworkAdapterOwner
from mfd_ping import Ping
from mfd_typing import OSName
from netaddr.ip import IPAddress, IPNetwork

from mfd_hyperv.attributes.vm_params import VMParams
from mfd_hyperv.attributes.vm_processor_attributes import VMProcessorAttributes
from mfd_hyperv.exceptions import HyperVExecutionException, HyperVException
from mfd_hyperv.helpers import standardise_value
from mfd_hyperv.instances.vm_network_interface import VM

if TYPE_CHECKING:
    from mfd_hyperv import HyperV


logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class HypervHypervisor:
    """Module for HyperV."""

    @os_supported(OSName.WINDOWS)
    def __init__(self, *, connection: "Connection"):
        """Class constructor.

        :param connection: connection instance of MFD connect class.
        """
        self._connection = connection
        self.vms = []

    def is_hyperv_enabled(self) -> bool:
        """Check if Hyper-V is enabled.

        :raises: HyperVException when Hyper-V is unavailable
        :return: True if enabled, False otherwise
        """
        status_correlation = {"Enabled": True, "Disabled": False}
        result = self._connection.execute_powershell(
            "Get-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V", expected_return_codes={}
        )
        if result.return_code:
            raise HyperVException("Hyper-V status unavailable")

        status_regex = r"State\s+:\s+(?P<status>(Disabled|Enabled))"
        match = re.search(status_regex, result.stdout)
        if match:
            logger.log(level=log_levels.MODULE_DEBUG, msg=f"Hyper-V status: {match.group('status')}")
            return status_correlation[match.group("status")]
        raise HyperVException("Hyper-V status unavailable")

    def create_vm(
        self,
        vm_params: VMParams,
        owner: Optional[NetworkAdapterOwner] = None,
        hyperv: "HyperV" = None,
        connection_timeout: int = 3600,
        dynamic_mng_ip: bool = False,
    ) -> VM:
        """Create a new VM using the specified vm_params.

        :param vm_params: dictionary of VM parameters
        :param owner: SUT host that will host new Vm
        :param hyperv: Hyperv object that will be used by Vm instance
        :param connection_timeout: timeout of RPyCConnection to VM
        :param dynamic_mng_ip: To enable or disable dynamic mng ip allocation
        """
        commands = [
            f'New-VM "{vm_params.name}" -Generation {vm_params.generation} -Path {vm_params.vm_dir_path}',
            f'Add-VMHardDiskDrive -VMName "{vm_params.name}" -Path {vm_params.diff_disk_path}',
            f"Set-VMProcessor -VMName {vm_params.name} -Count {vm_params.cpu_count}",
            f"Set-VMMemory -VMName {vm_params.name} -StartupBytes {vm_params.memory}MB",
            f"Remove-VMNetworkAdapter -VMName {vm_params.name} -Name *Adapter*",
            f"Add-VMNetworkAdapter -VMName '{vm_params.name}' -Name '{vm_params.mng_interface_name}'"
            f" -StaticMacAddress {str(vm_params.mng_mac_address).replace(':', '')}"
            f" -SwitchName '{vm_params.vswitch_name}'",
            f'Set-VMNetworkAdapter -Name "{vm_params.mng_interface_name}" -VMName "{vm_params.name}" -VmqWeight 0',
            f'Set-VMFirmware -EnableSecureBoot Off -VMName "{vm_params.name}"',
            f'Enable-VMIntegrationService -VMName "{vm_params.name}" -Name "Guest Service Interface"',
        ]

        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Create VM {vm_params.name}")
        for command in commands:
            self._connection.execute_powershell(command=command, custom_exception=HyperVExecutionException)

        self.start_vm(vm_params.name)
        mng_ip = self._wait_vm_mng_ips(vm_params.name)
        if dynamic_mng_ip:
            vm_params.mng_ip = mng_ip

        vm_connection = RPyCConnection(ip=vm_params.mng_ip, connection_timeout=connection_timeout)
        vm = VM(vm_connection, vm_params, owner, hyperv, connection_timeout)

        self.vms.append(vm)
        return vm

    def remove_vm(self, vm_name: str = "*") -> None:
        """Remove specified VM or all VMs.

        :param vm_name: Virtual Machine name
        """
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Removing {vm_name if vm_name != '*' else 'all'} VM")
        self._connection.execute_powershell(
            f"Remove-VM -name {vm_name} -force -Confirm:$false", custom_exception=HyperVExecutionException
        )
        if vm_name == "*":
            self.vms.clear()
        else:
            vm = next((vm for vm in self.vms if vm.name == vm_name), None)
            if vm is not None:
                self.vms.remove(vm)

    def start_vm(self, vm_name: str = "*") -> None:
        """Start VM with given name, if no name will be provided all VMs will be started.

        :param vm_name: Name of VM or *
        :raises: HyperVException when VM cannot be started
        """
        result = self._connection.execute_powershell(f"Start-VM {vm_name}", expected_return_codes={})
        if result.return_code:
            raise HyperVException(f"Cannot start VM{'s' if vm_name == '*' else f' {vm_name}'}")

    def stop_vm(self, vm_name: str = "*", turnoff: bool = False) -> None:
        """Stop VM with given name, if no name will be provided all VMs will be stopped.

        :param vm_name: Name of VM or *
        :param turnoff: whether let VM shutdown or "disconnect power from VM"
        :raises: HyperVException when VM cannot be stopped
        """
        cmd = f"Stop-VM {vm_name}"
        if turnoff:
            cmd += " -force -TurnOff -confirm:$false"

        result = self._connection.execute_powershell(cmd, expected_return_codes={})
        if result.return_code:
            raise HyperVException(f"Cannot stop VM{'s' if vm_name == '*' else f' {vm_name}'}")

    def _vm_connectivity_test(self, ip_address: IPAddress, timeout: int = 10) -> bool:
        """Ping given IP address and report result.

        :param ip_address: ip address to ping
        :param timeout: time given for ping process to reach expected state
        """
        ping = Ping(connection=self._connection)
        ping_process = ping.start(dst_ip=ip_address)
        timeout_reached = TimeoutCounter(timeout)
        while not (ping_process.running or timeout_reached):
            time.sleep(1)

        timeout_reached = TimeoutCounter(timeout)
        while ping_process.running and not timeout_reached:
            time.sleep(1)
        results = ping.stop(ping_process)
        return results.fail_count == 0

    def wait_vm_functional(self, vm_name: str, vm_mng_ip: IPAddress, timeout: int = 300) -> None:
        """Wait for Vm to be functional.

        VM is considered running and functional if its state is running and its management interface can be pinged.
        :param vm_name: virtual machine name
        :param vm_mng_ip: Ip address of VM management interface to ping
        :param timeout: maximum time duration for VM to become pingable
        :raises: HyperVException when VM management IP cannot be pinged after several attempts indicating an issue
        """
        timeout_counter = TimeoutCounter(timeout)
        while not timeout_counter:
            connectivity_result = self._vm_connectivity_test(vm_mng_ip, int(timeout / 10))
            current_state = self.get_vm_state(vm_name)
            if current_state == "Running" and connectivity_result:
                return
            logger.log(
                level=log_levels.MODULE_DEBUG,
                msg=f"Waiting 5s for VM state 'Running' and a successful ping. Current VM state is {current_state}"
                f" and ping is {'PASSing' if connectivity_result else 'FAILing'}",
            )
            time.sleep(5)
        raise HyperVException(f"VM {vm_name} cannot cannot reach state where it is pingable.")

    def wait_vm_stopped(self, vm_name: str, timeout: int = 300) -> None:
        """Wait for Vm to stop running.

        :param vm_name: virtual machine name
        :param timeout: maximum time duration for VM to become Off
        :raises: HyperVException when VM doesn't reach 'Off' state after duration of time indicating an issue
        """
        timeout_counter = TimeoutCounter(timeout)
        while not timeout_counter:
            current_state = self.get_vm_state(vm_name)
            if current_state == "Off":
                return
            logger.log(
                level=log_levels.MODULE_DEBUG,
                msg=f"Waiting 5s for VM state 'Off'. Current VM state is {current_state}",
            )
            time.sleep(5)
        raise HyperVException(f"VM {vm_name} cannot reach 'Off' state.")

    def get_vm_state(self, vm_name: str) -> str:
        """Get current vm state from host.

        :param vm_name: name of virtual machine
        """
        result = self._connection.execute_powershell(f"get-vm '{vm_name}' | fl").stdout
        return parse_powershell_list(result)[0].get("State")

    def restart_vm(self, vm_name: str = "*") -> None:
        """Restart VM with given name, if no name will be provided all VMs will be restarted.

        :param vm_name: Name of VM or *
        :raises: HyperVException when VM cannot be restarted
        """
        result = self._connection.execute_powershell(
            f"Restart-VM {vm_name} -force -confirm:$false", expected_return_codes={}
        )
        if result.return_code:
            raise HyperVException(f"Cannot restart VM{'s' if vm_name == '*' else f' {vm_name}'}")

    def clear_vm_locations(self) -> None:
        """Clear all possible VMs locations."""
        logger.log(level=log_levels.MODULE_DEBUG, msg="Clean all possible VMs locations.")

        locations = list(self._get_disks_free_space().keys())
        vms_locations = [f"{location}\\VMs" for location in locations]

        for location in vms_locations:
            try:
                self._connection.execute_powershell(f"Remove-Item -Recurse -Force {location}\\*")
            except Exception:
                pass

    def get_vm_attributes(self, vm_name: str) -> Dict[str, str]:
        """Return VM attributes in form of dictionary.

        :param vm_name: name of virtual machine
        :raises: HyperVException when attributes of VM cannot be retrieved
        :return: dictionary with vm attributes
        """
        result = self._connection.execute_powershell(f"Get-VM {vm_name} | select * | fl", expected_return_codes={})

        if result.return_code:
            raise HyperVException(f"Couldn't get VM {vm_name} attributes")

        return parse_powershell_list(result.stdout)[0]

    def get_vm_processor_attributes(
        self,
        vm_name: str,
    ) -> Dict[str, str]:
        """Get value of specified attribute of VMProcessor.

        :param vm_name: name of VM
        :raises: HyperVException when VMProcessor attributes cannot be retrieved
        """
        cmd = f"Get-VMProcessor -VMName {vm_name} | select * | fl"
        result = self._connection.execute_powershell(cmd, expected_return_codes={})

        if result.return_code:
            raise HyperVException(f"Couldn't get VMProcessor attributes of VM {vm_name}")

        return parse_powershell_list(result.stdout.lower())[0]

    def set_vm_processor_attribute(
        self, vm_name: str, attribute: Union[VMProcessorAttributes, str], value: Union[str, int, bool]
    ) -> None:
        """Set value of specified attribute of VMProcessor.

        :param vm_name: name of VM
        :param attribute: attribute that value is requested
        :param value: new value
        :raises: HyperVException when VMProcessor attributes cannot be set
        :return: new assigned value
        """
        if isinstance(attribute, VMProcessorAttributes):
            attribute = attribute.value
        value = standardise_value(value)

        cmd = f"Set-VMProcessor -VMName {vm_name} -{attribute} {value}"
        result = self._connection.execute_powershell(cmd, expected_return_codes={})

        if result.return_code:
            raise HyperVException(f"Couldn't set VMProcessor attribute {attribute} value {value} of VM {vm_name}")

    def _get_disks_free_space(self) -> Dict[str, Dict[str, str]]:
        """Get each disk free space.

        :return: dictionary {"partition_name": {"free": 0, "total": 5000}}
        """
        drive_types = {
            "Unknown": "0",
            "NoRootDirectory": "1",
            "Removable": "2",
            "Fixed": "3",
            "Network": "4",
            "CDRom": "5",
            "Ram": "6",
        }

        logger.log(level=log_levels.MODULE_DEBUG, msg="Get available space for each disk present on the system")
        result = self._connection.execute_powershell(
            "Get-WmiObject -Class Win32_LogicalDisk | Select-Object -Property Caption, DriveType, FreeSpace, Size | "
            "Out-File -FilePath wmi_file.txt; Get-Content wmi_file.txt; Remove-Item -Path wmi_file.txt",
            custom_exception=HyperVExecutionException,
        )

        # matches C:   3   288 300
        disk_pattern = re.compile(r"\s*(?P<partition>\w:)\s+(?P<type>\d)\s+(?P<free>\d+)\s+(?P<total>\d+)")
        disk_dict = {}
        for match in disk_pattern.finditer(result.stdout):
            # only take non-removable disks (fixed)
            if match.group("type") == drive_types.get("Fixed"):
                disk = f"{match.group('partition')}\\"
                disk_dict[disk] = {
                    "free": match.group("free"),
                    "total": match.group("total"),
                }

        if len(disk_dict) < 1:
            raise HyperVException("Expected partition was not found.")

        # sort by free space amount descending
        return dict(sorted(disk_dict.items(), key=lambda item: int(item[1]["free"]), reverse=True))

    def get_disk_paths_with_enough_space(self, bytes_required: int) -> str:
        """Return available_paths to disks that have enough free space for given bytes required.

        :param bytes_required: size of required VM images and differencing disks
        :raises: HyperVException when no partition is big enough
        :return: list of paths where VMs should be stored, list is ordered by the amount of free space descending
        """
        partitions = self._get_disks_free_space()
        logger.log(
            level=log_levels.MODULE_DEBUG,
            msg=f"Looking for partition with {bytes_required / 1_000_000_000} GB free space..",
        )

        big_enough_partitions = [key for key, value in partitions.items() if int(value["free"]) > bytes_required]

        if len(big_enough_partitions) == 0:
            raise HyperVException("No disk that has enough space")

        partition = big_enough_partitions[0]
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Found enough space on disk: {partition}")

        # check if VMS folder exist, if not create it
        if not self._connection.path(partition, "VMs").exists():
            self._connection.execute_command("mkdir VMs", cwd=f"{partition}")
            logger.log(level=log_levels.MODULE_DEBUG, msg=f"Created VMs folder on disk {partition}")
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"VMs folder is present on disk {partition}")
        return str(self._connection.path(partition, "VMs"))

    def copy_vm_image(
        self,
        vm_image: str,
        dst_location: "Path",
        src_location: str,
    ) -> str:
        """Copy VM image from source location to destination location.

        If available compressed archive file with image will be copied.

        :param vm_image: VM image to be copied
        :param dst_location: location for VM image to be stored in
        :param src_location: source location of VM image
        """
        vm_image = f"{vm_image}.vhdx"
        src_img_path = self._connection.path(src_location, vm_image)
        dst_img_path = self._connection.path(dst_location, vm_image)

        if dst_img_path.exists():
            self._connection.execute_powershell(
                f"remove-item {dst_img_path} -force", custom_exception=HyperVExecutionException
            )
            time.sleep(3)

        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Copying {vm_image} from {src_location}")
        src_zip_path = src_img_path.with_suffix(".zip")
        if src_zip_path.exists():
            dst_zip_path = dst_img_path.with_suffix(".zip")

            copy(
                self._connection,
                self._connection,
                src_zip_path,
                dst_zip_path,
            )

            logger.log(level=log_levels.MODULE_DEBUG, msg="Unpacking image from .zip archive and removing archive")
            # tar is preferred tool for decompression since it is about twice as fast as cmdlet
            # tar, by default is not available on Windows Server 2016 thus in that case use cmdlet
            if "16" in self._connection.get_system_info().os_name:
                self._connection.execute_powershell(
                    f"Expand-Archive -LiteralPath {dst_zip_path} {str(self._connection.path(dst_zip_path).parent)}",
                    cwd=str(self._connection.path(dst_zip_path).parent),
                )
            else:
                self._connection.execute_powershell(
                    f"tar -xf {dst_zip_path}", cwd=self._connection.path(dst_zip_path).parent
                )
            time.sleep(3)
            self._connection.execute_powershell(f"remove-item {dst_zip_path} -force")
            time.sleep(3)
        else:
            copy(
                self._connection,
                self._connection,
                src_img_path,
                dst_img_path,
            )
        return dst_img_path

    def _get_file_metadata(self, file_path: Union[str, Path]) -> Dict[str, str]:
        """Get metadata of file.

        Metadata consists of LastWriteTime and Length (size in bytes) of given file.

        :param file_path: file path
        """
        result = self._connection.execute_powershell(f"get-itemproperty {file_path} | fl")
        pattern = r"Length\s+:\s*(?P<length>[0-9]+)[a-zA-Z0-9:\s\n\/]+LastWriteTime\s+:\s*(?P<lwt>.*[AP]M)"
        match = re.search(pattern, result.stdout)
        if not match:
            raise HyperVException(f"Could not read file {file_path} metadata")
        length = match.group("length")
        last_write_time = match.group("lwt")

        logger.log(
            level=log_levels.MODULE_DEBUG,
            msg=f"Image {file_path} LastWriteTime: {last_write_time}, Length: {length}",
        )
        return {"lwt": last_write_time, "length": length}

    def _is_same_metadata(self, file_1: Dict[str, str], file_2: Dict[str, str], max_difference: str = 300) -> bool:
        """Check if metadata are the same.

        LastWriteTime is allowed to differ provided maximum number pof seconds.

        :param file_1: file metadata
        :param file_2: file metadata
        :param max_difference: maximum number of seconds 2 metadata can differ to be considered the same metadata
        """
        date_time_1 = datetime.strptime(file_1["lwt"], "%m/%d/%Y %I:%M:%S %p")
        date_time_2 = datetime.strptime(file_2["lwt"], "%m/%d/%Y %I:%M:%S %p")
        difference = date_time_1 - date_time_2

        diff_seconds = int(abs(difference.total_seconds()))
        if file_1["length"] == file_2["length"]:
            if diff_seconds == 0:
                return True
            if diff_seconds <= max_difference:
                logger.log(
                    level=log_levels.MODULE_DEBUG,
                    msg=f"LastWriteTime attribute difference ({diff_seconds}s) of both images is less than"
                    f" {max_difference}s. Sizes of both images are the same. No need to copy new file.",
                )
                return True

            logger.log(
                level=log_levels.MODULE_DEBUG,
                msg=f"LastWriteTime attribute difference ({diff_seconds}s) of both images is more than"
                f" {max_difference}s. Sizes of both images are the same. Need to copy new file.",
            )
            return False

        logger.log(level=log_levels.MODULE_DEBUG, msg="Sizes of both images are not the same. Need to copy new file.")
        return False

    def is_latest_image(
        self,
        local_img_path: "Path",
        fresh_images_path: str,
    ) -> bool:
        """Check if given image is up-to-date with remote VM location.

        :param local_img_path: VM image to be checked
        :param fresh_images_path: location for VM image to be stored in
        """
        remote_img_path = self._connection.path(fresh_images_path, local_img_path.name)
        if not remote_img_path.exists():
            logger.log(level=log_levels.MODULE_DEBUG, msg="Image not found on remote sharepoint. No copying required.")
            return True

        local_metadata = self._get_file_metadata(local_img_path)
        remote_metadata = self._get_file_metadata(remote_img_path)
        return self._is_same_metadata(local_metadata, remote_metadata)

    def get_vm_template(self, vm_base_image: str, src_location: str) -> str:
        """Get local path to VM image that will serve as a template for differencing disks.

        :param vm_base_image: image file name to find
        :param src_location: source location of VM image
        :return: image absolute path
        """
        # get location with most free space
        location = list(self._get_disks_free_space().keys())[0]
        logger.log(
            level=log_levels.MODULE_DEBUG, msg=f"VM-Template should be located on disk with most space: {location}"
        )

        vm_temp_path = self._connection.path(location, "VM-Template")
        if not vm_temp_path.exists():
            self._connection.execute_command("mkdir VM-Template", cwd=f"{location}")
            logger.log(level=log_levels.MODULE_DEBUG, msg=f"Created VM-Template folder on disk {location}")
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"VM-Template folder is present on disk {location}")

        # check if it contains disk with specified name
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Check if {vm_base_image} is present in {vm_temp_path}")
        result = self._connection.execute_powershell(
            command="Get-ChildItem | select -ExpandProperty FullName",
            cwd=f"{vm_temp_path}",
            custom_exception=HyperVExecutionException,
        )

        local_img_paths = [self._connection.path(item) for item in result.stdout.strip().splitlines()]
        for path in local_img_paths:
            filename = path.stem
            if vm_base_image == filename:
                if not self.is_latest_image(path, src_location):  # pragma: no cover
                    self.copy_vm_image(vm_base_image, vm_temp_path, src_location)
                logger.log(
                    level=log_levels.MODULE_DEBUG,
                    msg=f"Found base image {path}",
                )
                return str(path)
        else:
            logger.log(level=log_levels.MODULE_DEBUG, msg="File not found. It must be copied from external source")
            copied_image_path = self.copy_vm_image(vm_base_image, vm_temp_path, src_location)
            logger.log(
                level=log_levels.MODULE_DEBUG,
                msg=f"Found base image {copied_image_path}",
            )
            return str(copied_image_path)

    def create_differencing_disk(self, base_image_path: str, diff_disk_dir_path: str, diff_disk_name: str) -> str:
        """Create differencing disk for VM from base image.

        :param base_image_path: Path to base disk file
        :param diff_disk_dir_path: Absolute path to differencing disks directory
        :param diff_disk_name: Name of differencing disk
        :raises: HyperVException when differencing disk cannot be created
        :return: absolute path to created differencing disk
        """
        path_with_name = self._connection.path(diff_disk_dir_path, diff_disk_name)
        cmd = f"New-VHD -ParentPath {base_image_path} {path_with_name} -Differencing"
        result = self._connection.execute_powershell(cmd, expected_return_codes={})

        if result.return_code:
            raise HyperVException(f"Cannot create differencing disk {diff_disk_name}")

        # double check to make sure that disk exists even when command return code was 0
        if self._connection.path(diff_disk_dir_path, diff_disk_name).exists():
            logger.log(level=log_levels.MODULE_DEBUG, msg=f"VM differencing disk created: {path_with_name}")
            return str(path_with_name)

        raise HyperVException("Command execution succeed but disk doesn't exist ")

    def remove_differencing_disk(self, diff_disk_path: str) -> None:
        """Remove differencing disk.

        :param diff_disk_path: absolute path to differencing disk
        """
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Removing differencing disk {diff_disk_path}")
        cmd = f"Remove-Item {diff_disk_path}"
        self._connection.execute_powershell(cmd, custom_exception=HyperVExecutionException)

    def get_hyperv_vm_ips(self, file_path: str) -> List[IPAddress]:
        """Retrieve vm ip list from file."""
        result = self._connection.path(file_path).read_text()
        segments = result.split("\n\n")
        hv_segment = next(seg for seg in segments if "[hv]" in seg)

        ips = hv_segment.split()
        valid_ips = [IPAddress(ip.strip()) for ip in ips if "[" not in ip and "#" not in ip]
        network = IPNetwork(f"{self._connection._ip}/{self._get_mng_mask()}")
        return [ip for ip in valid_ips if ip in network]

    def _get_mng_mask(self) -> int:
        """Return Network Mask of management adapter (managementvSwitch)."""
        output = self._connection.execute_powershell("ipconfig").stdout
        parsed_output = parse_powershell_list(output)

        mng_adapter_info = next(
            adapter_info for adapter_info in parsed_output if str(self._connection._ip) in adapter_info.values()
        )
        mask_key = next(key for key in mng_adapter_info.keys() if "Subnet Mask" in key)
        mask = mng_adapter_info[mask_key]
        return IPAddress(mask).netmask_bits()

    def get_free_ips(self, ips: List[IPAddress], required: int = 5, timeout: int = 1200) -> List[str]:
        """Get IP addresses that are not taken and can't pi successfully pinged.

        Usually free IP addresses  do not send response when pinged back.
        :param ips: list of all VM IP addresses
        :param required: required number of IP addresses
        :param timeout: time given to check available IP addresses
        :raises: HyperVException when number of available VM IP addresses is less that required
        """
        taken_ips = []
        timeout_reached = TimeoutCounter(timeout)
        while not timeout_reached:
            not_choosen_ips = [item for item in ips if item not in taken_ips]
            ip = random.choice(not_choosen_ips)
            if not self._vm_connectivity_test(ip, 10):
                taken_ips.append(ip)
            if len(taken_ips) == required:
                return taken_ips
        raise HyperVException(
            f"Not enough free VM IPs. Found only {len(taken_ips)} IPs but {required} was required."
            f"Timeout of {timeout}s has been reached."
        )

    def format_mac(self, ip: IPAddress, guest_mac_prefix: str = "52:5a:00") -> str:
        """Get MAC address string based on mng IP address.

        VM-guest's management adapter MAC address is encoded to following formula:
            XX:XX:XX:YY:YY:YY, where

            XX:XX:XX - is constant part defined by 'guest_mac_prefix' field
            YY:YY:YY - 3 least significant octets from ip address

            Example:
                52:54:00:66:16:7B in case of KVM and ip = 10.102.22.103

        :param ip: IP address
        :param guest_mac_prefix: first 3 bytes of MAC address that are const
        :raises: HyperVException when MAC address cannot be produced from given IP address
        """
        match = re.search(r"(?:[\d]{1,3})\.([\d]{1,3})\.([\d]{1,3})\.([\d]{1,3})", str(ip))
        if match:
            return "{}:{:02x}:{:02x}:{:02x}".format(guest_mac_prefix, *[int(x) for x in match.groups()]).lower()
        raise HyperVException(f"Couldn't format IP {ip} into MAC address.")

    def _wait_vm_mng_ips(self, vm_name: str = "*", timeout: int = 3600) -> str:
        """Wait for specified VM or all VMs management adapters to receive correct IP address.

        During setup of many VMs DHCP takes long time to set up vm adapter IP address.
        :param vm_name: name of VM or *
        :param timeout: maximum time duration waited
        :raises: HyperVException when VM management interface cannot set (DHCP) IP address after given amount of time
        """
        timeout_reached = TimeoutCounter(timeout)
        while not timeout_reached:
            result = self._connection.execute_powershell(
                f"Get-VMNetworkAdapter -VMName {vm_name}"
                " | select vmname, ipaddresses, macaddress"
                " | Sort-Object -Property VMName | fl",
                expected_return_codes={0},
            )

            data = parse_powershell_list(result.stdout)[0]
            addresses = data["IPAddresses"]

            pattern = r"(?P<ipv4>([0-9]{1,3}\.){3}[0-9]{1,3})"
            match = re.search(pattern, addresses)

            if not match:
                logger.log(
                    level=log_levels.MODULE_DEBUG,
                    msg="Hosts not ready yet. No IPv4 address found. Waiting for IPs to set up",
                )
                time.sleep(5)
                continue

            ip4 = match.group("ipv4")
            if re.search(r"169(\.[0-9]{1,3}){3}", ip4):
                logger.log(
                    level=log_levels.MODULE_DEBUG,
                    msg="Hosts not ready yet. Default IPv4 address found. Waiting for IPs to set up",
                )
                time.sleep(5)
                continue

            return ip4

        raise HyperVException("Problem with setting IP on mng adapter on one of VMs")

    def _remove_folder_contents(self, dir_path: Union[str, Path]) -> None:
        """Empty specified folder.

        :param: dir_path: path to directory which has to be emptied
        """
        logger.log(
            level=log_levels.MODULE_DEBUG, msg=f"Remove all folders and files from {dir_path} after VMs cleanup"
        )
        self._connection.execute_powershell(
            "get-childitem -Recurse | remove-item -recurse -confirm:$false", cwd=dir_path
        )

    def _is_folder_empty(self, dir_path: Union[str, Path]) -> bool:
        """Check if specified folder is empty.

        :param: dir_path: path to directory which has to be emptied
        """
        # ensure directory is empty
        result = self._connection.execute_powershell(
            "Get-ChildItem | select -ExpandProperty fullname", cwd=dir_path, expected_return_codes={}
        )
        return result.stdout == ""

    def get_file_size(self, path: str) -> int:
        """Return size in bytes of specified file.

        :param path: absolute path of file
        :return: size of specified file
        """
        result = self._connection.execute_powershell(
            f"(Get-Item -Path {path}).Length", custom_exception=HyperVExecutionException
        )
        logger.log(
            level=log_levels.MODULE_DEBUG, msg=f"File {path} is ({round(int(result.stdout) / 1_000_000_000_000, 2)}GB)"
        )
        return int(result.stdout)
