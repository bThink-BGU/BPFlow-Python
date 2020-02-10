from blockdiag import parser, builder, drawer
import copy, random, sys, os, glob

from NodeLibrary import *

statecount = 0
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

builder.Diagram.initialization_code = None

node_types = (StartType(), SyncType(), LoopType(), PassType(), PermutationType(), JoinType(), WaitForSetType(), LoggerType())

def setup_diagram(diagram):
  for n in diagram.nodes:
    n.pred = []
    
    for nt in node_types:
      if nt.type_string() == n.type:
        n.node_type = nt
        nt.node_manipulator(n)
    
    if n.node_type is None:
      raise AttributeError("Unknown type '" + n.type + "'")
  
  build_predessessors_field(diagram)
  print_diagram(diagram, sys.argv[1])
  create_run_directory()


def build_predessessors_field(diagram):
  for e in diagram.edges:
    e.node2.pred.append((e.node1, e.label))


def print_diagram(diagram, file_name):
  draw = drawer.DiagramDraw('PNG', diagram, file_name + ".png")
  draw.draw()
  draw.save()


def create_run_directory():
  try:
    os.mkdir(sys.argv[1] + "_run")
  except FileExistsError:
    for f in glob.glob(sys.argv[1] + "_run/*"):
      os.remove(f)


def print_state():
  global statecount
  statecount = statecount + 1
  
  print("--- State:", statecount, "---")
  for n in diagram.nodes:
    print(n.id, "-->", "tokens:", n.tokens, "sync:", n.sync)
  
  for n in diagram.nodes:
    n.node_type.state_visualization(n)
  
  print_diagram(diagram, sys.argv[1] + "_run/" + str(statecount))


def step_to_next_state(diagram):
  tmp, changed = {}, False
  for n in diagram.nodes:
    tmp[n] = [t for pn, p in n.pred for t in pn.node_type.transformation(pn.tokens, pn, p)]
  
  for n in diagram.nodes:
    tmp[n], n.sync = n.node_type.synchronization(tmp[n], n.sync, n)
    if n.tokens != tmp[n]: changed = True
    n.tokens = tmp[n]
  
  return changed


def select_event(diagram):
  requested = [r for n in diagram.nodes for sync in n.sync if 'REQ' in sync for r in sync['REQ']]
  block_statements = [sync['BLOCK'] for n in diagram.nodes for sync in n.sync if 'BLOCK' in sync]
  candidates = [e for e in requested if not any([b(e) for b in block_statements])]
  e = random.choice(candidates)
  return e


def wake_up_tokens(diagram, e):
  for n in diagram.traverse_nodes():
    keep = []
    for t in n.sync:
      if ("REQ" in t and e in t["REQ"]) or ("WAIT" in t and t["WAIT"](e)):
        t = copy.deepcopy(t)
        if "REQ" in t: del t["REQ"]
        if "WAIT" in t: del t["WAIT"]
        if "BLOCK" in t: del t["BLOCK"]
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
      while step_to_next_state(diagram): print_state()
      
      e = select_event(diagram)
      print("********************** Event:", e, "***************************")
      
      wake_up_tokens(diagram, e)
  except IndexError:
    pass

if __name__ == "__main__":
  if len(sys.argv) != 2:
    print("Usage: python flow.py [diagram file name without the .flow extension]")
  else:
    model = parser.parse_file(sys.argv[1] + ".flow")
    diagram = builder.ScreenNodeBuilder.build(model)
    run_init(diagram)
    run_diagram(diagram)
