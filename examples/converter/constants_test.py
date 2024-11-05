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



print(const.get_colored_text("This is a header", "HEADER"))
print(const.get_colored_text("This is blue text", "OKBLUE"))
print(const.get_colored_text("This is green text", "OKGREEN"))
print(const.get_colored_text("This is red text", "RED"))

# Bold and underline examples
print(const.get_colored_text("Bold and green", "OKGREEN", bold=True))
print(const.get_colored_text("Bold, red, and underlined", "RED", bold=True, underline=True))

# Text with different widths (centering text)
print(const.get_colored_text("Centered and blue", "BLUE", width=30))
print(const.get_colored_text("Another centered text", "PURPLE", width=40))

# Warning and fail examples
print(const.get_colored_text("Warning! This is important.", "WARNING"))
print(const.get_colored_text("Error occurred", "FAIL", bold=True))

# Example with ANSI codes
print(const.get_colored_text("Bright cyan", "BRIGHT_CYAN"))
print(const.get_colored_text("Dark blue", "DARK_BLUE"))

# Combining styles
print(const.get_colored_text("Bold, Underlined, and Yellow", "YELLOW", bold=True, underline=True))

# Example with formatting numbers and special characters
special_text = f"{const.get_colored_text('Success!', 'GREEN', bold=True)}: Operation completed successfully."
print(special_text)

# Example of multiple color blocks in one output
print(f"{const.get_colored_text('Info:', 'OKBLUE')} {const.get_colored_text('Everything is running smoothly.', 'WHITE')}")
print(f"{const.get_colored_text('Warning:', 'WARNING')} {const.get_colored_text('Be cautious of potential issues.', 'LIGHT_YELLOW')}")
print(f"{const.get_colored_text('Error:', 'FAIL')} {const.get_colored_text('Critical failure detected!', 'RED', bold=True)}")

# Display the available colors dynamically
available_colors = const.available_colors()
for color_name in available_colors:
    print(const.get_colored_text(f"Color: {color_name}", color_name))

# Long text examples
long_text = """
This is a very long text that will demonstrate how text wrapping works in the console.
It should be possible to apply styles to long lines of text without any issue.
Let's see if it works with different colors, bold text, and underlining.
"""
print(const.get_colored_text(long_text, "CYAN"))

# Example with formatted numbers
print(const.get_colored_text("Number formatting example: 1,234,567", "GREEN"))

# Example with special characters
print(const.get_colored_text(f"Special characters: {const.SPECIAL_CHARACTERS}", "BRIGHT_MAGENTA"))

# Multi-line output with various styles
print("\n" + const.get_colored_text("== LOG START ==", "WHITE", bold=True))
print(const.get_colored_text("INFO: Initialization started", "OKBLUE"))
print(const.get_colored_text("WARNING: Low disk space", "WARNING"))
print(const.get_colored_text("ERROR: Unable to connect to database", "FAIL", bold=True))
print(const.get_colored_text("== LOG END ==", "WHITE", bold=True))

