#!/usr/bin/env python
"""
Given a directory of nimrodel json output files,
produce an HTML report
"""


from __future__ import print_function
from collections import defaultdict
from os import path as fp
import argparse
import codecs
import copy
import itertools
import json
import glob
import os

from html import XHTML

# ---------------------------------------------------------------------
# report format
# ---------------------------------------------------------------------

# columns to emit in the report
_PRIMARY_COL = 'origOccurrence'
_DEFAULT_COLS = [_PRIMARY_COL,
                 'count',
                 'forename',
                 'surname',
                 'article',
                 'title',
                 'role',
                 'provenance',
                 'appearanceDate']

# ---------------------------------------------------------------------
# html helpers
# ---------------------------------------------------------------------


def _add_column(hrow, is_header, content):
    """
    Add a column to a row

    Content can either be just a string, or a tuple
    of string and HTML attributes
    """
    if isinstance(content, tuple):
        text, attrs = content
    else:
        text = content
        attrs = {}

# pylint: disable=star-args
    if is_header:
        hrow.th(text, **attrs)
    else:
        hrow.td(text, **attrs)
# pylint: enable=star-args


def _add_row(table, headers, columns):
    """
    Add a row to an html table with a th cell for each
    header and a td cell for each column.

    The headers and columns could optionally be just
    a string, or a tuple of string and attributes

    Returns the row (which you could just ignore as this
    mutates the table)
    """
    hrow = table.tr()
    for col in headers:
        _add_column(hrow, True, col)
    for col in columns:
        _add_column(hrow, False, col)
    return hrow

# ---------------------------------------------------------------------
# overview
# ---------------------------------------------------------------------


def count(fun, items):
    """
    (v -> int, [v]) -> int
    """
    return sum(map(fun, items))


def count_and_mean(fun, items):
    """
    ((v -> int), [v]) -> (int, int)
    """
    total = count(fun, items)
    avg = float(total)/len(items)
    return (total, avg)


_REPORT_CSS = """
table { border: none; border-collapse: collapse; }
table td { border-left: 1px solid #000; padding: 2px;
           text-align: right; }
table th { border-left: 1px solid #000; }
table td:first-child { border-left: none; }
table th:first-child { border-left: none; }
"""


def _mk_overview(ofile, records,
                 records_before=None):
    """
    Create an HTML report showing some useful numbers about
    our data
    """

    htree = XHTML()
    htree.head.meta.style(_REPORT_CSS)
    hbody = htree.body

    def _add_header(table):
        "add a header to a count table"
        cols = ['']
        if records_before is not None:
            cols.append('before total')
        cols.append('after total')
        if records_before is not None:
            cols.append('before mean')
        cols.append('after mean')
        _add_row(table, cols, [])


    def _add_stat(table, name, get_stat):
        "add a statistic to a count table"
        cols = [name]
        sum_aft, avg_aft = count_and_mean(get_stat, records.values())
        if records_before is not None:
            sum_bef, avg_bef = count_and_mean(get_stat, records_before.values())
        else:
            sum_bef, avg_bef = -1, -1

        if records_before is not None:
            cols.append(unicode(sum_bef))
        cols.append(unicode(sum_aft))

        if records_before is not None:
            cols.append("{:.4}".format(avg_bef))
        cols.append("{:.4}".format(avg_aft))

        _add_row(table, [], cols)


    def get_num_attrs(items):
        "number of non-empty values for a list of dictionaries"
        non_empty = lambda d: len([v for v in d.values() if v])
        return count(non_empty, items)


    def get_num_instances(attr):
        """
        str -> [dict] -> int
        number of times an attribute is non empty
        """
        def inner(items):
            "[dict] -> int"
            non_empty = lambda d: 1 if d.get(attr) else 0
            return count(non_empty, items)
        return inner


    def mk_report_block(rlist, descr, prefix):
        """
        append a bullet point to a list, pointing to
        various subreports
        """
        item = rlist.li
        item.a(descr, href=prefix+".html")
        if records_before:
            item.span(" (")
            item.a("before", href=prefix+"-before.html")
            item.span(" | ")
            item.a("after", href=prefix+"-after.html")
            item.span(")")


    hbody.h2("reports")
    rlist = hbody.ul
    mk_report_block(rlist, "item by item", "report")
    mk_report_block(rlist, "each file condensed", "condensed")
    mk_report_block(rlist, "whole dir condensed", "single")

    hbody.h2('general counts')
    htotals = hbody.table
    _add_header(htotals)
    _add_stat(htotals, 'files', lambda _: 1)
    _add_stat(htotals, 'records', len)
    _add_stat(htotals, 'attributes', get_num_attrs)

    hbody.h2('attributes')
    hattrs = hbody.table
    _add_header(hattrs)
    attrs = _get_colnames(records, records_before=records_before,
                          default=[])
    for attr in attrs:
        _add_stat(hattrs, attr, get_num_instances(attr))

    with codecs.open(ofile, 'w', 'utf-8') as ofile:
        print(htree, file=ofile)

# ---------------------------------------------------------------------
# tabular report
# ---------------------------------------------------------------------


def _get_colnames(records, records_before=None,
                  default=None):
    """
    Return ordered list of attributes to print out as table columns
    """
    default = _DEFAULT_COLS if default is None else default
    keyset = set(default)
    records_before = records_before or {}
    for _, record in itertools.chain(records.iteritems(),
                                     records_before.iteritems()):
        for subrecord in record:
            keyset.update(subrecord.keys())

    return default + sorted(keyset - frozenset(default))

_BEFORE_STYLE = {'style':'color:grey;'}


def _add_report_row(colnames, htable, subrecord,
                    filename=None,
                    is_before=False):
    """
    Populate a row with elements from a record
    """
    if is_before:
        mk_content = lambda t: (t, _BEFORE_STYLE)
    else:
        mk_content = lambda t: t

    headers = [filename or ""]
    columns = [mk_content(unicode(subrecord.get(c, "")))
               for c in colnames]
    _add_row(htable, headers, columns)


def _add_rowset(filename, colnames, htable, record,
                record_before=None):
    """
    Add rows to the table, one for each subrecord
    """
    record_after = record
    if record_before:
        _add_report_row(colnames, htable, record_before[0],
                        filename=filename,
                        is_before=True)
        for subrec in record_before[1:]:
            _add_report_row(colnames, htable, subrec,
                            is_before=True)
    elif record:
        _add_report_row(colnames, htable, record[0],
                        filename=filename)
        record_after = record[1:]

    for subrec in record_after:
        _add_report_row(colnames, htable, subrec)


def _mk_report(ofile, records,
               records_before=None):
    """
    dictionary of records to html tree
    """
    htree = XHTML()
    htable = htree.body.table()

    colnames = _get_colnames(records, records_before)
    _add_row(htable, ['file'] + colnames, [])
    fnames = set(records.keys())
    fnames = fnames | set(records_before.keys() if records_before else [])
    for fname in sorted(fnames):
        record_before = None if records_before is None\
            else records_before.get(fname)
        record_after = records.get(fname, [])
        _add_rowset(fname, colnames, htable, record_after,
                    record_before=record_before)
    with codecs.open(ofile, 'w', 'utf-8') as ofile:
        print(htree, file=ofile)

# ---------------------------------------------------------------------
# condensing
# ---------------------------------------------------------------------


def _subrec_key(subrec):
    """
    Hashabel representation of a subrecord
    """
    return tuple(sorted(subrec.items()))


def _condense_helper(subrecs):
    """
    count the instances of a subrecord within a record
    """
    counts = defaultdict(int)
    subrecs2 = []
    for subrec in subrecs:
        key = _subrec_key(subrec)
        if key not in counts:
            subrec2 = copy.copy(subrec)
            subrecs2.append(subrec2)
        counts[key] += 1
    for subrec in subrecs2:
        subrec['count'] = counts[_subrec_key(subrec)]
    return subrecs2


def _condense_records(records):
    """
    remove duplicate subrecords but keep track of the times they occur
    """
    records2 = {}
    for fname, subrecords in records.items():
        records2[fname] = sorted(_condense_helper(subrecords),
                                 key=lambda d: d.get(_PRIMARY_COL))
    return records2


def _supercondense_record(records):
    """
    squash all records into a single dir-wide record

    (returns that one list instead of a dictionary)
    """
    elems = itertools.chain.from_iterable(records.values())
    return sorted(_condense_helper(elems),
                  key=lambda d: d.get(_PRIMARY_COL))

# ---------------------------------------------------------------------
#
# ---------------------------------------------------------------------


def _read_inputs(inputdir):
    """
    Read input dir, return dictionary from filenames to json records
    """
    records = {}
    for filename in glob.glob(fp.join(inputdir, '*')):
        with open(filename) as ifile:
            bname = fp.basename(filename)
            subrecs = json.load(ifile)
            records[bname] = [subrecs]\
                if isinstance(subrecs, dict) else subrecs
    return records


def _norm_records(records):
    """
    Tidy up whitespace within records
    """
    records2 = {}
    for fname, subrecs in records.items():
        subrecs2 = []
        for subrec in subrecs:
            subrec2 = {}
            for key in subrec:
                subrec2[key] = " ".join(subrec[key].split())
            subrecs2.append(subrec2)
        records2[fname] = subrecs2
    return records2


def main():
    """
    Read input dir, dump in output dir
    """
    psr = argparse.ArgumentParser(description='TTT converter')
    psr.add_argument('input', metavar='DIR', help='dir with json files')
    psr.add_argument('output', metavar='DIR', help='output directory')
    psr.add_argument('--before', metavar='DIR',
                     help='another dir with json files (for comparsion)')
    args = psr.parse_args()
    if not fp.exists(args.output):
        os.makedirs(args.output)

    # straightforward one row per json object
    records = _norm_records(_read_inputs(args.input))
    # squashed and sorted within each file
    crecords = _condense_records(records)
    # squashed and sorted altogether
    drecords = {fp.basename(args.input):
                _supercondense_record(records)}

    # if we're in diff mode
    if args.before:
        records_before = _norm_records(_read_inputs(args.before))
        crecords_before = _condense_records(records_before)
        drecords_before = {fp.basename(args.before):
                           _supercondense_record(records_before)}
        _mk_report(fp.join(args.output, "report-before.html"),
                   records_before)
        _mk_report(fp.join(args.output, "report-after.html"),
                   records)
        _mk_report(fp.join(args.output, "condensed-before.html"),
                   crecords_before)
        _mk_report(fp.join(args.output, "condensed-after.html"),
                   crecords)
        _mk_report(fp.join(args.output, "single-before.html"),
                   drecords_before)
        _mk_report(fp.join(args.output, "single-after.html"),
                   drecords)
    else:
        records_before = None
        crecords_before = None
        drecords_before = None


    _mk_overview(fp.join(args.output, "index.html"),
                 records,
                 records_before=records_before)
    _mk_report(fp.join(args.output, "report.html"),
               records,
               records_before=records_before)
    _mk_report(fp.join(args.output, "condensed.html"),
               crecords,
               records_before=crecords_before)
    _mk_report(fp.join(args.output, "single.html"),
               drecords,
               records_before=drecords_before)


main()
