> [!IMPORTANT]
> This project is under development. All source code and features on the main branch are for the purpose of testing or evaluation and not production ready.

# MFD Hyperv

Module for handling functionalities of HyperV hypervisor.

## Usage

```python
from mfd_hyperv.base import HyperV
from mfd_connect import LocalConnection

conn = LocalConnection()
hyperv = HyperV(connection=conn)
hyperv.hw_qos.delete_scheduler_queue("vSwitch00", "5")
```

## Implemented methods

### Hardware QoS Offload functionality:

* `create_scheduler_queue(vswitch_name: str,  sq_id: str, sq_name: str, limit: bool, tx_max: str, tx_reserve: str, rx_max: str) -> None` - create scheduler queue
* `update_scheduler_queue(vswitch_name: str, limit: str, tx_max: str, tx_reserve: str, rx_max: str, sq_id: str) -> None` - update existing scheduler queue
* `delete_scheduler_queue(vswitch_name: str, sq_id: str) -> None` - delete existing scheduler queue
* `get_qos_config(vswitch_name: str) -> Dict[str, Union[str, bool]]` - get current QoS configuration for the vSwitch
* `set_qos_config(vswitch_name: str, hw_caps: bool, hw_reserv: bool, sw_reserv: bool, flags: str) -> None` - set QoS configuration on the vSwitch
* `disassociate_scheduler_queues_with_vport(vswitch_name: str, vport: int) -> None` - disassociate scheduler queues with virtual port
* `list_scheduler_queues_with_vport(vswitch_name: str, vport: str) -> List[str]` - list scheduler queues associated with virtual port
* `associate_scheduler_queues_with_vport(vswitch_name: str, vport: str, sq_id: str, lid: int, lname: str) -> None` - associate scheduler queues with virtual port
* `get_vmswitch_port_name(switch_friendly_name: str, vm_name: str) -> str` - get vmswitch port name
* `is_scheduler_queues_created(vswitch_name: str, sq_id: int, sq_name: str, tx_max: str) -> bool` - check if scheduler queues was properly created
* `list_queue(vswitch_name: str) -> str` - list queue from vSwitch
* `get_queue_all_info(vswitch_name: str) -> str` - get queue info for flag `all`
* `get_queue_offload_info(vswitch_name: str, sq_id: int) -> str` -  get queue info for flag `offload` and indicated queue

### Hypervisor:

* `is_hyperv_enabled() -> bool` - check status of Hyper-V service on the machine
* `create_vm(vm_params: VMParams, owner: Optional[NetworkAdapterOwner] = None, hyperv=None, connection_timeout=3600, dynamic_mng_ip=False) -> VM` - create Hyper-V Virtual Machine (VM). Passing "hyperv" object to created VM allows for using VM object methods.
* `remove_vm(vm_name: str = "*") -> None` - remove VM with given name or all VMs
* `start_vm(vm_name: str = "*") -> None` - start VM with given name or all VMs
* `stop_vm(vm_name: str = "*", turnoff: bool = False) -> None` - stop VM with given name or all VMs. Allows to choose between graceful shutdown and forcible turnoff.
* `_vm_connectivity_test(ip_address: IPAddress) -> bool` - check ping connectivity with provided IP address
* `wait_vm_functional(vm_name: str, vm_mng_ip: IPAddress, timeout: int = 300) -> None` - wait for VM status "Running" and successful ping response
* `wait_vm_stopped(self, vm_name: str, timeout: int = 300) -> None` - wait for VM status "Off"
* `get_vm_state(vm_name: str) -> str` - get current VM state
* `restart_vm(vm_name: str = "*") -> None` - restart VM with given name or all VMs
* `clear_vm_locations() -> None` - check paths all paths where VM files could be stored and delete all remaining files
* `get_vm_attributes(vm_name: str) -> Dict[str, str]` - get VM attributes from host
* `get_vm_processor_attributes(vm_name: str) -> Dict[str, str]` - get processor attributes of given VM
* `set_vm_processor_attribute(vm_name: str, attribute: Union[VMProcessorAttributes, str], value: Union[str, int, bool]) -> None` - set VM Processor attribute
* `_get_disks_free_space() -> Dict[str, Dict[str, str]]` - return information such as the amount of free space and the total amount of space for all fixed drives that are not the system partition C
* `get_disk_paths_with_enough_space(bytes_required: int) -> str` - get disk with free space that exceeds given amount
* `copy_vm_image(vm_image: str, dst_location: "Path", src_location: str) -> str` - copy VM image from source location to destination location. If available compressed archive file with image will be copied
* `_get_file_metadata(file_path) -> Dict[str, str]` - get metadata of file. Metadata consists of LastWriteTime and Length (size in bytes) of given file.
* `_is_same_metadata(file_1, file_2, max_difference=300) -> bool` - check if metadata are the same. LastWriteTime is allowed to differ provided maximum number pof seconds.
* `is_latest_image(local_img_path: "Path", fresh_images_path: str) -> bool` - check if given image is up-to-date with remote VM location.
* `get_vm_template(vm_base_image: str, src_location: str) -> str` - get local path to VM image that will serve as a template for differencing disks.
* `create_differencing_disk(base_image_path: str, diff_disk_dir_path: str, diff_disk_name: str) -> str` - create differencing disk for VM from base image.
* `remove_differencing_disk(diff_disk_path: str) -> None` - remove differencing disk.
* `get_hyperv_vm_ips(file_path: str) -> List[IPAddress]` - retrieve vm ip list from file.
* `_get_mng_mask() -> int` - return Network Mask of management adapter (managementvSwitch).
* `get_free_ips(ips, required=5, timeout=600) -> List[str]` - get IP addresses that are not taken and can't pi successfully pinged
* `format_mac(ip, guest_mac_prefix: str = "52:5a:00") -> str` - get MAC address string based on mng IP address.
* `_wait_vm_mng_ips(vm_name: str = "*", timeout: int = 3600) -> str` - wait for specified VM or all VMs management adapters to receive correct IP address.
* `_remove_folder_contents(dir_path) -> None` - remove files from specified folder.
* `_is_folder_empty(dir_path) -> bool` - check if specified folder is empty.
* `get_file_size(path: str) -> int` - return size in bytes of specified file.

### VSwitch manager:

* `create_vswitch(interface_names: List[str], vswitch_name: str = vswitch_name_prefix, enable_iov: bool = False, enable_teaming: bool = False, mng: bool = False, interfaces: Optional[List[WindowsNetworkInterface]] = None) -> VSwitch` - create vSwitch. Passing interfaces object to created VSwitch allows for using VSwitch object methods.
* `_generate_name(vswitch_name: str, enable_teaming: bool) -> str` - create unified vswitch name with updated counter
* `create_mng_vswitch() -> VSwitch` - create management vSwitch. Only object is created when management vSwitch is already present on the machine
* `remove_vswitch(interface_name: str) -> None` - remove vswitch identified by its 'interface_name'.
*  `get_vswitch_mapping(self) -> dict[str, str]` - Get a list of Hyper-V vSwitches and the adapters they are mapped to.
        Returns: Dictionary where key are names of vswitches, values are Friendly names of an interfaces connect to (NetAdapterInterfaceDescription field from powershell output)
* `get_vswitch_attributes(interface_name: str) -> Dict[str, str]` - get vSwitch attributes in form of dictionary.
* `set_vswitch_attribute(interface_name: str, attribute: Union[VSwitchAttributes, str], value: Union[str, int, bool]) -> None` - set attribute on VSwitch.
* `remove_tested_vswitches() -> None` - remove all tested vSwitches, doesn't remove management vSwitch.
* `is_vswitch_present(interface_name: str) -> bool` - check if given virtual switch is present.
* `wait_vswitch_present(vswitch_name: str, timeout: int = 60, interval: int = 10) -> None` - wait for timeout duration for vSwitch to appear present.
* `rename_vswitch(interface_name: str, new_name: str) -> None:` - rename vSwitch and check if the change was successful

### VMNetworkInterfaceManager manager:

* `create_vm_network_interface(vm_name: str, vswitch_name: str | None = None, sriov: bool = False, vmq: bool = True, get_attributes: bool = False, vm: VM | None = None, vswitch: VSwitch | None = None) -> VMNetworkInterface` - add network interface to VM.
* `remove_vm_interface(vm_interface_name: str, vm_name: str) -> None` - remove network interface from VM.
* `connect_vm_interface(vm_interface_name: str, vm_name: str, vswitch_name: str) -> None` - connect vm adapter to virtual switch.
* `disconnect_vm_interface(vm_interface_name: str, vm_name: str) -> None` - disconnect VM Network Interface from vswitch.
* `clear_vm_interface_attributes_cache(self, vm_name=None) -> None` - clear cached vnics attributes information of specified VM.
* `set_vm_interface_attribute(vm_interface_name: str, vm_name: str, attribute: Union[VMNetworkInterfaceAttributes, str], value: Union[str, int]) -> None` - set attribute on vm adapter.
* `get_vm_interface_attributes(vm_interface_name: str, vm_name: str) -> Dict[str, str]` - get attributes of VM network interface.
* `get_vm_interfaces(vm_name: str) -> List[Dict[str, str]]` - return dictionary of VM Network interfaces.
* `_generate_name(vm_name) -> str` - create unified vn adapter interface name with updated counter
* `set_vm_interface_vlan(state, vm_name, interface_name, vlan_type, vlan_id, management_os) -> None` - configures the VLAN settings for the traffic through a virtual network adapter.
* `set_vm_interface_rdma(vm_name, interface_name, state) -> None` - set RDMA on VM nic (enable or disable)
* `get_vm_interface_vlan(vm_name, interface_name) -> Dict[str, str]` - get VLAN settings for the traffic through a virtual network adapter.
* `get_vm_interface_rdma(vm_name, interface_name) -> Dict[str, str]` - get RDMA settings for VM network adapter.
* `get_adapters_vf_datapath_active() -> bool` - Return Vfdatapathactive status of all VM adapters.
* `get_vm_interface_attached_to_vswitch(self, vswitch_name: str) -> str` - get the VMNetworkAdapter name that is attached to the vswitch.
    Parameters:
        :param `vswitch_name`: name of vswitch interface
    Raises: `HyperVExecutionException` on any Powershell command execution error
    Returns: `name` of interfaces attached to the `vswitch_name`
* `get_vlan_id_for_vswitch(self, vswitch_name: str) -> int` - get VLAN tagging set for Hyper-V vSwitch. Only access and untagged modes are supported at this point.
    Parameters:
        :param `vswitch_name`: vswitch adapter object
    Raises: `HyperVExecutionException` on any Powershell command execution error
    Returns: `vlan number`. `0` if untagged

### VSwitch:

* `interfaces()` - interfaces property representing list of interfaces that vswitch is created on.
* `interfaces(value)` - interfaces property setter
* `interfaces_binding() -> None` - create bindings between vswitch and network interfaces objects
* `get_attributes() -> Dict[str, str]` - return vSwitch attributes in form of dictionary.
* `set_and_verify_attribute(attribute: Union[VSwitchAttributes, str], value: Union[str, int, bool], sleep_duration: int = 1) -> bool` - set specified vswitch attribute to specified value and check if results where applied in the OS.
* `remove()` - remove vswitch identified by its 'interface_name'
* `rename(new_name: str) -> None` - rename vswitch with a specific name

## OS supported:

* WINDOWS

## Issue reporting

If you encounter any bugs or have suggestions for improvements, you're welcome to contribute directly or open an issue [here](https://github.com/intel/mfd-hyperv/issues).