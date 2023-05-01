#!/usr/bin/env python3

import pathlib
import shutil
import sys, inspect, subprocess
import os
import argparse
import copy
import random
import time
from datetime import datetime
from dataclasses import dataclass, field
from pathlib import Path

import tomli
from pyverilog.vparser.parser import parse, NodeNumbering
from pyverilog.ast_code_generator.codegen import ASTCodeGenerator
from pyverilog.vparser.plyparser import ParseError
import pyverilog.vparser.ast as vast

import fitness

AST_CLASSES = []

for name, obj in inspect.getmembers(vast):
    if inspect.isclass(obj):
        AST_CLASSES.append(obj)

REPLACE_TARGETS = {}  # dict from class to list of classes that are okay to substituite for the original class
for i in range(len(AST_CLASSES)):
    REPLACE_TARGETS[AST_CLASSES[i]] = []
    REPLACE_TARGETS[AST_CLASSES[i]].append(AST_CLASSES[i])  # can always replace with a node of the same type
    for j in range(len(AST_CLASSES)):
        # get the immediate parent classes of both classes, and if the parent if not Node, the two classes can be swapped
        if i != j and inspect.getmro(AST_CLASSES[i])[1] == inspect.getmro(AST_CLASSES[j])[1] and \
                inspect.getmro(AST_CLASSES[j])[1] != vast.Node:
            REPLACE_TARGETS[AST_CLASSES[i]].append(AST_CLASSES[j])

"""
Valid targets for the delete and insert operators.
"""
DELETE_TARGETS = ["IfStatement", "NonblockingSubstitution", "BlockingSubstitution", "ForStatement", "Always", "Case",
                  "CaseStatement", "DelayStatement", "Localparam", "Assign", "Block"]
INSERT_TARGETS = ["IfStatement", "NonblockingSubstitution", "BlockingSubstitution", "ForStatement", "Always", "Case",
                  "CaseStatement", "DelayStatement", "Localparam", "Assign"]

TEMPLATE_MUTATIONS = {"increment_by_one": ("Identifier", "Plus"), "decrement_by_one": ("Identifier", "Minus"),
                      "negate_equality": ("Eq", "NotEq"), "negate_inequality": ("NotEq", "Eq"),
                      "negate_ulnot": ("Ulnot", "Ulnot"),
                      "sens_to_negedge": ("Sens", "Sens"), "sens_to_posedge": ("Sens", "Sens"),
                      "sens_to_level": ("Sens", "Sens"), "sens_to_all": ("Sens", "Sens"),
                      "blocking_to_nonblocking": ("BlockingSubstitution", "NonblockingSubstitution"),
                      "nonblocking_to_blocking": ("NonblockingSubstitution", "BlockingSubstitution")}

_script_dir = pathlib.Path(__file__).parent.resolve()
# add root dir in order to be able to load "benchmarks" module
sys.path.append(str(_script_dir.parent.parent))
import benchmarks

# global cache
GENOME_FITNESS_CACHE = {}
FITNESS_EVAL_TIMES = []


@dataclass
class Benchmark:
    src_file: Path
    output: str
    project_dir: Path
    oracle: Path
    timeout: float
    verilog_files: list = field(default_factory=list)


def parse_path(base: Path, path: str) -> Path:
    if os.path.isabs(path):
        return Path(path)
    else:
        return base / path


def load_benchmark(project_path: Path, bug_name: str, testbench_name: str):
    project = benchmarks.load_project(project_path)
    benchmark = benchmarks.get_benchmark(project, bug_name, testbench_name, use_trace_testbench=False)

    # it is important for the testbench sources to come first as they might have a timescale
    other_sources = benchmarks.get_other_sources(benchmark)
    assert isinstance(benchmark.testbench, benchmarks.VerilogOracleTestbench)
    verilog_files = benchmark.testbench.sources + other_sources + [benchmark.bug.buggy]

    # translate from our common benchmarks.Benchmark format to the local cirfix benchmark format
    bb = Benchmark(
        src_file=benchmark.bug.buggy,
        output=benchmark.testbench.output,
        project_dir=benchmark.design.directory,
        oracle=benchmark.testbench.oracle,
        timeout=benchmark.testbench.timeout,
        verilog_files=verilog_files
    )
    return bb, benchmark.bug.original


def validate_benchmark(benchmark: Benchmark):
    assert benchmark.src_file.exists(), f"{benchmark.src_file} does not exist"
    assert benchmark.project_dir.exists(), f"{benchmark.project_dir} does not exist"
    assert benchmark.oracle.exists(), f"{benchmark.oracle} does not exist"
    for ff in benchmark.verilog_files:
        assert ff.exists(), f"{ff} does not exist"


@dataclass
class Config:
    working_dir: Path
    benchmark: Benchmark
    gens: int = 5
    popsize: int = 200
    restarts: int = 1
    fault_loc: bool = True
    control_flow: bool = True
    limit_transitive_dependency_set: bool = False
    dependency_set_max: int = 5
    replacement_rate: float = 1 / 3
    deletion_rate: float = 1 / 3
    insertions_rate: float = 1 / 3
    mutation_rate: float = 1 / 2
    crossover_rate: float = 1 / 2
    fitness_mode: str = "outputwires"
    simulator: str = "vcs"
    verbose: bool = False
    simulator_compile_timeout: float = 60 * 2 # 2 minute timeout by default


def load_config(filename: Path, working_dir: Path, benchmark: Benchmark, sim: str, simulator_compile_timeout: float) -> Config:
    with open(filename, 'rb') as ff:
        dd = tomli.load(ff)
    conf = Config(
        working_dir=working_dir,
        benchmark=benchmark
    )
    if "fitness_mode" in dd:
        conf.fitness_mode = dd["fitness_mode"]
    if "gens" in dd:
        conf.gens = int(dd["gens"])
    if "popsize" in dd:
        conf.popsize = int(dd["popsize"])
    if "mutation_rate" in dd:
        conf.mutation_rate = float(dd["mutation_rate"])
    if "crossover_rate" in dd:
        conf.crossover_rate = float(dd["crossover_rate"])
    if "deletion_rate" in dd:
        conf.deletion_rate = float(dd["deletion_rate"])
    if "insertion_rate" in dd:
        conf.insertion_rate = float(dd["insertion_rate"])
    if "replacement_rate" in dd:
        conf.replacement_rate = float(dd["replacement_rate"])
    if "restarts" in dd:
        conf.restarts = int(dd["restarts"])
    if "fault_loc" in dd:
        conf.fault_loc = bool(dd["fault_loc"])
    if "control_flow" in dd:
        conf.control_flow = bool(dd["control_flow"])
    if "limit_transitive_dependency_set" in dd:
        conf.limit_transitive_dependency_set = bool(dd["limit_transitive_dependency_set"])
    if "dependency_set_max" in dd:
        conf.dependency_set_max = int(dd["dependency_set_max"])
    conf.simulator = sim
    conf.simulator_compile_timeout = simulator_compile_timeout
    return conf


def validate_config(conf: Config):
    assert conf.fitness_mode in ["outputwires", "testcases"], f"invalid fitness mode: {conf.fitness_mode}"
    if conf.fitness_mode == "testcases" and conf.fault_loc:
        print("WARNING: Cannot use fault localization unless output wires are being used for fitness metrics." +
              "Turning off fault localization.")
        time.sleep(1)
        conf.fault_loc = False
    mutation_op_rate = conf.replacement_rate + conf.insertions_rate + conf.deletion_rate
    assert abs(mutation_op_rate - 1) < 0.05, \
        f"ERROR: The mutation operator rates should add up to 1. (is {mutation_op_rate})"
    assert abs(conf.crossover_rate + conf.mutation_rate - 1) < 0.05, \
        "ERROR: The mutation operator and crossover rates should add up to 1."
    validate_benchmark(conf.benchmark)


TIME_NOW = datetime.today().strftime('%Y-%m-%d-%H:%M:%S')

# global seed
SEED = "repair_%s" % TIME_NOW
SEED_CTR = 0


def inc_seed():
    global SEED_CTR
    SEED_CTR += 1
    return SEED + str(SEED_CTR)


class MutationOp(ASTCodeGenerator):

    def __init__(self, popsize, fault_loc, control_flow, limit_transitive_dependency_set: bool, dependency_set_max: int,
                 verbose: bool):
        super().__init__()
        self.numbering = NodeNumbering()
        self.popsize = popsize
        self.fault_loc = fault_loc
        self.control_flow = control_flow
        self.limit_transitive_dependency_set = limit_transitive_dependency_set
        self.dependency_set_max = dependency_set_max
        self.verbose = verbose
        # temporary variables used for storing data for the mutation operators
        self.fault_loc_set = set()
        self.new_vars_in_fault_loc = dict()
        self.wires_brought_in = dict()
        self.implicated_lines = set()  # contains the line number implicated by FL
        # self.blacklist = set()
        self.tmp_node = None
        self.deletable_nodes = []
        self.insertable_nodes = []
        self.replaceable_nodes = []
        self.node_class_to_replace = None
        self.nodes_by_class = []
        self.stmt_nodes = []
        self.max_node_id = -1

    """ 
    Replaces the node corresponding to old_node_id with new_node.
    """

    def replace_with_node(self, ast, old_node_id, new_node):
        attr = vars(ast)
        for key in attr:  # loop through all attributes of this AST
            if attr[key].__class__ in AST_CLASSES:  # for each attribute that is also an AST
                if attr[key].node_id == old_node_id:
                    attr[key] = copy.deepcopy(new_node)
                    return
            elif attr[key].__class__ in [list, tuple]:  # for attributes that are lists or tuples
                for i in range(len(attr[key])):  # loop through each AST in that list or tuple
                    tmp = attr[key][i]
                    if tmp.__class__ in AST_CLASSES and tmp.node_id == old_node_id:
                        attr[key][i] = copy.deepcopy(new_node)
                        return

        for c in ast.children():
            if c: self.replace_with_node(c, old_node_id, new_node)

    """
    Deletes the node with the node_id provided, if such a node exists.
    """

    def delete_node(self, ast, node_id):
        attr = vars(ast)
        for key in attr:  # loop through all attributes of this AST
            if attr[key].__class__ in AST_CLASSES:  # for each attribute that is also an AST
                if attr[key].node_id == node_id and attr[key].__class__.__name__ in DELETE_TARGETS:
                    attr[key] = None
            elif attr[key].__class__ in [list, tuple]:  # for attributes that are lists or tuples
                for i in range(len(attr[key])):  # loop through each AST in that list or tuple
                    tmp = attr[key][i]
                    if tmp.__class__ in AST_CLASSES and tmp.node_id == node_id and tmp.__class__.__name__ in DELETE_TARGETS:
                        attr[key][i] = None

        for c in ast.children():
            if c: self.delete_node(c, node_id)

    """
    Inserts node with node_id after node with after_id.
    """

    def insert_stmt_node(self, ast, node, after_id):
        if ast.__class__.__name__ == "Block":
            if after_id == ast.node_id:
                # node.show()
                # input("...")
                ast.statements.insert(0, copy.deepcopy(node))
                return
            else:
                insert_point = -1
                for i in range(len(ast.statements)):
                    stmt = ast.statements[i]
                    if stmt and stmt.node_id == after_id:
                        insert_point = i + 1
                        break
                if insert_point != -1:
                    # print(ast.statements)
                    ast.statements.insert(insert_point, copy.deepcopy(node))
                    # print(ast.statements)
                    return

        for c in ast.children():
            if c: self.insert_stmt_node(c, node, after_id)

    """
    Gets the node matching the node_id provided, if one exists, by storing it in the temporary node variable.
    Used by the insert and replace operators.
    """

    def get_node_from_ast(self, ast, node_id):
        if ast.node_id == node_id:
            self.tmp_node = ast

        for c in ast.children():
            if c: self.get_node_from_ast(c, node_id)

    """ 
    Gets all the line numbers for the code implicated by the FL.
    """

    def collect_lines_for_fl(self, ast):
        if ast.node_id in self.fault_loc_set:
            self.implicated_lines.add(ast.lineno)

        for c in ast.children():
            if c: self.collect_lines_for_fl(c)

    """
    Gets a list of all nodes that can be deleted.
    """

    def get_deletable_nodes(self, ast):
        # with fault localization, make sure that any node being deleted is also in DELETE_TARGETS 
        if self.fault_loc and len(self.fault_loc_set) > 0:
            if ast.node_id in self.fault_loc_set and ast.__class__.__name__ in DELETE_TARGETS:
                self.deletable_nodes.append(ast.node_id)
        else:
            if ast.__class__.__name__ in DELETE_TARGETS:
                self.deletable_nodes.append(ast.node_id)

        for c in ast.children():
            if c: self.get_deletable_nodes(c)

    """
    Gets a list of all nodes that can be inserted into to a begin ... end block.
    """

    def get_insertable_nodes(self, ast):
        # with fault localization, make sure that any node being used is also in INSERT_TARGETS
        # (to avoid inserting, e.g., overflow+1 into a block statement)
        if self.fault_loc and len(self.fault_loc_set) > 0:
            if ast.node_id in self.fault_loc_set and ast.__class__.__name__ in INSERT_TARGETS:
                self.insertable_nodes.append(ast.node_id)
        else:
            if ast.__class__.__name__ in INSERT_TARGETS:
                self.insertable_nodes.append(ast.node_id)

        for c in ast.children():
            if c: self.get_insertable_nodes(c)

    """
    Gets the class of the node being replaced in a replace operation. 
    This class is used to find potential sources for the replacement.
    """

    def get_node_to_replace_class(self, ast, node_id):
        if ast.node_id == node_id:
            self.node_class_to_replace = ast.__class__

        for c in ast.children():
            if c: self.get_node_to_replace_class(c, node_id)

    """
    Gets all nodes that compatible to be replaced with a node of the given class type. 
    These nodes are potential sources for replace operations.
    """

    def get_replaceable_nodes_by_class(self, ast, node_type):
        if ast.__class__ in REPLACE_TARGETS[node_type]:
            self.replaceable_nodes.append(ast.node_id)

        for c in ast.children():
            if c: self.get_replaceable_nodes_by_class(c, node_type)

    """
    Gets all nodes that are of the given class type. 
    These nodes are used for applying mutation templates.
    """

    # TODO: do this only for fault loc set?
    def get_nodes_by_class(self, ast, node_type):
        if ast.__class__.__name__ == node_type:
            self.nodes_by_class.append(ast.node_id)

        for c in ast.children():
            if c: self.get_nodes_by_class(c, node_type)

    """
    Gets all nodes that are found within a begin ... end block. 
    These nodes are potential destinations for insert operations.
    """

    def get_nodes_in_block_stmt(self, ast):
        if ast.__class__.__name__ == "Block":
            if len(ast.statements) == 0:  # if empty block, return the node id for the block (so that a node can be inserted into the empty block)
                self.stmt_nodes.append(ast.node_id)
            else:
                for c in ast.statements:
                    if c: self.stmt_nodes.append(c.node_id)

        for c in ast.children():
            if c: self.get_nodes_in_block_stmt(c)

    """
    Control dependency analysis of the given program branch.
    """

    def analyze_program_branch(self, ast, cond_list, mismatch_set, uniq_headers):
        if ast:
            if ast.__class__.__name__ == "Identifier" and (
                    ast.name in mismatch_set or ast.name in tuple(self.new_vars_in_fault_loc.values())):
                for cond in cond_list:
                    if cond: self.add_node_and_children_to_fault_loc(cond, mismatch_set, uniq_headers, ast)

            for c in ast.children():
                self.analyze_program_branch(c, cond_list, mismatch_set, uniq_headers)

    """
    Add node and its immediate children to the fault loc set.    
    """

    def add_node_and_children_to_fault_loc(self, ast, mismatch_set, uniq_headers, parent=None):
        # if ast.__class__.__name__ == "Identifier" and ast.name in self.blacklist: return
        self.fault_loc_set.add(ast.node_id)
        if parent and parent.__class__.__name__ == "Identifier" and parent.name not in self.wires_brought_in:
            self.wires_brought_in[parent.name] = set()
        if ast.__class__.__name__ == "Identifier" and ast.name not in mismatch_set and ast.name not in uniq_headers:  # and ast.name not in self.blacklist:
            if not self.limit_transitive_dependency_set or len(self.wires_brought_in[parent.name]) < self.dependency_set_max:
                self.wires_brought_in[parent.name].add(ast.name)
                self.new_vars_in_fault_loc[ast.node_id] = ast.name
            # else:
            #     self.blacklist.add(ast.name)
        for c in ast.children():
            if c:
                self.fault_loc_set.add(c.node_id)
                # add all children identifiers to depedency set
                if c.__class__.__name__ == "Identifier" and c.name not in mismatch_set and c.name not in uniq_headers:  # and c.name not in self.blacklist:
                    if not self.limit_transitive_dependency_set or len(
                            self.wires_brought_in[parent.name]) < self.dependency_set_max:
                        self.wires_brought_in[parent.name].add(c.name)
                        self.new_vars_in_fault_loc[c.node_id] = c.name
                    # else:
                    #     self.blacklist.add(c.name)

    """
    Given a set of output wires that mismatch with the oracle, get a list of node IDs that are potential fault localization targets.
    """

    # TODO: add decl to fault loc targets?
    def get_fault_loc_targets(self, ast, mismatch_set, uniq_headers, parent=None, include_all_subnodes=False):
        # data dependency analysis
        # if ast.__class__.__name__ == "Identifier" and ast.name in self.blacklist: return
        if ast.__class__.__name__ in ["BlockingSubstitution", "NonblockingSubstitution",
                                      "Assign"]:  # for assignment statements =, <=
            if ast.left and ast.left.__class__.__name__ == "Lvalue" and ast.left.var:
                if ast.left.var.__class__.__name__ == "Identifier" and ast.left.var.name in mismatch_set:  # single assignment
                    include_all_subnodes = True
                    parent = ast.left.var
                    if parent and not parent.name in self.wires_brought_in: self.wires_brought_in[parent.name] = set()
                    self.add_node_and_children_to_fault_loc(ast, mismatch_set, uniq_headers, parent)
                elif ast.left.var.__class__.__name__ == "LConcat":  # l-concat / multiple assignments
                    for v in ast.left.var.list:
                        if v.__class__.__name__ == "Identifier" and v.name in mismatch_set:
                            if not v.name in self.wires_brought_in: self.wires_brought_in[v.name] = set()
                            include_all_subnodes = True
                            parent = v
                            self.add_node_and_children_to_fault_loc(ast, mismatch_set, uniq_headers, parent)

        # control dependency analysis        
        elif self.control_flow and ast.__class__.__name__ == "IfStatement":
            self.analyze_program_branch(ast.true_statement, [ast.cond], mismatch_set, uniq_headers)
            self.analyze_program_branch(ast.false_statement, [ast.cond], mismatch_set, uniq_headers)
        elif self.control_flow and ast.__class__.__name__ == "CaseStatement":
            for c in ast.caselist:
                if c:
                    cond_list = [ast.comp]
                    if c.cond:
                        for tmp_var in c.cond: cond_list.append(tmp_var)
                    self.analyze_program_branch(c.statement, cond_list, mismatch_set, uniq_headers)
        elif self.control_flow and ast.__class__.__name__ == "ForStatement":
            cond_list = []
            if ast.pre: cond_list.append(ast.pre)
            if ast.cond: cond_list.append(ast.cond)
            if ast.post: cond_list.append(ast.post)
            self.analyze_program_branch(ast.statement, cond_list, mismatch_set, uniq_headers)

        if include_all_subnodes:  # recurisvely ensure all children of a fault loc target are also included in the fault loc set
            self.fault_loc_set.add(ast.node_id)
            if ast.__class__.__name__ == "Identifier" and ast.name not in mismatch_set and ast.name not in uniq_headers:  # and ast.name not in self.blacklist:
                if parent and parent.__class__.__name__ == "Identifier":
                    if not self.limit_transitive_dependency_set or len(
                            self.wires_brought_in[parent.name]) < self.dependency_set_max:
                        self.wires_brought_in[parent.name].add(ast.name)
                        self.new_vars_in_fault_loc[ast.node_id] = ast.name
                    # else:
                    #     self.blacklist.add(ast.name)

        for c in ast.children():
            if c:
                self.get_fault_loc_targets(c, mismatch_set, uniq_headers, parent, include_all_subnodes)

        # TODO: for sdram_controller, control_flow + limit gives smaller fl set than no control_flow + limit. why? is this a bug?

    """
    The delete, insert, and replace operators to be called from outside the class.
    Note: node_id, with_id, and after_id would not be none if we are trying to regenerate AST from patch list, and would be none for a random mutation.
    """

    def delete(self, ast, patch_list, node_id=None):
        self.deletable_nodes = []  # reset deletable nodes for the next delete operation, in case previous delete returned early

        if node_id == None:
            self.get_deletable_nodes(ast)  # get all nodes that can be deleted without breaking the AST / syntax
            if len(self.deletable_nodes) == 0:  # if no nodes can be deleted, return without attepmting delete
                print("Delete operation not possible. Returning with no-op.")
                return patch_list, ast

            random.seed(inc_seed())
            node_id = random.choice(self.deletable_nodes)  # choose a random node_id to delete
            print("Deleting node with id %s\n" % node_id)

        self.delete_node(ast, node_id)  # delete the node corresponding to node_id
        self.numbering.renumber(ast)  # renumber nodes
        self.max_node_id = self.numbering.c  # reset max_node_id
        self.numbering.c = -1
        self.deletable_nodes = []  # reset deletable nodes for the next delete operation

        child_patchlist = copy.deepcopy(patch_list)
        child_patchlist.append("delete(%s)" % node_id)  # update patch list

        return child_patchlist, ast

    def insert(self, ast, patch_list, node_id=None, after_id=None):
        self.insertable_nodes = []  # reset the temporary variables, in case previous insert returned early
        self.tmp_node = None

        if node_id == None and after_id == None:
            self.get_insertable_nodes(
                ast)  # get all nodes with a type that is suited to insertion in block statements -> src
            self.get_nodes_in_block_stmt(ast)  # get all nodes within a block statement -> dest
            if len(self.insertable_nodes) == 0 or len(
                    self.stmt_nodes) == 0:  # if no insertable nodes exist, exit gracefully
                print("Insert operation not possible. Returning with no-op.")
                return patch_list, ast
            random.seed(inc_seed())
            after_id = random.choice(self.stmt_nodes)  # choose a random src and dest
            random.seed(inc_seed())
            node_id = random.choice(self.insertable_nodes)
            print("Inserting node with id %s after node with id %s\n" % (node_id, after_id))
        self.get_node_from_ast(ast, node_id)  # get the node associated with the src node id
        self.insert_stmt_node(ast, self.tmp_node, after_id)  # perform the insertion
        self.numbering.renumber(ast)  # renumber nodes
        self.max_node_id = self.numbering.c  # reset max_node_id
        self.numbering.c = -1

        child_patchlist = copy.deepcopy(patch_list)
        child_patchlist.append("insert(%s,%s)" % (node_id, after_id))  # update patch list

        return child_patchlist, ast

    def replace(self, ast, patch_list, node_id=None, with_id=None):
        self.tmp_node = None  # reset the temporary variables (in case previous replace returned sooner)
        self.replaceable_nodes = []
        self.node_class_to_replace = None

        if node_id == None:
            if self.max_node_id == -1:  # if max_id is not know yet, traverse the AST to find the number of nodes -- needed to pick a random id to replace
                self.numbering.renumber(ast)
                self.max_node_id = self.numbering.c
                self.numbering.c = -1  # reset the counter for numbering
            if self.fault_loc and len(self.fault_loc_set) > 0:
                random.seed(inc_seed())
                node_id = random.choice(
                    tuple(self.fault_loc_set))  # get a fault loc target if fault localization is being used
            else:
                random.seed(inc_seed())
                node_id = random.randint(0, self.max_node_id)  # get random node id to replace
            print("Node to replace id: %s" % node_id)

        self.get_node_to_replace_class(ast, node_id)  # get the class of the node associated with the random node id
        print("Node to replace class: %s" % self.node_class_to_replace)
        if self.node_class_to_replace == None:  # if the node does not exist, return with no-op
            return patch_list, ast

        if with_id == None:
            self.get_replaceable_nodes_by_class(ast,
                                                self.node_class_to_replace)  # get all valid nodes that have a class that could be substituted for the original node's class
            if len(self.replaceable_nodes) == 0:  # if no replaceable nodes exist, exit gracefully
                print("Replace operation not possible. Returning with no-op.")
                return patch_list, ast
            print("Replaceable nodes: %s" % str(self.replaceable_nodes))
            random.seed(inc_seed())
            with_id = random.choice(self.replaceable_nodes)  # get a random node id from the replaceable nodes
            print("Replacing node id %s with node id %s" % (node_id, with_id))

        self.get_node_from_ast(ast, with_id)  # get the node associated with with_id

        # safety guard: this could happen if crossover makes the GA think a node is actually suitable for replacement when in reality it is not....    
        if self.tmp_node.__class__ not in REPLACE_TARGETS[self.node_class_to_replace]:
            print(self.tmp_node.__class__)
            print(REPLACE_TARGETS[self.node_class_to_replace])
            return patch_list, ast

        self.replace_with_node(ast, node_id, self.tmp_node)  # perform the replacement
        self.tmp_node = None  # reset the temporary variables
        self.replaceable_nodes = []
        self.node_class_to_replace = None
        self.numbering.renumber(ast)  # renumber nodes
        self.max_node_id = self.numbering.c  # update max_node_id
        self.numbering.c = -1

        child_patchlist = copy.deepcopy(patch_list)
        child_patchlist.append("replace(%s,%s)" % (node_id, with_id))  # update patch list

        return child_patchlist, ast

    def weighted_template_choice(self, templates):
        random.seed(inc_seed())
        p = random.random()
        if p <= 0.3:
            random.seed(inc_seed())
            return random.choice(["increment_by_one", "decrement_by_one"])
        elif p <= 0.6:
            random.seed(inc_seed())
            return random.choice(["negate_equality", "negate_inequality", "negate_ulnot"])
        elif p <= 0.8:
            random.seed(inc_seed())
            return random.choice(["nonblocking_to_blocking", "blocking_to_nonblocking"])
        else:
            random.seed(inc_seed())
            return random.choice(["sens_to_negedge", "sens_to_posedge", "sens_to_level", "sens_to_all"])

    # TODO: make sure ast is a deepcopy
    def apply_template(self, ast, patch_list, template=None, node_id=None):
        self.tmp_node = None  # reset the temporary variables, in case the previous template operator returned early
        self.nodes_by_class = []

        if template == None:
            template = self.weighted_template_choice(list(TEMPLATE_MUTATIONS.keys()))
            node_type = TEMPLATE_MUTATIONS[template][0]
            # print(template)
            # print(node_type)
            self.get_nodes_by_class(ast, node_type)
            # print(self.nodes_by_class)
            if len(self.nodes_by_class) == 0:
                print("\nTemplate %s cannot be applied to AST. Returning with no-op." % template)
                return patch_list, ast  # no-op
            random.seed(inc_seed())
            node_id = random.choice(self.nodes_by_class)
            # print(node_id)

        self.get_node_from_ast(ast, node_id)

        # safety guards: the following can be caused by crossover operations splitting a patchlist
        if self.tmp_node is None:
            print("Node with id %d does not exist. Returning with no-op." % node_id)
            return patch_list, ast  # no-op
        elif not (self.tmp_node.__class__.__name__ == TEMPLATE_MUTATIONS[template][0]):
            print(
                "Node classes do not match for template. This could have been caused by a crossover operation. Returning with no-op.")
            print("Node class was %s whereas expected class was %s..." % (
                self.tmp_node.__class__.__name__, TEMPLATE_MUTATIONS[template][0]))
            return patch_list, ast  # no-op

        if self.verbose:
            print("\nApplying template %s to node %d\nOld:" % (template, node_id))
            self.tmp_node.show()

        child_patchlist = copy.deepcopy(patch_list)

        if template == "increment_by_one":
            new_node = vast.Plus(copy.deepcopy(self.tmp_node), vast.IntConst(1, copy.deepcopy(self.tmp_node.lineno)),
                                 copy.deepcopy(self.tmp_node.lineno))
            new_node.node_id = node_id
        elif template == "decrement_by_one":
            new_node = vast.Minus(copy.deepcopy(self.tmp_node), vast.IntConst(1, copy.deepcopy(self.tmp_node.lineno)),
                                  copy.deepcopy(self.tmp_node.lineno))
        elif template == "negate_equality":
            new_node = vast.NotEq(copy.deepcopy(self.tmp_node.left), copy.deepcopy(self.tmp_node.right),
                                  copy.deepcopy(self.tmp_node.lineno))
        elif template == "negate_inequality":
            new_node = vast.Eq(copy.deepcopy(self.tmp_node.left), copy.deepcopy(self.tmp_node.right),
                               copy.deepcopy(self.tmp_node.lineno))
        elif template == "negate_ulnot":
            new_node = vast.Ulnot(copy.deepcopy(self.tmp_node.right), copy.deepcopy(self.tmp_node.lineno))
        elif template == "sens_to_negedge":
            new_node = copy.deepcopy(self.tmp_node)
            new_node.type = "negedge"
        elif template == "sens_to_posedge":
            new_node = copy.deepcopy(self.tmp_node)
            new_node.type = "posedge"
        elif template == "sens_to_level":
            new_node = copy.deepcopy(self.tmp_node)
            new_node.type = "level"
        elif template == "sens_to_all":
            new_node = copy.deepcopy(self.tmp_node)
            new_node.type = "all"
        elif template == "nonblocking_to_blocking":
            new_node = vast.BlockingSubstitution(copy.deepcopy(self.tmp_node.left), copy.deepcopy(self.tmp_node.right),
                                                 copy.deepcopy(self.tmp_node.ldelay),
                                                 copy.deepcopy(self.tmp_node.rdelay),
                                                 copy.deepcopy(self.tmp_node.lineno))
        elif template == "blocking_to_nonblocking":
            new_node = vast.NonblockingSubstitution(copy.deepcopy(self.tmp_node.left),
                                                    copy.deepcopy(self.tmp_node.right),
                                                    copy.deepcopy(self.tmp_node.ldelay),
                                                    copy.deepcopy(self.tmp_node.rdelay),
                                                    copy.deepcopy(self.tmp_node.lineno))

        new_node.node_id = node_id
        if self.verbose:
            print("New:")
            new_node.show()
        self.replace_with_node(ast, node_id, new_node)  # replace with new template node
        child_patchlist.append("template(%s,%s)" % (template, node_id))
        self.numbering.renumber(ast)  # renumber nodes
        self.max_node_id = self.numbering.c  # update max_node_id
        self.numbering.c = -1

        if self.verbose:
            ast.show()

        self.tmp_node = None  # reset the temporary variables
        self.nodes_by_class = []

        return child_patchlist, ast

    def get_crossover_children(self, parent_1, parent_2):
        if len(parent_1) < 1 or len(parent_2) < 1:
            return parent_1, parent_2

        random.seed(inc_seed())
        sp_1 = random.randint(0, len(parent_1))
        random.seed(inc_seed())
        sp_2 = random.randint(0, len(parent_2))

        parent_1_half_1 = copy.deepcopy(parent_1)[:sp_1]
        parent_1_half_2 = copy.deepcopy(parent_1)[sp_1:]
        parent_2_half_1 = copy.deepcopy(parent_2)[:sp_2]
        parent_2_half_2 = copy.deepcopy(parent_2)[sp_2:]

        print(parent_1, parent_2)
        print(sp_1, sp_2)
        print(parent_1_half_1, parent_1_half_2)
        print(parent_2_half_1, parent_2_half_2)

        parent_1_half_1.extend(parent_2_half_2)
        parent_2_half_1.extend(parent_1_half_2)

        print(parent_1_half_1, parent_2_half_1)

        return parent_1_half_1, parent_2_half_1

    def crossover(self, ast, parent_1, parent_2):
        child_1, child_2 = self.get_crossover_children(parent_1, parent_2)

        child_1_ast = self.ast_from_patchlist(copy.deepcopy(ast), child_1)
        child_2_ast = self.ast_from_patchlist(copy.deepcopy(ast), child_2)

        return child_1, child_2, child_1_ast, child_2_ast

    def ast_from_patchlist(self, ast, patch_list):
        for m in patch_list:
            operator = m.split('(')[0]
            operands = m.split('(')[1].replace(')', '').split(',')
            if operator == "replace":
                _, ast = self.replace(ast, patch_list, int(operands[0]), int(operands[1]))
            elif operator == "insert":
                _, ast = self.insert(ast, patch_list, int(operands[0]), int(operands[1]))
            elif operator == "delete":
                _, ast = self.delete(ast, patch_list, int(operands[0]))
            elif operator == "template":
                _, ast = self.apply_template(ast, patch_list, operands[0], int(operands[1]))
            else:
                print("Invalid operator in patch list: %s" % m)
        return ast


def is_interesting(conf: Config, mutation_op, ast, codegen, patch_list):
    tmp_ast = mutation_op.ast_from_patchlist(copy.deepcopy(ast), patch_list)
    minimized_src_file = conf.working_dir / f"minimized.v"
    with open(minimized_src_file, "w+") as f:
        f.write(codegen.visit(tmp_ast))

    ff, _ = calc_candidate_fitness(conf, minimized_src_file)
    os.remove(minimized_src_file)

    if ff == 1:
        print("Patch %s still has a fitness of 1.0 --> interesting" % str(patch_list))
        return True
    else:
        print("Patch %s has a fitness < 1.0 --> not interesting" % str(patch_list))
        return False


"""
Delta debugging for patch minimization.
"""


def minimize_patch(conf: Config, mutation_op, ast, codegen, prefix, patch_list, suffix):
    mid = len(patch_list) // 2
    if mid == 0:
        return patch_list

    left = patch_list[:mid]
    if is_interesting(conf, mutation_op, ast, codegen, prefix + left + suffix):
        return minimize_patch(conf, mutation_op, ast, codegen, prefix, left, suffix)

    right = patch_list[mid:]
    if is_interesting(conf, mutation_op, ast, codegen, prefix + right + suffix):
        return minimize_patch(conf, mutation_op, ast, codegen, prefix, right, suffix)

    left = minimize_patch(conf, mutation_op, ast, codegen, prefix, left, right + suffix)
    right = minimize_patch(conf, mutation_op, ast, codegen, prefix + left, right, suffix)

    return left + right


def tournament_selection(mutation_op, codegen, orig_ast, popn):
    # Choose 5 random candidates for parent selection
    pool = copy.deepcopy(popn)
    while len(pool) > 5:
        random.seed(inc_seed())
        r = random.choice(pool)
        pool.remove(r)

    # generate ast from patchlist for each candidate, compute fitness for each candidate
    max_fitness = -1
    # max_fitness = math.inf
    best_parent_ast = orig_ast
    best_parent_patchlist = []

    for parent_patchlist in pool:
        parent_fitness = GENOME_FITNESS_CACHE[str(parent_patchlist)]

        if parent_fitness > max_fitness:
            # if parent_fitness < max_fitness:
            max_fitness = parent_fitness
            winner_patchlist = parent_patchlist

    winner_ast = copy.deepcopy(orig_ast)
    winner_ast = mutation_op.ast_from_patchlist(winner_ast, winner_patchlist)

    return copy.deepcopy(winner_patchlist), winner_ast


def run_with_iverilog(verbose: bool, working_dir: Path, timeout: float, files: list, stdout, include_dir: Path,
                      compile_timeout: float) -> bool:
    cmd = ['iverilog', '-g2012']
    if include_dir is not None:
        cmd += ["-I", str(include_dir.resolve())]
    cmd += files
    if verbose:
        print(" ".join(str(c) for c in cmd))
    # while iverilog generally does not timeout, we add the timeout here for feature parity with the VCS version
    try:
        r = subprocess.run(cmd, cwd=working_dir, check=False, stdout=stdout, timeout=compile_timeout)
        compiled_successfully = r.returncode == 0
    except subprocess.TimeoutExpired:
        compiled_successfully = False
    # if the simulation does not compile, we won't run anything
    if compiled_successfully:
        try:
            if verbose:
                print('./a.out')
            r = subprocess.run(['./a.out'], cwd=working_dir, shell=True, timeout=timeout, stdout=stdout)
            success = r.returncode == 0
        except subprocess.TimeoutExpired:
            success = False  # failed
        os.remove(os.path.join(working_dir, 'a.out'))
        return  success
    else:
        return False # failed to compile


_vcs_flags = ["-sverilog", "-full64"]


def run_with_vcs(verbose: bool, working_dir: Path, timeout: float, files: list, stdout, include_dir: Path,
                 compile_timeout: float) -> bool:
    cmd = ["vcs"] + _vcs_flags
    if include_dir is not None:
        cmd += [f"+incdir+{str(include_dir.resolve())}"]
    cmd += files
    if verbose:
        print(" ".join(str(c) for c in cmd))
    # VCS can take hours to compile for some changes ...
    try:
        r = subprocess.run(cmd, cwd=working_dir, check=False, stdout=stdout, timeout=compile_timeout)
        compiled_successfully = r.returncode == 0
    except subprocess.TimeoutExpired:
        compiled_successfully = False
    # if the simulation does not compile, we won't run anything
    if compiled_successfully:
        try:
            if verbose:
                print('./simv')
            r = subprocess.run(['./simv'], cwd=working_dir, shell=False, timeout=timeout, stdout=stdout)
            success = r.returncode == 0
        except subprocess.TimeoutExpired:
            success = False # failed
        return success
    else:
        return False # failed to compile


def run(conf: Config, repair_file: Path = None, verbose: bool = False) -> Path:
    # by default, we just run the benchmark
    if repair_file is None:
        repair_file = conf.benchmark.src_file

    benchmark = conf.benchmark
    # make sure there is no output, delete it if necessary
    output = conf.working_dir / benchmark.output
    if output.exists():
        os.remove(output)

    new_files = [ff for ff in benchmark.verilog_files if ff != benchmark.src_file] + [repair_file]
    files = [str(ff.resolve()) for ff in new_files]
    stdout = None if (conf.verbose or verbose) else subprocess.PIPE
    include_dir = benchmark.project_dir

    if conf.simulator == "vcs":
        success = run_with_vcs(conf.verbose, conf.working_dir, benchmark.timeout, files, stdout, include_dir,
                                conf.simulator_compile_timeout)
    else:
        success = run_with_iverilog(conf.verbose, conf.working_dir, benchmark.timeout, files, stdout, include_dir,
                                    conf.simulator_compile_timeout)

    # if the simulation crashed or timed out, we want to remove any half-finished output that may exist
    if not success:
        if output.exists():
            if conf.verbose or verbose: print(f"Simulation failed, but output {output} was created!")
            #os.remove(output) # we might not actually want to delete the output since there might still be some value

    # we always return the name of the output file, the caller will check if it actually exists
    return output


def calc_candidate_fitness(conf: Config, fileName: Path):
    benchmark = conf.benchmark

    if conf.verbose:
        print("Running simulation")

    t_start = time.time()

    output = run(conf, fileName)

    if not output.exists():
        t_finish = time.time()
        return 0, t_finish - t_start  # if the code does not compile, return 0
        # return math.inf

    with open(benchmark.oracle, "r") as f:
        oracle_lines = f.readlines()

    with open(output, "r") as f:
        sim_lines = f.readlines()

    if conf.fitness_mode == "outputwires":
        ff, total_possible = fitness.calculate_fitness(oracle_lines, sim_lines, None, "")

        normalized_ff = ff / total_possible
        if normalized_ff < 0: normalized_ff = 0
        print("FITNESS = %f" % normalized_ff)
        t_finish = time.time()

        return normalized_ff, t_finish - t_start
    elif conf.fitness_mode == "testcases":  # experimental
        total_possible = len(sim_lines)
        count = 0
        for l in sim_lines:
            if "pass" in l.lower(): count += 1
        print("%d out of %d testcases pass" % (count, total_possible))

        t_finish = time.time()
        return count / total_possible, t_finish - t_start


def get_elite_parents(popn, pop_size):
    elite_size = int(5 / 100 * pop_size)
    elite = []
    for parent in popn:
        elite.append((parent, GENOME_FITNESS_CACHE[str(parent)]))
    elite.sort(key=lambda x: x[1])
    return elite[-elite_size:]


def strip_bits(bits):
    for i in range(len(bits)):
        bits[i] = bits[i].strip()
    return bits


def get_output_mismatch(benchmark: Benchmark, output: Path):
    with open(benchmark.oracle, "r") as f:
        oracle = f.readlines()

    with open(output, "r") as f:
        sim = f.readlines()

    diff_bits = []

    headers = strip_bits(oracle[0].split(","))

    if len(oracle) != len(sim):
        # if the output and oracle are not the same length, all output wires are defined to be mismatched
        diff_bits = headers[1:]  # don't include time...
    else:
        for i in range(1, len(oracle)):
            clk = oracle[i].split(",")[0]
            tmp_oracle = strip_bits(oracle[i].split(",")[1:])
            tmp_sim = strip_bits(sim[i].split(",")[1:])

            for b in range(len(tmp_oracle)):
                if tmp_oracle[b] != tmp_sim[b]:
                    diff_bits.append(
                        headers[b + 1])  # offset by 1 since clk is also a header and is not an actual output

    res = set()

    for i in range(len(diff_bits)):
        tmp = diff_bits[i]
        if "[" in tmp:
            res.add(tmp.split("[")[0])
        else:
            res.add(tmp)

    uniq_headers = set()
    for i in range(len(headers)):
        tmp = headers[i]
        if "[" in tmp:
            uniq_headers.add(tmp.split("[")[0])
        else:
            uniq_headers.add(tmp)

    return res, uniq_headers


def seed_popn(conf: Config, ast, mutation_op, codegen, log, log_file):
    seeded = []
    start_time = time.time()
    while len(seeded) < 999:
        child, new_ast = mutation_op.apply_template(copy.deepcopy(ast), [])
        code = codegen.visit(new_ast)
        if conf.verbose:
            print(child)
            print(code)
        if str(child) not in GENOME_FITNESS_CACHE:
            candidate_file = conf.working_dir / f"candidate.v"
            with open(candidate_file, "w+") as f:
                f.write(code)

            child_fitness = -1
            # re-parse the written candidate to check for syntax errors -> zero fitness if the candidate does not compile
            try:
                tmp_ast, directives = parse([str(candidate_file.resolve())])
            except ParseError:
                child_fitness = 0
            # if the child fitness was not 0, i.e. the parser did not throw syntax errors
            if child_fitness == -1:
                child_fitness, sim_time = calc_candidate_fitness(conf, candidate_file)
                global FITNESS_EVAL_TIMES
                FITNESS_EVAL_TIMES.append(sim_time)

            os.remove(candidate_file)

            GENOME_FITNESS_CACHE[str(child)] = child_fitness
            print(child_fitness)
            if log and log_file:
                log_file.write(
                    "\t%s --template_seeding--> %s\t\t%s\n" % ("[]", str(child), "{:.17g}".format(child_fitness)))

            if child_fitness == 1.0:
                print("\n######## REPAIR FOUND WHILE SEEDING INITIAL POPN ########")
                repair_found(conf, log_file, code, child, start_time, mutation_op, ast, codegen)
                sys.exit(0)
        else:  # not a unique seed, log it anyways
            if log and log_file:
                log_file.write("\t%s --template_seeding--> %s\t\t%s\n" % (
                    "[]", str(child), "{:.17g}".format(GENOME_FITNESS_CACHE[str(child)])))

        seeded.append(child)
        # input("...")
    print(GENOME_FITNESS_CACHE)
    print(len(GENOME_FITNESS_CACHE))
    return seeded


def extended_fl_for_study(fl_lines, delta):
    extended_fl = set()
    for i in range(max(fl_lines) + delta):  # e.g. 0 thru 108
        if i in fl_lines:
            extended_fl.add(i)
        else:
            for j in range(1, delta + 1):
                if i + j in fl_lines or i - j in fl_lines:
                    extended_fl.add(i)
    return extended_fl


def repair_found(conf: Config, log_file, code: str, patch_list, start_time, mutation_op, ast, codegen):
    if conf.verbose:
        print(code)
        print(patch_list)

    with open(conf.working_dir / (conf.benchmark.src_file.stem + ".repaired.v"), "w") as f:
        f.write(code)
    with open(conf.working_dir / "patch.txt", "w") as f:
        f.write(str(patch_list) + "\n")

    total_time = time.time() - start_time
    print("TOTAL TIME TAKEN TO FIND REPAIR = %f" % total_time)
    with open(conf.working_dir / "time.txt", "w") as f:
        f.write(str(total_time) + "\n")

    if log_file:
        log_file.write("\n\n######## REPAIR FOUND ########\n\t\t%s\n" % str(patch_list))
        log_file.write("TOTAL TIME TAKEN TO FIND REPAIR = %f\n" % total_time)

    minimized = minimize_patch(conf, mutation_op, ast, codegen, [], patch_list, [])
    print("\n\n")
    print("Minimized patch: %s" % str(minimized))
    with open(conf.working_dir / "minimized.txt", "w") as f:
        f.write(str(minimized) + "\n")
    min_repaired_file = conf.working_dir / (conf.benchmark.src_file.stem + ".repaired.min.v")
    with open(min_repaired_file, "w") as f:
        new_ast = mutation_op.ast_from_patchlist(ast, minimized)
        min_code = codegen.visit(new_ast)
        f.write(min_code)

    # generate diff if possible
    original_file = conf.working_dir / (conf.benchmark.src_file.stem + ".v")
    do_diff(original_file, min_repaired_file, conf.working_dir / "patch_diff.txt")

    if log_file:
        log_file.write("Minimized patch: %s\n" % str(minimized))
        log_file.close()


def do_diff(file_a: Path, file_b: Path, output_file: Path):
    cmd = "diff"
    r = subprocess.run(["which", cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if r.returncode == 0:
        with open(output_file, 'wb') as f:
            subprocess.run(["diff", str(file_a.resolve()), str(file_b.resolve())], stdout=f)


def main():
    global SEED

    optparser = argparse.ArgumentParser()
    optparser.add_argument("-v", "--version", action="store_true", dest="showversion",
                           default=False, help="Show the version")
    optparser.add_argument("-I", "--include", dest="include", action="append",
                           default=[], help="Include path")
    optparser.add_argument("-D", dest="define", action="append",
                           default=[], help="Macro Definition")
    optparser.add_argument("--project", required=True)
    optparser.add_argument("--bug", required=True)
    optparser.add_argument("--testbench")
    optparser.add_argument("--working-dir", dest="working_dir", required=True)
    optparser.add_argument("--config", dest="config", default=_script_dir / "repair.conf")
    optparser.add_argument("--simulator", default="vcs")
    optparser.add_argument("--simulator-compile-timeout", dest="simulator_compile_timeout", type=float,
                           default=60.0 * 2, help="maximum time to compile verilog in seconds")
    optparser.add_argument("--log", action="store_true")
    optparser.add_argument("--code-from-patchlist", dest="code_from_patchlist", action="store_true")
    optparser.add_argument("--minimize-only", dest="minimize_only", action="store_true")
    optparser.add_argument("--seed")
    optparser.add_argument("--verbose", action="store_true", default=False)

    args = optparser.parse_args()

    # overwrite the default seed if one was specified
    if args.seed is not None:
        SEED = args.seed

    benchmark, original_file = load_benchmark(Path(args.project), args.bug, args.testbench)
    conf = load_config(Path(args.config), Path(args.working_dir), benchmark, args.simulator,
                       args.simulator_compile_timeout)
    conf.verbose = args.verbose
    # remove working dir content if it exists
    if conf.working_dir.exists():
        for ff in conf.working_dir.glob("*"):
            if ff.is_dir():
                shutil.rmtree(ff)
            else:
                os.remove(ff)
    else:  # create it otherwise
        os.mkdir(conf.working_dir)
    # make sure the configuration is valid
    validate_config(conf)

    codegen = ASTCodeGenerator()
    # parse the files (in filelist) to ASTs (PyVerilog ast)

    include_dir = str(benchmark.project_dir.resolve())
    ast, directives = parse([benchmark.src_file],
                            preprocess_include=[include_dir],
                            preprocess_define=args.define)

    # show original file with pyverilog formatting
    src_code = codegen.visit(ast)
    if conf.verbose:
        ast.show()
        print(src_code)
        print("\n\n")
    source_copy = conf.working_dir / (conf.benchmark.src_file.stem + ".v")
    with open(source_copy, "w") as f:
        f.write(src_code)

    # show the bug if the original file exists
    if original_file.exists():
        # load with pyverilog and serialize for better diffing
        original_ast, _ = parse([original_file],
                                preprocess_include=[include_dir],
                                preprocess_define=args.define)
        original_src_code = codegen.visit(original_ast)
        original_copy = conf.working_dir / original_file.name
        with open(original_copy, 'w') as f:
            f.write(original_src_code)
        do_diff(original_copy, source_copy, conf.working_dir / "bug_diff.txt")

    # we exclude initialization from the total time since we are printing out
    # some debug information that isn't essential
    # also, we try to exclude jitter from pyverilogs buggy parser caching
    start_time = time.time()

    mutation_op = MutationOp(conf.popsize, conf.fault_loc, conf.control_flow,
                             conf.limit_transitive_dependency_set, conf.dependency_set_max, conf.verbose)

    if args.code_from_patchlist:
        patch_list = eval(input("Please enter the patchlist representation of candidate... "))
        new_ast = mutation_op.ast_from_patchlist(ast, patch_list)
        new_ast.show()

        gencode = codegen.visit(new_ast)
        patchlist_src_file = conf.working_dir / "patchlist_code.v"
        with open(patchlist_src_file, "w+") as f:
            f.write(gencode)

        code_fitness, sim_time = calc_candidate_fitness(conf, patchlist_src_file)
        print(code_fitness)
        print(gencode)

        exit(0)

    elif args.minimize_only:
        patch_list = eval(input("Please enter the patchlist representation of candidate... "))
        print(minimize_patch(conf, mutation_op, ast, codegen, [], patch_list, []))
        exit(0)

    # calculate fitness of the original buggy program
    orig_fitness, sim_time = calc_candidate_fitness(conf, benchmark.src_file)
    global FITNESS_EVAL_TIMES
    FITNESS_EVAL_TIMES.append(sim_time)
    GENOME_FITNESS_CACHE[str([])] = orig_fitness
    print("Original program fitness = %f" % orig_fitness)

    if conf.fitness_mode == "outputwires":
        output = run(conf, verbose = True)
        mismatch_set, uniq_headers = get_output_mismatch(benchmark, output)
        print(mismatch_set)

    # create log file
    log_file = None
    if args.log:
        log_file = open(conf.working_dir / "log.txt", 'w')
        log_file.write("SEED:\n\t %s\n" % SEED)
        log_file.write("SOURCE FILE:\n\t %s\n" % benchmark.src_file)
        log_file.write("benchmark.project_dir:\n\t %s\n" % benchmark.project_dir)
        log_file.write("conf.fitness_mode:\n\t %s\n" % conf.fitness_mode)
        log_file.write("ORACLE:\n\t %s\n" % benchmark.oracle)
        log_file.write("PARAMETERS:\n")
        log_file.write("\tgens=%d\n" % conf.gens)
        log_file.write("\tpopsize=%d\n" % conf.popsize)
        log_file.write("\tmutation_rate=%f\n" % conf.mutation_rate)
        log_file.write("\tcrossover_rate=%f\n" % conf.crossover_rate)
        log_file.write("\treplacement_rate=%f\n" % conf.replacement_rate)
        log_file.write("\tinsertion_rate=%f\n" % conf.insertions_rate)
        log_file.write("\tdeletion_rate=%f\n" % conf.deletion_rate)
        log_file.write("\trestarts=%d\n" % conf.restarts)
        log_file.write("\tfault_loc=%s\n" % conf.fault_loc)
        log_file.write("\tcontrol_flow=%s\n" % conf.control_flow)
        log_file.write("\tlimit_transitive_dependency_set=%s\n" % conf.limit_transitive_dependency_set)
        log_file.write("\tdependency_set_max=%s\n\n" % conf.dependency_set_max)

    best_patches = dict()

    comp_failures = 0

    for restart_attempt in range(conf.restarts):
        popn = []
        popn.append([])
        # popn.append(['insert(53,78)'])

        # seed initial population using repair templates
        popn.extend(seed_popn(conf, copy.deepcopy(ast), mutation_op, codegen, args.log, log_file))

        # print(popn)

        tmp_cnts = {}
        for i in popn:
            if str(i) in tmp_cnts:
                tmp_cnts[str(i)] += 1
            else:
                tmp_cnts[str(i)] = 1

        print("Seeded popn:")
        print(tmp_cnts)
        print("\n\n")

        for i in range(conf.gens):  # for each generation
            print("\nIN GENERATION %d OF ATTEMPT %d" % (i, restart_attempt))
            if args.log: log_file.write("IN GENERATION %d OF ATTEMPT %d\n" % (i, restart_attempt))

            time.sleep(1)
            _children = []

            if i > 0:
                elite_parents = get_elite_parents(popn, conf.popsize)
                for parent in elite_parents:
                    _children.append(parent[0])
                    if args.log: log_file.write(
                        "\t%s --elitism--> %s\t\t%f\n" % (str(parent[0]), str(parent[0]), parent[1]))

            while len(_children) < conf.popsize:
                # time.sleep(2) # use this to slow down the processing for debugging purposes
                parent_patchlist, parent_ast = tournament_selection(mutation_op, codegen, ast, popn)
                print(parent_patchlist)

                fl2_wires = copy.deepcopy(mismatch_set)

                if mutation_op.fault_loc:
                    tmp_mismatch_set = copy.deepcopy(mismatch_set)
                    print()
                    mutation_op.get_fault_loc_targets(parent_ast, tmp_mismatch_set,
                                                      uniq_headers)  # compute fault localization for the parent
                    print("Initial Fault Localization:", str(mutation_op.fault_loc_set))
                    while len(mutation_op.new_vars_in_fault_loc) > 0:
                        new_mismatch_set = set(mutation_op.new_vars_in_fault_loc.values())
                        print("New vars in fault loc:", new_mismatch_set)
                        mutation_op.new_vars_in_fault_loc = dict()
                        tmp_mismatch_set = tmp_mismatch_set.union(new_mismatch_set)
                        mutation_op.get_fault_loc_targets(parent_ast, tmp_mismatch_set, uniq_headers)
                        print("Fault Localization:", str(mutation_op.fault_loc_set))
                    print("Final mismatch set:", tmp_mismatch_set)
                    print("Final Fault Localization:", str(mutation_op.fault_loc_set))
                    print(len(mutation_op.fault_loc_set))

                mutation_op.implicated_lines = set()
                mutation_op.collect_lines_for_fl(parent_ast)
                print("Lines implicated by FL: %s" % str(mutation_op.implicated_lines))
                print("Number of lines implicated by FL: %d" % len(mutation_op.implicated_lines))

                mutation_op.implicated_lines = set()

                random.seed(inc_seed())
                p = random.random()
                _tmp_children = []
                if p <= 0.2:  # apply templates 20% of the time
                    child, child_ast = mutation_op.apply_template(copy.deepcopy(parent_ast),
                                                                  copy.deepcopy(parent_patchlist))
                    _tmp_children.append((child, child_ast))
                    if args.log: log_file.write("\t%s --template--> %s\t\t" % (str(parent_patchlist), str(child)))
                else:
                    random.seed(inc_seed())
                    p = random.random()
                    if i > 1 and 0 <= p and p < conf.crossover_rate and len(
                            _children) <= conf.popsize - 2:  # the last condition ensures that crossover does not result in a popn larger than popsize
                        # do crossover
                        parent_2_patchlist, _ = tournament_selection(mutation_op, codegen, ast, popn)
                        child_1, child_2, child_1_ast, child_2_ast = mutation_op.crossover(ast, parent_patchlist,
                                                                                           parent_2_patchlist)
                        _tmp_children.append((child_1, child_1_ast))
                        _tmp_children.append((child_2, child_2_ast))
                        if args.log: log_file.write("\t%s + %s --crossover--> %s + %s\t\t" % (
                            str(parent_patchlist), str(parent_2_patchlist), str(child_1), str(child_2)))
                        print(child_1, child_2)
                    else:
                        # do mutation
                        random.seed(inc_seed())
                        p = random.random()
                        if 0 <= p and p <= conf.replacement_rate:
                            # TODO: optimization -> don't return ast from parent selection; compute it later (crossover doesn't need it)
                            child, child_ast = mutation_op.replace(parent_ast, parent_patchlist)
                            if args.log: log_file.write(
                                "\t%s --mutation--> %s\t\t" % (str(parent_patchlist), str(child)))
                        elif conf.replacement_rate < p and p <= conf.replacement_rate + conf.deletion_rate:
                            child, child_ast = mutation_op.delete(parent_ast, parent_patchlist)
                            if args.log: log_file.write(
                                "\t%s --mutation--> %s\t\t" % (str(parent_patchlist), str(child)))
                        else:
                            child, child_ast = mutation_op.insert(parent_ast, parent_patchlist)
                            if args.log: log_file.write(
                                "\t%s --mutation--> %s\t\t" % (str(parent_patchlist), str(child)))
                        _tmp_children.append((child, child_ast))
                        print()
                        print(child)

                # calculate children fitness
                for (child_patchlist, child_ast) in _tmp_children:
                    if str(child_patchlist) in GENOME_FITNESS_CACHE:
                        child_fitness = GENOME_FITNESS_CACHE[str(child_patchlist)]
                        print(child_fitness)
                    else:
                        candidate_file = conf.working_dir / f"candidate.v"
                        with open(candidate_file, "w+") as f:
                            code = codegen.visit(child_ast)
                            f.write(code)

                        child_fitness = -1
                        # re-parse the written candidate to check for syntax errors -> zero fitness if the candidate does not compile
                        try:
                            tmp_ast, directives = parse([str(candidate_file.resolve())],
                                                        preprocess_include=[include_dir],
                                                        preprocess_define=args.define)
                        except ParseError:
                            child_fitness = 0
                            comp_failures += 1
                            # child_fitness = math.inf
                        # if the child fitness was not 0, i.e. the parser did not throw syntax errors
                        if child_fitness == -1:
                            child_fitness, sim_time = calc_candidate_fitness(conf, candidate_file)
                            FITNESS_EVAL_TIMES.append(sim_time)

                        os.remove(candidate_file)

                        GENOME_FITNESS_CACHE[str(child_patchlist)] = child_fitness
                        print(child_fitness)

                    if args.log: log_file.write("%s " % "{:.17g}".format(child_fitness))
                    print("\n\n#################\n\n")

                    if child_fitness == 1.0:
                        print("\n######## REPAIR FOUND IN ATTEMPT %d ########" % restart_attempt)
                        repair_found(conf, log_file, code, child_patchlist, start_time, mutation_op, ast, codegen)
                        sys.exit(0)

                    _children.append(child_patchlist)

                if args.log: log_file.write("\n")

                if mutation_op.fault_loc:
                    mutation_op.fault_loc_set = set()  # reset the fault localization data structures for the next parent
                    mutation_op.new_vars_in_fault_loc = dict()
                    mutation_op.wires_brought_in = dict()
                    # mutation_op.blacklist = set()

                print("NUMBER OF COMPILATION FAILURES SO FAR: %d" % comp_failures)

                # exit(1)

            popn = copy.deepcopy(_children)

            for i in popn: print(i)
            print()

        best_patches[restart_attempt] = get_elite_parents(popn, conf.popsize)

    total_time = time.time() - start_time
    print("TOTAL TIME TAKEN = %f" % total_time)
    fitness_times = sum(FITNESS_EVAL_TIMES)
    print("TOTAL TIME SPENT ON FITNESS EVALS = %f" % fitness_times)
    if args.log:
        log_file.write("\n\n\nTOTAL TIME TAKEN = %f\n\n" % total_time)

    if args.log:
        log_file.write("BEST PATCHES:\n")
    for attempt in best_patches:
        print("Attempt number %d" % attempt)
        if args.log:
            log_file.write("\tAttempt number %d:\n" % attempt)
        for candidate in best_patches[attempt]:
            print(candidate)
            if args.log:
                log_file.write("\t\t%s\n" % str(candidate))
        print()

    if args.log:
        log_file.close()


if __name__ == '__main__':
    main()
