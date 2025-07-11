# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for exceptions."""
import subprocess


class HyperVException(Exception):
    """Handle HyperV module exceptions."""


class HyperVExecutionException(subprocess.CalledProcessError):
    """Handle execution exceptions."""
