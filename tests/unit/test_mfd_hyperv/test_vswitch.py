# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Tests for `mfd_hyperv` vswitch."""

import pytest
from mfd_connect import LocalConnection
from mfd_typing import OSName

from mfd_hyperv.instances.vswitch import VSwitch


class TestVNetworkInterface:
    @pytest.fixture()
    def vswitch(self, mocker):
        conn = mocker.create_autospec(LocalConnection)
        conn.get_os_name.return_value = OSName.WINDOWS
        vswitch = VSwitch(
            connection=conn,
            interface_name="ifname",
            host_adapter_names=["host_adapter_name"],
            enable_iov=True,
            enable_teaming=False,
            host_adapters=[mocker.Mock()],
        )
        mocker.stopall()
        return vswitch

    def test_set_and_verify_attribute(self, vswitch, mocker):
        mocker.patch("mfd_hyperv.vswitch_manager.VSwitchManager.set_vswitch_attribute")
        mocker.patch("time.sleep")

        attrs = {"rscoffloadenabled": "10"}
        vswitch.owner.hyperv.vswitch_manager.get_vswitch_attributes.return_value = attrs

        vswitch.set_and_verify_attribute("enablerscoffload", "10")

    def test_rename(self, vswitch, mocker):
        mocker.patch("mfd_hyperv.vswitch_manager.VSwitchManager.rename_vswitch")

        new_name = "new_test_name"
        vswitch.rename(new_name=new_name)

        assert vswitch.name == f"vEthernet ({new_name})"
        assert vswitch.interface_name == new_name
