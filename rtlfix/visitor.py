# Copyright 2022 The Regents of the University of California
# released under BSD 3-Clause License
# author: Kevin Laeufer <laeufer@cs.berkeley.edu>
# Some code was imported from pyverilog/utils/identifierreplace.py
# and is under the following copyright + license.
# Copyright (C) 2015, Shinya Takamaeda-Yamazaki
# License: Apache 2.0

from pyverilog.utils.identifierreplace import children_items


class AstVisitor:
    """ Generic AST visitor for pyverilog. Inspired by the IdentifierReplace class. """

    def __init__(self):
        pass

    def visit(self, node):
        method = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        ret = visitor(node)
        if ret is None:
            return node
        return ret

    def generic_visit(self, node):
        for name, child in children_items(node):
            if child is None:
                continue
            if isinstance(child, list) or isinstance(child, tuple):
                r = []
                for c in child:
                    r.append(self.visit(c))
                ret = tuple(r)
            else:
                ret = self.visit(child)
            setattr(node, name, ret)
        return node
