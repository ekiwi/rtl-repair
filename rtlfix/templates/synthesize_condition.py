# Copyright 2022 The Regents of the University of California
# released under BSD 3-Clause License
# author: Kevin Laeufer <laeufer@cs.berkeley.edu>

from rtlfix.repair import RepairTemplate
from rtlfix.types import InferWidths
from rtlfix.utils import Namespace
import pyverilog.vparser.ast as vast


def synthesize_condition(ast: vast.Source):
    """ try to synthesize boolean conditions
        - this template repairs a superset of `add_inversion`
        - in order not to create comb loops, we should only consider expressions involving variables that
            - are not dominated by the condition
            - or are registers (indicated by being assigned in a non-blocking assignment process)
        - maybe preference should be given to combinations of existing conditions
    """
    namespace = Namespace(ast)
    infer = InferWidths()
    infer.run(ast)
    repl = ConditionSynthesizer(infer.widths)
    repl.apply(namespace, ast)


class ConditionSynthesizer(RepairTemplate):
    def __init__(self, widths):
        super().__init__(name="condition")
        self.widths = widths
