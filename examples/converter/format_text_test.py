#!/usr/bin/env python3
import common
from pawnlib.typing.converter import format_text, format_hex, format_link
from pawnlib.output.color_print import dump, classdump
from pawnlib.config import pawnlib_config as pawn

text = "This is text"

styles = ["bold", "italic", "code", "pre", "strike", "quote"]

# Displaying Slack/Markdown formatted text
pawn.console.log("### SLACK/MARKDOWN FORMATTING ###")
for style in styles:
    formatted_text = format_text(text, style)
    pawn.console.log(f"[{style.upper()}] : {formatted_text}")

# Adding a separator between Slack/Markdown and HTML formatting
pawn.console.log("\n### HTML FORMATTING ###")
for style in styles:
    formatted_html = format_text(text, style, output_format='html')
    pawn.console.log(f"[{style.upper()}] : {formatted_html}")


# Slack-style link
formatted_link_slack = format_link("http://google.com", "Google")
pawn.console.log(formatted_link_slack)


# Markdown-style link
formatted_link_markdown = format_link("http://google.com", "Google", output_format="markdown")
pawn.console.log(formatted_link_markdown)
# Output: [Google](http://google.com)

# HTML-style link
formatted_link_html = format_link("http://google.com", "Google", output_format="html")
pawn.console.log(formatted_link_html)
# Output: <a href="http://google.com">Google</a>

# Custom delimiters
formatted_link_custom = format_link("http://google.com", "Google", output_format="custom", custom_delimiters=("<<", ">>"))
pawn.console.log(formatted_link_custom)
# Output: <<Google:http://google.com>>

# Text defaults to URL
formatted_link_default = format_link("http://google.com")
pawn.console.log(formatted_link_default)
# Output: <http://google.com|http://google.com>

formatted_link_html = format_link("http://google.com", "Google",
                                  output_format="html",
                                  html_attributes={"target": "_blank", "rel": "noopener noreferrer"}
                                  )
pawn.console.log(formatted_link_html)

