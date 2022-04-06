from blockdiag import parser, builder, drawer
import copy
import random
import sys
import os
import glob

from NodeLibrary import *

statecount = 0  # const
builder.DiagramNode.type = "pass"
builder.DiagramNode.SYNC = None
builder.DiagramNode.T = None
builder.DiagramNode.tokens = []
builder.DiagramNode.sync = []
builder.DiagramNode.req = "[]"
builder.DiagramNode.wait = "[]"
builder.DiagramNode.block = "[]"
builder.DiagramNode.count = 0
builder.DiagramNode.autoformat = 'true'
builder.DiagramNode.initial = None
builder.DiagramNode.keys = None
builder.DiagramNode.node_type = None
builder.DiagramNode.set = None
builder.DiagramNode.threshold = None
builder.DiagramNode.tokens_display = "full"
builder.DiagramNode.priority = 0
builder.DiagramNode.join_by = []
builder.DiagramNode.join = None

builder.DiagramNode.waitall = "[]"
builder.DiagramNode.at = "res"

builder.Diagram.run = None
builder.Diagram.initialization_code = ""
builder.Diagram.event_selection_mechanism = 'random'

node_types = (StartType(), SyncType(), LoopType(), PassType(), PermutationType(),
              JoinType(), WaitForSetType(), LoggerType(), WaitAll())

global _id
_id = 0


def traverse_nodes(n):
    if not hasattr(n, 'nodes'):
        yield n
    else:
        for nn in n.nodes:
            # Add nn.group = n ?
            yield from traverse_nodes(nn)


def traverse_nodes_group(n):
    if not hasattr(n, 'nodes'):
        pass
    else:
        for nn in n.nodes:
            # Add nn.group = n ?
            yield from traverse_nodes_group(nn)
            if type(nn) is NodeGroup:
                yield nn


def get_group_nodes(g):
    n = [n for n in g.nodes]
    for e in g.edges:
        if e.node2 in n:
            n.remove(e.node2)
            yield e.node2
    gr = g
    while gr is not diagram and len(nodes) != 0:
        gr = g.group
        for e in gr.edges:
            if e.node2 in n:
                n.remove(e.node2)
                yield e.node2


def setup_diagram(diagram):
    global nodes
    global nodes_group
    nodes = [n for n in traverse_nodes(diagram)]
    nodes_group = [n for n in traverse_nodes_group(diagram)]

    for n in nodes:
        n.pred = []

        for nt in node_types:
            if nt.type_string() == n.type:
                n.node_type = nt
                nt.node_manipulator(n)
                break

        if n.node_type is None:
            raise AttributeError("Unknown type '" + n.type + "'")
    for g in nodes_group:
        g.stop_group = False
        g.conn_nodes = [n for n in get_group_nodes(g)]
        g.groupStop = set(g.nodes) - set(g.conn_nodes)
        for cn in g.conn_nodes:
            if not hasattr(cn, "stop_nodes"):
                cn.stop_nodes = []
            for sn in g.groupStop:
                cn.stop_nodes.append(sn)

    build_predessessors_field(diagram)
    print_diagram(diagram, sys.argv[1])
    create_run_directory()


def build_predessessors_field(diagram):
    for e in diagram.traverse_edges():
        e.node2.pred.append((e.node1, e.label))


def print_diagram(diagram, file_name):
    draw = drawer.DiagramDraw('png', diagram, file_name + ".png")
    draw.draw()
    draw.save()


def create_run_directory():
    try:
        os.mkdir(sys.argv[1] + "_run")
    except FileExistsError:
        for f in glob.glob(sys.argv[1] + "_run/*"):
            os.remove(f)


def print_state(terminal_output=True):
    global statecount
    statecount = statecount + 1

    if terminal_output:
        print("--- State:", statecount, "---")
        for n in nodes:
            print(n.id, "-->", "tokens:", n.tokens, "sync:", n.sync)

    for n in nodes:
        n.node_type.state_visualization(n)

    print_diagram(diagram, sys.argv[1] + "_run/" + str(statecount))


def step_to_next_state(diagram):
    global _id
    tmp, changed = {}, False
    for n in nodes:
        if n not in tmp.keys():
            tmp[n] = []
            for pn, p in n.pred:
                trans = [t for t in pn.node_type.transformation(pn.tokens, pn, p)]
                if pn.group != n.group:
                    if hasattr(n, "stop_nodes"):
                        for sn in n.stop_nodes:
                            if sn not in tmp.keys():
                                tmp[sn] = []
                            for t in trans:
                                if "ID" not in t.keys():
                                    t["ID"] = _id
                                    _id += 1
                            tmp[sn].extend(trans)
                tmp[n].extend(trans)

            tmp[n].extend(n.node_type.keep(n.tokens, n))

    # for g in nodes_group:
    #     for n in g.conn_nodes:
    #         for t in n.tokens + n.sync:
    #             for sn in g.groupStop:
    #                 if t["ID"] not in [tt["ID"] for tt in (sn.tokens + sn.sync)]:
    #                     if t in n.tokens:
    #                         n.tokens.remove(t)
    #                     elif t in n.sync:
    #                         n.sync.remove(t)

    for n in nodes:
        tmp[n], n.sync = n.node_type.synchronization(tmp[n], n.sync, n)
        if n.tokens != tmp[n]:
            changed = True
        n.tokens = tmp[n]

    for g in nodes_group:
        for n in g.conn_nodes:
            for t in n.tokens + n.sync:
                for sn in g.groupStop:
                    if t["ID"] not in [tt["ID"] for tt in (sn.tokens + sn.sync)]:
                        if t in n.tokens:
                            n.tokens.remove(t)
                        elif t in n.sync:
                            n.sync.remove(t)
    return changed


class EndOfRunException(Exception):
    pass


def select_event(diagram):
    requested = [(r, n.priority)
                 for n in nodes for sync in n.sync if 'REQ' in sync for r in sync['REQ']]
    block_statements = [sync['BLOCK']
                        for n in nodes for sync in n.sync if 'BLOCK' in sync]
    candidates = [(e, p) for (e, p) in requested if not any([b(e)
                                                             for b in block_statements])]

    if diagram.event_selection_mechanism == 'random':
        pass
    elif diagram.event_selection_mechanism == 'priority':
        if len(candidates) > 0:
            p = max(candidates, key=lambda e: int(e[1]))[1]
            candidates = [e for e in candidates if e[1] == p]
    else:
        raise Exception("Illegal value of event_selection_mechanism:" +
                        diagram.event_selection_mechanism)

    if len(candidates) == 0:
        raise EndOfRunException()

    return random.choice(candidates)[0]


def wake_up_tokens(diagram, e):
    for n in nodes:
        keep = []
        for t in n.sync:
            if ("REQ" in t and e in t["REQ"]) or ("WAIT" in t and t["WAIT"](e)):
                t = copy.deepcopy(t)
                if "REQ" in t:
                    del t["REQ"]
                if "WAIT" in t:
                    del t["WAIT"]
                if "BLOCK" in t:
                    del t["BLOCK"]
                t["event"] = e
                n.tokens.append(t)
            else:
                keep.append(t)
        n.sync = keep


def run_diagram(diagram):
    setup_diagram(diagram)

    print_state()

    try:
        while True:
            while step_to_next_state(diagram):
                print_state()

            e = select_event(diagram)
            print("*** Event:", e, "***")

            wake_up_tokens(diagram, e)
    except EndOfRunException:
        pass


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(
            "Usage: python flow.py [diagram file name without the .flow extension]")
    else:
        model = parser.parse_file(sys.argv[1] + ".flow")
        diagram = builder.ScreenNodeBuilder.build(model)

        if diagram.run is None:
            run_init(diagram)
            run_diagram(diagram)
        else:
            exec(diagram.run)
