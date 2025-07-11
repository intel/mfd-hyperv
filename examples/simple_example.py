# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT

import pathlib
import time
import logging

from time import sleep
from mfd_typing import MACAddress
from mfd_hyperv import HyperV
from mfd_connect import RPyCConnection
from mfd_hyperv.hypervisor import VMProcessorAttributes, VMParams
from mfd_hyperv.vswitch_manager import VSwitchAttributes, VSwitch
from mfd_hyperv.vm_network_interface_manager import VMNetworkInterfaceAttributes


class Owner:
    def __init__(self, connection):
        self.connection = connection


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

conn = RPyCConnection(ip="10.10.10.10")
hyperv = HyperV(connection=conn)


hyperv.hypervisor.stop_vm("*", turnoff=True)

# remove vms
hyperv.hypervisor.remove_vm()

# delete leftover tested vswitches
hyperv.vswitch_manager.remove_tested_vswitches()

hyperv.hypervisor.clear_vm_locations()

mng_vswitch = hyperv.vswitch_manager.create_mng_vswitch()

# remove vms leftovers
possible_locations = list(hyperv.hypervisor._get_disks_free_space().keys())
for path in possible_locations:
    vms_path = pathlib.PureWindowsPath(path, "VMs")
    try:
        hyperv.hypervisor.clear_vms_folders(vms_path)
    except Exception:
        pass

ips = hyperv.hypervisor.get_hyperv_vm_ips()
mac = hyperv.hypervisor.format_mac(ips[0])
#
free_vm_ips = hyperv.hypervisor.get_free_ips(ips, 1)
free_vm_macs = [hyperv.hypervisor.format_mac(ip) for ip in free_vm_ips]
dd = 1
############################################################################################################# VSwitch

if hyperv.vswitch_manager.is_vswitch_present("vs"):
    vs = VSwitch("vs", create=False)
    try:
        hyperv.vswitch_manager.remove_vswitch(vs)
    except Exception:
        pass


if not hyperv.hypervisor.is_latest_image("D:\\VM-Template\\Base_W19.vhdx"):
    hyperv.hypervisor.replace_image("D:\\VM-Template\\Base_W19.vhdx")

vswitch = hyperv.vswitch_manager.create_vswitch(["SLOT 1 Port 1"], "vs", enable_iov=False)
hyperv.vswitch_manager.rename_vswitch(vswitch.interface_name, "new_name")

hyperv.vswitch_manager.set_vswitch_attribute(vswitch.interface_name, VSwitchAttributes.EnableRscOffload, True)
attrs = hyperv.vswitch_manager.get_vswitch_attributes(vswitch.interface_name)
rsc = attrs.get(VSwitchAttributes.RscOffloadEnabled)
valu = hyperv.vswitch_manager.set_vswitch_attribute(vswitch.interface_name, VSwitchAttributes.EnableRscOffload, True)
val = hyperv.vswitch_manager.set_vswitch_attribute(
    vswitch.interface_name, VSwitchAttributes.DefaultQueueVmmqEnabled, True
)

############################################################################################################# VM

image_path = hyperv.hypervisor.get_vm_template("Base_W19")
size = hyperv.hypervisor.get_file_size(image_path)
full_size = int(size + 3 * (0.75 * size))
path = hyperv.hypervisor.get_disk_paths_with_enough_space(full_size)

diff_disk_path = hyperv.hypervisor.create_differencing_disk(image_path, path, "dd_1.vhdx")

vm_params = VMParams(
    name="Base_W19_VM001",
    cpu_count=4,
    hw_threads_per_core=0,
    memory=4096,
    generation=2,
    vm_dir_path=path,
    diff_disk_path=diff_disk_path,
    mng_interface_name="mng",
    mng_mac_address=MACAddress(free_vm_macs[0]),
    mng_ip=free_vm_ips[0],
    vswitch_name="managementvSwitch",
)

vm = hyperv.hypervisor.create_vm(vm_params)

attrs = hyperv.hypervisor.get_vm_attributes("Base_W19_VM001")

vnic = hyperv.vm_network_interface_manager.create_vm_network_interface(
    vm.name, vswitch.interface_name, sriov=True, vmq=True
)
vnic2 = hyperv.vm_network_interface_manager.create_vm_network_interface(
    vm.name, vswitch.interface_name, sriov=False, vmq=True
)


hyperv.vm_network_interface_manager.set_vm_interface_attribute(
    vnic.interface_name, vm.name, VMNetworkInterfaceAttributes.IovWeight, 0
)
time.sleep(1)
read_value = hyperv.vm_network_interface_manager.get_vm_interface_attributes(vnic.interface_name, vm.name)[
    VMNetworkInterfaceAttributes.IovWeight
]

hyperv.vm_network_interface_manager.set_vm_interface_attribute(
    vnic2.interface_name, vm.name, VMNetworkInterfaceAttributes.IovWeight, 100
)
time.sleep(1)
read_value2 = hyperv.vm_network_interface_manager.get_vm_interface_attributes(vnic2.interface_name, vm.name)[
    VMNetworkInterfaceAttributes.IovWeight
]

ifaces_info = hyperv.vm_network_interface_manager.get_vm_interfaces(vm.name)

hyperv.vm_network_interface_manager.remove_vm_interface(vnic2.interface_name, vm.name)

proc_attrs = hyperv.hypervisor.get_vm_processor_attributes(vm.name)
tpc = proc_attrs[VMProcessorAttributes.HWThreadCountPerCore]
count = proc_attrs[VMProcessorAttributes.Count]

hyperv.hypervisor.stop_vm(vm.name)

hyperv.hypervisor.set_vm_processor_attribute(vm.name, VMProcessorAttributes.HWThreadCountPerCore, 1)
hyperv.hypervisor.set_vm_processor_attribute(vm.name, VMProcessorAttributes.Count, 8)

proc_attrs = hyperv.hypervisor.get_vm_processor_attributes(vm.name)
tpc_new = proc_attrs[VMProcessorAttributes.HWThreadCountPerCore]
count_new = proc_attrs[VMProcessorAttributes.Count]

hyperv.hypervisor.start_vm(vm.name)
hyperv.hypervisor.wait_vm_functional(vm.name, vm.mng_ip)

hyperv.hypervisor.restart_vm(vm.name)
hyperv.hypervisor.wait_vm_functional(vm.name, vm.mng_ip)

# cleanup
hyperv.hypervisor.stop_vm("*", turnoff=True)
sleep(15)

# remove vms
hyperv.hypervisor.remove_vm()
sleep(5)

# delete leftover tested vswitches
hyperv.vswitch_manager.remove_tested_vswitches()

# remove vms leftovers
hyperv.hypervisor.clear_vm_locations()

dd = hyperv.hypervisor.is_hyperv_enabled()
