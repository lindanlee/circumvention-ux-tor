#!/usr/bin/env python

# * if the configuration was eventually successful
# * total time to successful configuration
# * if failure, ultimate reason for failure
# * number of tries until success
# * causes for errors
# * if participants listened to our directions (ie choosing the next bridge, or anything on the error screen)
# * all paths taken through the interface

import collections
import datetime
import getopt
import json
import re
import sys

import inst

# src and dst are vertices; i.e. pages or states in the interface.
# via is a string indicating an action that moved you from src to dst.
# src and dst can be the same.
Edge = collections.namedtuple('Edge', ['run', 'timestamp', 'src', 'dst', 'via'])

def is_event_wanted(event):
    if event["type"] in ("mouseover", "mouseout"):
        return False
    if event["type"] in ("popupshown", "popuphidden"):
        return False
    if event["type"] in ("pagehide", "pageadvanced", "pagerewound"):
        return False
    if event["type"] in ("load", "unload") and event["target_id"] == "configuration":
        return False
    if event["type"] in ("click", "command") and event.get("target_tagname") in ("menuitem", "wizard", None):
        return False
    if event["type"] == "command" and event["target_tagname"] == "button":
        return False
    return True

def get_id(event):
    """
    Canonicalizes event target
    """
    if event["type"] == "start":
        return ""
    elif event["type"] in ("mouseover", "mouseout"):
        return event["value"]
    elif event["type"] == "select":
        return "%s.%s" % (event["target_id"], event.get("value", '""'))
    elif event["type"] == "progresschanged" or (event["type"] == "click" and event["target_tagname"] == "menuitem"):
        return event["value"]
    elif event["type"] == "unload" and event["target_id"] == "progress_bar":
        return "finish"
    else:
        return event["target_id"]

def parse_inst_log(f):
    records = inst.parse_records(f)
    # For now, assert that we have exactly one "start" event, in the first
    # record.
    assert len(records) > 0
    assert records[0].event["type"] == "start"
    #for record in records[1:]:
    #    assert record.event["type"] != "start"

    records = [record for record in records if is_event_wanted(record.event)]

    edges = []

    current_state = "start"
    for r in records:
        if r.event["type"] in ("pageshow", "load", "unload"):
            current_state = get_id(r.event)
            # Change previous edge to point to this new state.
            edges[-1] = edges[-1]._replace(dst=current_state)
        else:
            e = Edge(r.exec_id, r.date, current_state, current_state, ("%s %s" % (r.event["type"], get_id(r.event))).strip())
            edges.append(e)

    return edges

def quote(s):
    return '"' + re.sub(r'[\\"]', lambda m: "\\"+m.group(), s) + '"'

if __name__ == '__main__':
    _, args = getopt.gnu_getopt(sys.argv[1:], "")

    for _, f in inst.input_files(args):
        edges = parse_inst_log(f)
        print("digraph G {")
        for e in edges:
            print("\t%s -> %s [label=%s]" % (e.src, e.dst, quote(e.via)))
        print("}")