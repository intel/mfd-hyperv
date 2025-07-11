# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for helper functions."""
from typing import Union


def standardise_value(value: Union[int, str, bool]) -> str:
    """Make input value standardised, no matter it's type to make comparisons more easily."""
    value = str(value)
    value = value.lower()
    if value in ["true", "false"]:
        return f"${value}"
    return value
