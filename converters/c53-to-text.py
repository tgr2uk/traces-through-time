#!/usr/bin/env python
# pylint: disable=invalid-name
# weird filename ok because not a module
# pylint: enable=invalid-name

"""
Strip any dateline [no date] elements from a Henry III
fineroll XML file, along metadata and any other boring
elements
"""
from __future__ import print_function
from os import path as fp
import codecs
import math
import os
import sys
import xml.etree.ElementTree as ET
import re

from ttt.cli import CliConfig, iodir_argparser, generic_main
from ttt.date import read_date

_MEMBRANE_BRACKETS = re.compile(r'\s*\((.*)\)')
_MEMBRANE_PUNCT = re.compile(r'[.:-]')

# ---------------------------------------------------------------------
#
# ---------------------------------------------------------------------


def _digits(items):
    "number of digits needed to represent the size of the given list"
    if items:
        return int(math.log10(len(items))) + 1
    else:
        return 1


def _empty_out(node):
    """
    Delete all children and text in a node
    """
    for child in node:
        node.remove(child)
    node.text = ''


def _remove_boring_parts(tree):
    """
    Remove unwanted pieces of the input XML tree
    (in place, returns None)
    """
    for node in tree.iter('teiHeader'):
        tree.remove(node)
    for node in tree.iter('note'):
        _empty_out(node)
    for dateline in tree.iter('dateline'):
        text = ''.join(dateline.itertext()).strip()
        if "No date" in text:
            _empty_out(dateline)


def _membrane_name(line):
    """
    Turn the name of a membrane into something we can use as
    part of a filename
    """
    mname = line.lower().strip()
    mname = " ".join(mname.split()[:2])
    mname = _MEMBRANE_PUNCT.sub("", mname)
    mname = _MEMBRANE_BRACKETS.sub(r".\1", mname)
    mname = "-".join(mname.split())
    return mname


def _write_membrane(ntext, oprefix):
    """
    Write out text for an individual membrane
    (may involve multiple files)
    """
    lines = ntext.split("\n")
    mname = _membrane_name(lines[0])
    subentries = lines[1:]
    digits = _digits(subentries)
    for i, line in enumerate(subentries):
        date_str = " ".join(line.split()[:3])
        try:
            date = read_date(date_str, fuzzy=True)
        except ValueError as _:
            date = None
        filename = "-".join([oprefix,
                             mname,
                             str(i+1).zfill(digits)])
        with codecs.open(filename, 'w', 'utf-8') as stream:
            if date is not None:
                print(date, file=stream)
            print(line, file=stream)


def _write_items(tree, oprefix):
    """
    Write out text for individual pieces of the XML tree.
    (nimrodel or opennlp seem to crash and burn on large files,
    so we have to feed it little tiny pieces)
    """
    for node in tree.iter('entry'):
        ntext = node.text.strip()
        if ntext.startswith("Membrane "):
            _write_membrane(ntext, oprefix)


def convert(idir, odir, subpath):
    """
    read XML file, write tweaked XML file
    """
    # Is there a cleaner way to do this?
    try:
        prefix = subpath[:10]  # e.g. C53_p00177
        tree = ET.parse(fp.join(idir, subpath))
        oprefix = fp.join(odir, prefix)
        if not fp.exists(oprefix):
            os.makedirs(oprefix)
        _write_items(tree, fp.join(oprefix, prefix))
    except ET.ParseError as oops:
        # shrug
        print(oops, file=sys.stderr)


def main():
    """
    Read input dir, dump in output dir
    """
    cfg = CliConfig(description='C53 xml to text',
                    input_description='XML files (via antiword)',
                    glob='*.xml')
    psr = iodir_argparser(cfg)
    args = psr.parse_args()
    generic_main(cfg, convert, args)

if __name__ == '__main__':
    main()
