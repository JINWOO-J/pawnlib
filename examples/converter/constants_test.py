#!/usr/bin/env python3
import common
from pawnlib.typing import const, constants
from pawnlib.config import pawn

pawn.console.log(f"Seconds in a minute: {const.MINUTE_IN_SECONDS}")
pawn.console.log(f"Grade color for '0x0': {const.grade_color('0x0')}")
pawn.console.log(f"Grade name for '0x0': {const.grade_name('0x0')}")

pawn.console.log(f"AWS Region name for 'ap-southeast-1': {const.get_aws_region_name('ap-southeast-1')}")
pawn.console.log(f"AWS Region name using direct method for 'ap-southeast-1': {const.region_name('ap-southeast-1')}")

pawn.console.log(f"AWS Regions list (keys): {list(const.REGIONS.keys())}")

pawn.console.log(f"AWS Region list: {const.get_aws_region_list()}")

pawn.console.log(f"AWS Region name for 'us-east-1': {const.get_aws_region_name('us-east-1')}")

pawn.console.log(f"AWS Region name for 'us-east-32' (invalid): {const.get_aws_region_name('us-east-32')}")
