#!/usr/bin/env python3
# A super minimal static site generator
# Written by Samadi van Koten
# Disclaimer: I wrote this in a few hours so don't blame me if it breaks

import sys
from warnings import warn
if sys.version_info.major < 3 or \
        (sys.version_info.major == 3 and sys.version_info.minor < 2):
    raise RuntimeError("This script requires Python 3.2 or greater (3.4.1 minimum recommended)")
elif sys.version_info.minor < 4 or \
        (sys.version_info.minor == 4 and sys.version_info.micro < 1):
    warn("This script may run incorrectly on versions of Python less than 3.4.1", RuntimeWarning)


import re
import os
from distutils import dir_util # Weird place for a recursive directory copy...
from collections import namedtuple
import cinje # Template engine
import markdown

sys.path.insert(0, '') # Allow importing from the current directory
import config
import template # Yes, cinje is just that awesome

Page = namedtuple("Page", "title body path")

# A regex for extracting titles
TITLE_RE = re.compile(r"^(?:\s*\n)*title\s*:\s*(.*)")

def read_pages(content="content"):
    # Initialize a markdown translator with extensions such as tables, etc.
    mdconv = markdown.Markdown(extensions=[
        'markdown.extensions.extra',
        ])

    for path, dirs, files in os.walk(content):
        for fn in files:
            # Check if it's a markdown file
            if not fn.lower().endswith(".md"):
                print(fn + ": Not a markdown file")
                continue

            # Read the markdown file
            file_path = os.path.join(path, fn)
            with open(file_path, "r") as f:
                md = f.read()

            # Extract the title, if it's specified
            title = None
            m = TITLE_RE.match(md)
            if m:
                md = md[:m.start()] + md[m.end():]
                title = m.group(1)

            # Convert the markdown to HTMl
            md_html = mdconv.convert(md)
            mdconv.reset() # Resetting improves speed, apparently

            # Yield a Page object
            page_path = file_path.lstrip(content).rstrip("md") + "html"
            yield Page(title, md_html, page_path)

def build(pages=None, output="output"):
    if not pages:
        pages = config.pages

    # Create the output directory if it doesn't exist
    if not os.path.exists(output):
        os.mkdir(output)

    # Recursively copy assets/ into the output directory
    dir_util.copy_tree("assets", os.path.join(output, "assets"), update=1)

    for page in pages:
        # Render the template with the Page object
        out_html = ''.join(template.render(config, page))

        # Can't use os.path.join because page.path is absolute
        outpath = os.path.normpath(output + page.path)

        # Create the parent directory if necessary
        outdir = os.path.dirname(outpath)
        if not os.path.exists(outdir):
            os.makedirs(outdir)

        # Write the HTML to the output file
        with open(outpath, "w") as f:
            f.write(out_html)

if __name__=='__main__':
    config.pages = list(read_pages())
    build()
