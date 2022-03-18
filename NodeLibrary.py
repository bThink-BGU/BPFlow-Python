import abc
import copy
import itertools
from collections import Counter
from itertools import permutations
from typing import *

from blockdiag.builder import *


def run_init(diagram):
    exec(diagram.initialization_code)


class NodeType(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def type_string(self) -> str:
        pass

    def node_manipulator(self, n: DiagramNode) -> None:
        n.org_label = n.label
        n.org_height = n.height
        if n.priority != 0:
            n.numbered = n.priority

    def transformation(self, tokens: Sequence[Dict], node: DiagramNode, port: str) -> Sequence[Dict]:
        return [copy.deepcopy(t) for t in tokens]

    def state_visualization(self, n: DiagramNode) -> None:
        n.label = n.org_label
        n.height = n.org_height

        if n.org_label != "":
            n.label = n.org_label + "\n-------------"

        if n.height is None:
            n.height = 80
        else:
            n.height += 20

        if n.tokens_display == 'full':
            for t in n.tokens:
                n.label += "\n" + str(t)
                n.height += 10
        elif n.tokens_display == 'count only':
            n.label += "\n" + len(n.tokens) + " tokens"
        else:
            raise Exception("Illegal value for 'tokens_display': " + n.tokens_display)

    def synchronization(self, tokens: Sequence[Dict], sync: Sequence[Dict], node: DiagramNode) -> (
    Sequence[Dict], Sequence[Dict]):
        return (tokens, [])

    def keep(self, tokens: Sequence[Dict], node: DiagramNode) -> Sequence[Dict]:
        return []


######################################################################################
class StartType(NodeType):

    def type_string(self) -> str:
        return "start"

    def node_manipulator(self, node: DiagramNode) -> None:
        node.shape = "beginpoint"
        node.label = ""

        if node.initial is None:
            node.tokens = [{}]
        else:
            node.tokens = eval(node.initial)

        super().node_manipulator(node)


######################################################################################
class SyncType(NodeType):

    def type_string(self) -> str:
        return "sync"

    def node_manipulator(self, node: DiagramNode) -> None:
        node.label = 'SYNC'
        h = 30
        if node.req != "[]":
            node.label += "\nreq:" + node.req
            h += 10
        if node.wait != "[]":
            node.label += "\nwait:" + node.wait
            h += 10
        if node.block != "[]":
            node.label += "\nblock:" + node.block
            h += 10
        if node.height is None:
            node.height = h
        node.block_text = node.block
        node.wait_text = node.block
        if node.autoformat != 'false':
            node.color = '#fcfbe3'
        super().node_manipulator(node)

    def state_visualization(self, n: DiagramNode) -> None:
        n.label = n.org_label + "\n-----------"
        n.height = 60

        if n.tokens_display == 'full' or n.tokens_display == 'full with event':
            for t in n.sync:
                t = copy.deepcopy(t)
                if "REQ" in t:
                    del t["REQ"]
                if "WAIT" in t:
                    del t["WAIT"]
                if "BLOCK" in t:
                    del t["BLOCK"]
                n.label += "\n" + str(t)
                n.height += 20
            n.height = min(400, n.height)
        elif n.tokens_display == 'count only':
            if len(n.sync) > 0:
                n.label += "\n %d tokens" % len(n.sync)
        else:
            raise Exception("Illegal value for 'tokens_display': " + n.tokens_display)

    def genF(self, l):
        return lambda e: e in l

    def synchronization(self, tokens: Sequence[Dict], sync: Sequence[Dict], node: DiagramNode) -> Sequence[Dict]:
        sync = copy.deepcopy(sync)
        for t in tokens:
            t = copy.deepcopy(t)

            if node.req != "[]":
                t['REQ'] = eval(node.req, globals(), t)

            if node.wait != "[]":
                w = eval(node.wait, globals(), t)
                t['WAIT'] = w if callable(w) else self.genF(w)

            if node.block != "[]":
                b = eval(node.block, globals(), t)
                t['BLOCK'] = b if callable(b) else self.genF(b)

            if node.tokens_display != 'full with event':
                if 'event' in t:
                    del t['event']

            sync.append(t)

        return ([], sync)


######################################################################################
class LoopType(NodeType):

    def type_string(self) -> str:
        return "loop"

    def node_manipulator(self, node: DiagramNode) -> None:
        node.label = 'LOOP'
        node.label += "\ncount:" + node.count
        super().node_manipulator(node)

    def transformation(self, tokens: Sequence[Dict], node: DiagramNode, port: str) -> Sequence[Dict]:
        nxtt = []

        for pt in tokens:
            t = copy.deepcopy(pt)

            try:
                t["COUNT"] = t["COUNT"] - 1
            except KeyError:
                t["COUNT"] = int(node.count)

            if port == 'after':
                if t["COUNT"] == 0:
                    nxtt.append(t)
            else:
                if t["COUNT"] != 0:
                    nxtt.append(t)

        return nxtt


######################################################################################
class PassType(NodeType):

    def type_string(self) -> str:
        return "pass"

    def transformation(self, tokens: Sequence[Dict], node: DiagramNode, port: str) -> Sequence[Dict]:
        return [copy.deepcopy(t) for t in tokens]


######################################################################################
class PermutationType(NodeType):

    def type_string(self) -> str:
        return "permutation"

    def node_manipulator(self, node: DiagramNode) -> None:
        node.label = 'PERMUTATION'
        node.label += "\nkeys:" + node.keys
        super().node_manipulator(node)

    def transformation(self, tokens: Sequence[Dict], node: DiagramNode, port: str) -> Sequence[Dict]:
        ret = []

        for t in tokens:
            keys = eval(node.keys, globals(), t)
            values = [t[k] for k in keys]
            pvalues = permutations(values)

            for pval in pvalues:
                t = copy.deepcopy(t)
                for k in range(len(pval)):
                    t[keys[k]] = pval[k]
                ret.append(t)

        return ret


######################################################################################
class JoinType(NodeType):

    def type_string(self) -> str:
        return "join"

    def node_manipulator(self, node: DiagramNode) -> None:
        node.label = 'JOIN\nCOUNT=%s' % node.count
        node.log = []
        super().node_manipulator(node)

    def state_visualization(self, n: DiagramNode) -> None:
        n.label = n.org_label
        n.height = 50

        n.label += "\n---------------------"
        for t in n.log:
            n.label += "\n" + str(t)
            n.height += 20

    def get_groups(self, node: DiagramNode):
        ret = []

        join_by = eval(node.join_by)

        def joinby(t):
            return [t[i] for i in join_by]

        node.log.sort(key=joinby)

        join = None
        for t in node.log:
            if joinby(t) != join:
                join = joinby(t)
                group = [t]
            else:
                group.append(t)
                if (len(group) >= eval(node.count)):
                    ret.append(group)

        return ret

    def synchronization(self, tokens: Sequence[Dict], sync: Sequence[Dict], node: DiagramNode) -> (
    Sequence[Dict], Sequence[Dict]):
        if len(tokens) != 0:
            node.log.extend(tokens)

        return (tokens, [])

    #   TODO change this node to work like WaitForSetType - i.e., without using transformation.
    def transformation(self, tokens: Sequence[Dict], node: DiagramNode, port: str) -> Sequence[Dict]:
        groups = self.get_groups(node)
        if len(groups) != 0:
            for g in groups:
                for t in g:
                    node.log.remove(t)

            if node.join is None:
                return [{'group': g} for g in groups]
            else:
                return [eval(node.join)(g) for g in groups]

        return []


######################################################################################
class WaitForSetType(NodeType):

    def type_string(self) -> str:
        return "waitforset"

    def node_manipulator(self, node: DiagramNode) -> None:
        node.label = "ANY " + node.threshold + " OF \n" + node.set
        node.set = eval(node.set)
        node.visited = []
        node.threshold = int(node.threshold)
        # node.width = 400
        node.height = 100
        super().node_manipulator(node)

    def state_visualization(self, n: DiagramNode) -> None:
        n.label = n.org_label
        n.height = 80

        n.label += "\n---------------------"
        n.label += "\nhistory=" + str(n.visited)
        for t in n.tokens:
            n.label += "\n" + str(t)
            n.height += 10

    def transformation(self, tokens: Sequence[Dict], node: DiagramNode, port: str) -> Sequence[Dict]:
        node.visited += [t for t in tokens if t in node.set and t not in node.visited]

        if len(node.visited) >= node.threshold:
            tmp = node.visited
            node.visited = []
            return [{'subset': tmp}]
        else:
            return []


######################################################################################
class WaitAll(NodeType):

    def type_string(self) -> str:
        return "waitall"

    def node_manipulator(self, node: DiagramNode) -> None:
        node.label = "WAIT All  OF\n" + node.waitall + ("\n at " + node.at if node.at is not None else "")
        node.width = 400
        node.height = 50
        super().node_manipulator(node)

    def state_visualization(self, n: DiagramNode) -> None:
        n.label = n.org_label + "\n"
        n.height = 50
        if n.tokens_display == 'full' or n.tokens_display == 'full with event':
            for t in n.sync:
                t = copy.deepcopy(t)
                del t["WAIT"]
                n.label += f"{t}\n"
                n.height += 20

            n.label += "-----------\n"

            for t in n.tokens:
                # t = copy.deepcopy(t)
                # del t["WAIT"]
                n.label += f"{t}\n"
                n.height += 20

        elif n.tokens_display == 'count only':
            if len(n.tokens) > 0:
                n.label += "\n %d tokens" % len(n.tokens)
        else:
            raise Exception("Illegal value for 'tokens_display': " + n.tokens_display)

    def genF(self, l):
        return lambda e: True in [e in le for le in l]

    def synchronization(self, tokens: Sequence[Dict], sync: Sequence[Dict], node: DiagramNode) -> Sequence[Dict]:
        sync = copy.deepcopy(sync)
        finished = []
        for t in tokens:
            t = copy.deepcopy(t)

            if "WAITALL" not in t.keys():
                tmp = eval(node.waitall, globals(), t)
                if type(tmp) is dict:
                    k =list(tmp.keys())
                    t['WAITALL'] = [tmp[k] for k in k]
                    t['WAITALLNAMES'] = k
                else :
                  t['WAITALL'] = tmp

            if "event" in t.keys():
                e = t["event"]
                for waitlist in t["WAITALL"]:
                    if e in waitlist:
                        waitlist.remove(e)
                del t["event"]

            if [] in t['WAITALL']:
                finished.append(t)
            else:
                l = copy.deepcopy(t['WAITALL'])
                print(f'l={l}')
                t['WAIT'] = self.genF(l)  # need to be the union
                sync.append(t)

        return (finished, sync)

    def transformation(self, tokens: Sequence[Dict], node: DiagramNode, port: str) -> Sequence[Dict]:
        nxt = []

        for t in tokens:
            if [] in t["WAITALL"]:
                if "WAITALLNAMES" in t.keys():
                    t[node.at] = t["WAITALLNAMES"][t["WAITALL"].index([])]
                    del t["WAITALLNAMES"]
                del t["WAITALL"]
                nxt.append(copy.deepcopy(t))

        return nxt

    def keep(self, tokens: Sequence[Dict], node: DiagramNode) -> Sequence[Dict]:
        return [t for t in tokens if [] not in t['WAITALL']]


######################################################################################
class LoggerType(NodeType):

    def type_string(self) -> str:
        return "logger"

    def node_manipulator(self, node: DiagramNode) -> None:
        node.label = 'LOG'
        node.loog = []
        super().node_manipulator(node)

    def state_visualization(self, n: DiagramNode) -> None:
        n.label = n.org_label
        n.height = 100

        n.label += "\n---------------------"
        for t in n.loog:
            n.label += "\n" + str(t)
            n.height += 10

    def synchronization(self, tokens: Sequence[Dict], sync: Sequence[Dict], node: DiagramNode) -> (
    Sequence[Dict], Sequence[Dict]):
        if len(tokens) != 0:
            node.loog += tokens

        return (tokens, [])
