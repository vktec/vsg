#!/usr/bin/env python3
# A super minimal static site generator
# Written by Samadi van Koten

"""
Usage:
    ./build.py [build]
    ./build.py watch
    ./build.py serve [-p <port>] [-h <host>]
    ./build.py --help
    ./build.py --version

Options:
    --help      Show this screen.
    --version   Show the version.
    -p --port   Specify a custom port to listen on [default: 8080].
    -h --host   Specify a custom host to listen on [default: localhost].
"""

VERSION="0.2.1"

import sys
from warnings import warn
if sys.version_info < (3, 2):
    raise RuntimeError("This script requires Python 3.2 or greater (3.4.1 minimum recommended)")
elif sys.version_info < (3, 4, 1):
    warn("This script may run incorrectly on versions of Python less than 3.4.1", RuntimeWarning)

import time
import os
import shutil
from os import path
from distutils import dir_util # Weird place for a recursive directory copy...
from docopt import docopt
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import cinje # Template engine
import markdown
import frontmatter

class Page:
    def __init__(self, fn, prefix=None, children=[], md=None):
        if not prefix:
            prefix = config.dirs.content

        if not md:
            md = markdown_translator

        if hasattr(fn, "path"): # Handle DirEntry objects
            fn = fn.path

        page = frontmatter.load(fn)
        self._meta = page.metadata

        # Convert the markdown to HTML
        self.body = md.convert(page.content)
        md.reset() # Resetting improves speed, apparently

        # Create the output path
        self.path = fn.lstrip(prefix).rstrip("md") + "html"

        self.children = children

    def __contains__(self, name):
        return name in self._meta or name in dir(self)

    def __getattr__(self, name):
        return self._meta[name] if name in self._meta else None

def read_pages(content=None):
    if not content:
        content = config.dirs.content

    content = path.normcase(path.normpath(content))

    def read_subdir(d):
        assert d.is_dir()

        index_path = path.join(d.path, "index.md")
        if not path.isfile(index_path):
            print(d.path + " does not contain index.md; skipping")

        children = []
        for de in os.scandir(d.path):
            if de.is_dir():
                children.extend(read_subdir(de))
                continue

            if de.name != "index.md":
                children.append(Page(de, content))

        yield Page(index_path, content, children)

    for de in os.scandir(content):
        if de.is_dir():
            yield from read_subdir(de)
            continue

        # Check if it's a markdown file
        if not de.name.endswith(".md"):
            print(fn + ": Not a markdown file")
            continue

        yield Page(de, content)

def save_pages(pages, output=None):
    if not output:
        output=config.dirs.output

    for page in pages:
        # Render the template with the Page object
        out_html = "".join(template.render(config, page))

        # Can't use path.join because page.path is absolute
        outpath = path.normpath(output + page.path)

        # Create the parent directory if necessary
        outdir = path.dirname(outpath)
        os.makedirs(outdir, exist_ok=True)

        # Write the HTML to the output file
        with open(outpath, "w") as f:
            f.write(out_html)

        # Recurse through tree
        if page.children:
            save_pages(page.children, output)

def build(pages=None, output=None, assets=None):
    if not pages:
        pages = config.pages

    if not output:
        output=config.dirs.output

    if not assets:
        assets=config.dirs.assets

    if isinstance(assets, str):
        assets = {assets}

    # Create the output directory if it doesn't exist
    os.makedirs(output, exist_ok=True)

    # Recursively copy the assets directories into the output directory
    for src in assets:
        if path.isdir(src):
            dest = path.join(output, path.basename(src))
            dir_util.copy_tree(src, dest, update=1)
        else:
            shutil.copy(src, output)

    save_pages(pages, output)

def init(opts):
    global config, template, markdown_translator

    sys.path.insert(0, "") # Allow importing from the current directory

    import template # Yes, cinje is just that awesome

    # Configuration
    import types
    defaults = types.ModuleType("vsg.defaults")
    defaults.extensions = {
            "markdown.extensions.extra",
            "markdown.extensions.codehilite",
            "markdown.extensions.sane_lists",
            }

    defaults.dirs = types.SimpleNamespace()
    defaults.dirs.content = "content"
    defaults.dirs.output = "output"
    defaults.dirs.assets = {"assets"}

    sys.modules["vsg.defaults"] = sys.modules["defaults"] = defaults
    import config
    del sys.modules["vsg.defaults"], sys.modules["defaults"]

    markdown_translator = markdown.Markdown(extensions=config.extensions)

class VsgRebuildEventHandler(FileSystemEventHandler):
    def __init__(self, *args, **kwargs):
        super(VsgRebuildEventHandler, self).__init__(*args, **kwargs)
        self.last_build_time = 0 # For debouncing

    def on_any_event(self, evt):
        # Debounce code (watchdog is a little overzealous in its event reporting)
        if self.last_build_time < time.time() - 2:
            self.last_build_time = time.time()

            print("Rebuilding...")
            config.pages = list(read_pages())
            build()

def start_watching(root="."):
    handler = VsgRebuildEventHandler()
    observer = Observer()
    observer.schedule(handler, root, recursive=True)
    observer.start()
    return observer

def main(opts):
    init(opts)
    if opts["watch"]:
        observer = start_watching()
        try:
            observer.join()
        except KeyboardInterrupt:
            observer.stop()
            observer.join()
    elif opts["serve"]:
        sys.stderr.write("Not implemented\n")
        return 1
    else: # Build
        config.pages = list(read_pages())
        build()

if __name__=="__main__":
    opts = docopt(__doc__, version="vsg v" + VERSION)
    exit(main(opts))

