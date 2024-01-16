"""
   Copyright 2013, Shinya Takamaeda-Yamazaki and Contributors

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""

from __future__ import absolute_import
from __future__ import print_function
import os
import copy
from ply.yacc import yacc

from pyverilog.vparser.preprocessor import VerilogPreprocessor
from pyverilog.vparser.lexer import VerilogLexer
from pyverilog.vparser.ast import *


#################################################
# Parser Definition
#################################################
# Expression Precedence
# Reference: http://hp.vector.co.jp/authors/VA016670/verilog/index.html
precedence = (
    # <- Weak
    ('left', 'LOR'),
    ('left', 'LAND'),
    ('left', 'OR'),
    ('left', 'XOR', 'XNOR'),
    ('left', 'AND'),
    ('left', 'EQ', 'NE', 'EQL', 'NEL'),
    ('left', 'LT', 'GT', 'LE', 'GE'),
    ('left', 'LSHIFT', 'RSHIFT', 'LSHIFTA', 'RSHIFTA'),
    ('left', 'PLUS', 'MINUS'),
    ('left', 'TIMES', 'DIVIDE', 'MOD'),
    ('left', 'POWER'),
    ('right', 'UMINUS', 'UPLUS', 'ULNOT', 'UNOT',
     'UAND', 'UNAND', 'UOR', 'UNOR', 'UXOR', 'UXNOR'),
    # -> Strong
)


# --------------------------------------------------------------------------
# Parse Rule Definition
# --------------------------------------------------------------------------
def p_source_text(p):
    'source_text : description'
    p[0] = Source(name='', description=p[1], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_description(p):
    'description : definitions'
    p[0] = Description(definitions=p[1], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_definitions(p):
    'definitions : definitions definition'
    p[0] = p[1] + (p[2],)
    p.set_lineno(0, p.lineno(1))


def p_definitions_one(p):
    'definitions : definition'
    p[0] = (p[1],)
    p.set_lineno(0, p.lineno(1))


def p_definition(p):
    'definition : moduledef'
    p[0] = p[1]
    p.set_lineno(0, p.lineno(1))


def p_definition_pragma(p):
    'definition : pragma'
    p[0] = p[1]
    p.set_lineno(0, p.lineno(1))


# --------------------------------------------------------------------------
def p_pragma_assign(p):
    'pragma : LPAREN TIMES ID EQUALS expression TIMES RPAREN'
    p[0] = Pragma(PragmaEntry(p[3], p[5], lineno=p.lineno(1)),
                  lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_pragma(p):
    'pragma : LPAREN TIMES ID TIMES RPAREN'
    p[0] = Pragma(PragmaEntry(p[3], lineno=p.lineno(1)),
                  lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


# --------------------------------------------------------------------------
def p_moduledef(p):
    'moduledef : MODULE modulename paramlist portlist items ENDMODULE'
    p[0] = ModuleDef(name=p[2], paramlist=p[3], portlist=p[4], items=p[5],
                     default_nettype=p.lexer.default_nettype, lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))
    p[0].end_lineno = p.lineno(6)


def p_modulename(p):
    'modulename : ID'
    p[0] = p[1]
    p.set_lineno(0, p.lineno(1))


def p_modulename_or(p):
    'modulename : SENS_OR'  # or primitive
    p[0] = p[1]
    p.set_lineno(0, p.lineno(1))


def p_paramlist(p):
    'paramlist : DELAY LPAREN params RPAREN'
    p[0] = Paramlist(params=p[3], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_paramlist_empty(p):
    'paramlist : empty'
    p[0] = Paramlist(params=())


def p_params(p):
    'params : params_begin param_end'
    p[0] = p[1] + (p[2],)
    p.set_lineno(0, p.lineno(1))


def p_params_begin(p):
    'params_begin : params_begin param'
    p[0] = p[1] + (p[2],)
    p.set_lineno(0, p.lineno(1))


def p_params_begin_one(p):
    'params_begin : param'
    p[0] = (p[1],)
    p.set_lineno(0, p.lineno(1))


def p_params_one(p):
    'params : param_end'
    p[0] = (p[1],)
    p.set_lineno(0, p.lineno(1))


def p_param(p):
    'param : PARAMETER param_substitution_list COMMA'
    paramlist = [Parameter(rname, rvalue, lineno=p.lineno(2))
                 for rname, rvalue in p[2]]
    p[0] = Decl(tuple(paramlist), lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_param_signed(p):
    'param : PARAMETER SIGNED param_substitution_list COMMA'
    paramlist = [Parameter(rname, rvalue, signed=True, lineno=p.lineno(2))
                 for rname, rvalue in p[3]]
    p[0] = Decl(tuple(paramlist), lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_param_width(p):
    'param : PARAMETER width param_substitution_list COMMA'
    paramlist = [Parameter(rname, rvalue, p[2], lineno=p.lineno(3))
                 for rname, rvalue in p[3]]
    p[0] = Decl(tuple(paramlist), lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_param_signed_width(p):
    'param : PARAMETER SIGNED width param_substitution_list COMMA'
    paramlist = [Parameter(rname, rvalue, p[3], signed=True, lineno=p.lineno(3))
                 for rname, rvalue in p[4]]
    p[0] = Decl(tuple(paramlist), lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_param_integer(p):
    'param : PARAMETER INTEGER param_substitution_list COMMA'
    paramlist = [Parameter(rname, rvalue, lineno=p.lineno(3))
                 for rname, rvalue in p[3]]
    p[0] = Decl(tuple(paramlist), lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_param_end(p):
    'param_end : PARAMETER param_substitution_list'
    paramlist = [Parameter(rname, rvalue, lineno=p.lineno(2))
                 for rname, rvalue in p[2]]
    p[0] = Decl(tuple(paramlist), lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_param_end_signed(p):
    'param_end : PARAMETER SIGNED param_substitution_list'
    paramlist = [Parameter(rname, rvalue, signed=True, lineno=p.lineno(2))
                 for rname, rvalue in p[3]]
    p[0] = Decl(tuple(paramlist), lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_param_end_width(p):
    'param_end : PARAMETER width param_substitution_list'
    paramlist = [Parameter(rname, rvalue, p[2], lineno=p.lineno(3))
                 for rname, rvalue in p[3]]
    p[0] = Decl(tuple(paramlist), lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_param_end_signed_width(p):
    'param_end : PARAMETER SIGNED width param_substitution_list'
    paramlist = [Parameter(rname, rvalue, p[3], signed=True, lineno=p.lineno(3))
                 for rname, rvalue in p[4]]
    p[0] = Decl(tuple(paramlist), lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_param_end_integer(p):
    'param_end : PARAMETER INTEGER param_substitution_list'
    paramlist = [Parameter(rname, rvalue, lineno=p.lineno(3))
                 for rname, rvalue in p[3]]
    p[0] = Decl(tuple(paramlist), lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_portlist(p):
    'portlist : LPAREN ports RPAREN SEMICOLON'
    p[0] = Portlist(ports=p[2], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_portlist_io(p):
    'portlist : LPAREN ioports RPAREN SEMICOLON'
    p[0] = Portlist(ports=p[2], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_portlist_paren_empty(p):
    'portlist : LPAREN RPAREN SEMICOLON'
    p[0] = Portlist(ports=(), lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_portlist_empty(p):
    'portlist : SEMICOLON'
    p[0] = Portlist(ports=(), lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_ports(p):
    'ports : ports COMMA portname'
    port = Port(name=p[3], width=None, dimensions=None, type=None, lineno=p.lineno(1))
    p[0] = p[1] + (port,)
    p.set_lineno(0, p.lineno(1))


def p_ports_one(p):
    'ports : portname'
    port = Port(name=p[1], width=None, dimensions=None, type=None, lineno=p.lineno(1))
    p[0] = (port,)
    p.set_lineno(0, p.lineno(1))


def p_portname(p):
    'portname : ID'
    p[0] = p[1]
    p.set_lineno(0, p.lineno(1))


def p_sigtypes(p):
    'sigtypes : sigtypes sigtype'
    p[0] = p[1] + (p[2],)
    p.set_lineno(0, p.lineno(1))


def p_sigtypes_one(p):
    'sigtypes : sigtype'
    p[0] = (p[1],)
    p.set_lineno(0, p.lineno(1))


def p_sigtype_input(p):
    'sigtype : INPUT'
    p[0] = p[1]
    p.set_lineno(0, p.lineno(1))


def p_sigtype_output(p):
    'sigtype : OUTPUT'
    p[0] = p[1]
    p.set_lineno(0, p.lineno(1))


def p_sigtype_inout(p):
    'sigtype : INOUT'
    p[0] = p[1]
    p.set_lineno(0, p.lineno(1))


def p_sigtype_tri(p):
    'sigtype : TRI'
    p[0] = p[1]
    p.set_lineno(0, p.lineno(1))


def p_sigtype_reg(p):
    'sigtype : REG'
    p[0] = p[1]
    p.set_lineno(0, p.lineno(1))


def p_sigtype_logic(p):
    'sigtype : LOGIC'
    p[0] = p[1]
    p.set_lineno(0, p.lineno(1))


def p_sigtype_wire(p):
    'sigtype : WIRE'
    p[0] = p[1]
    p.set_lineno(0, p.lineno(1))


def p_sigtype_signed(p):
    'sigtype : SIGNED'
    p[0] = p[1]
    p.set_lineno(0, p.lineno(1))


def p_sigtype_supply0(p):
    'sigtype : SUPPLY0'
    p[0] = p[1]
    p.set_lineno(0, p.lineno(1))


def p_sigtype_supply1(p):
    'sigtype : SUPPLY1'
    p[0] = p[1]
    p.set_lineno(0, p.lineno(1))


def p_ioports(p):
    'ioports : ioports COMMA ioport'
    if isinstance(p[3], str):
        t = None
        for r in reversed(p[1]):
            if isinstance(r.first, Input):
                t = Ioport(Input(name=p[3], width=r.first.width, lineno=p.lineno(3)),
                           lineno=p.lineno(3))
                break
            if isinstance(r.first, Output) and r.second is None:
                t = Ioport(Output(name=p[3], width=r.first.width, lineno=p.lineno(3)),
                           lineno=p.lineno(3))
                break
            if isinstance(r.first, Output) and isinstance(r.second, Reg):
                t = Ioport(Output(name=p[3], width=r.first.width, lineno=p.lineno(3)),
                           Reg(name=p[3], width=r.first.width,
                               lineno=p.lineno(3)),
                           lineno=p.lineno(3))
                break
            if isinstance(r.first, Inout):
                t = Ioport(Inout(name=p[3], width=r.first.width, lineno=p.lineno(3)),
                           lineno=p.lineno(3))
                break
        p[0] = p[1] + (t,)
    else:
        p[0] = p[1] + (p[3],)
    p.set_lineno(0, p.lineno(1))


def p_ioports_one(p):
    'ioports : ioport_head'
    p[0] = (p[1],)
    p.set_lineno(0, p.lineno(1))


def create_ioport(sigtypes, name, width=None, dimensions=None, lineno=0):
    typecheck_ioport(sigtypes)
    first = None
    second = None
    signed = False
    if 'signed' in sigtypes:
        signed = True
    if 'input' in sigtypes:
        first = Input(name=name, width=width, signed=signed,
                      dimensions=dimensions, lineno=lineno)
    if 'output' in sigtypes:
        first = Output(name=name, width=width, signed=signed,
                       dimensions=dimensions, lineno=lineno)
    if 'inout' in sigtypes:
        first = Inout(name=name, width=width, signed=signed,
                      dimensions=dimensions, lineno=lineno)
    if 'wire' in sigtypes:
        second = Wire(name=name, width=width, signed=signed,
                      dimensions=dimensions, lineno=lineno)
    if 'reg' in sigtypes:
        second = Reg(name=name, width=width, signed=signed,
                     dimensions=dimensions, lineno=lineno)
    if 'tri' in sigtypes:
        second = Tri(name=name, width=width, signed=signed,
                     dimensions=dimensions, lineno=lineno)
    return Ioport(first, second, lineno=lineno)


def typecheck_ioport(sigtypes):
    if 'input' not in sigtypes and 'output' not in sigtypes and 'inout' not in sigtypes:
        raise ParseError("Syntax Error")
    if 'input' in sigtypes and 'output' in sigtypes:
        raise ParseError("Syntax Error")
    if 'inout' in sigtypes and 'output' in sigtypes:
        raise ParseError("Syntax Error")
    if 'inout' in sigtypes and 'input' in sigtypes:
        raise ParseError("Syntax Error")
    if 'input' in sigtypes and 'reg' in sigtypes:
        raise ParseError("Syntax Error")
    if 'inout' in sigtypes and 'reg' in sigtypes:
        raise ParseError("Syntax Error")
    if 'input' in sigtypes and 'tri' in sigtypes:
        raise ParseError("Syntax Error")
    if 'output' in sigtypes and 'tri' in sigtypes:
        raise ParseError("Syntax Error")


def p_ioport(p):
    'ioport : sigtypes portname'
    p[0] = create_ioport(p[1], p[2], lineno=p.lineno(2))
    p.set_lineno(0, p.lineno(1))


def p_ioport_width(p):
    'ioport : sigtypes width portname'
    p[0] = create_ioport(p[1], p[3], width=p[2], lineno=p.lineno(3))
    p.set_lineno(0, p.lineno(1))


def p_ioport_dimensions(p):
    'ioport : sigtypes width portname dimensions'
    p[0] = create_ioport(p[1], p[3], width=p[2], dimensions=p[4], lineno=p.lineno(3))
    p.set_lineno(0, p.lineno(1))


def p_ioport_head(p):
    'ioport_head : sigtypes portname'
    p[0] = create_ioport(p[1], p[2], lineno=p.lineno(2))
    p.set_lineno(0, p.lineno(1))


def p_ioport_head_width(p):
    'ioport_head : sigtypes width portname'
    p[0] = create_ioport(p[1], p[3], width=p[2], lineno=p.lineno(3))
    p.set_lineno(0, p.lineno(1))


def p_ioport_head_dimensions(p):
    'ioport_head : sigtypes width portname dimensions'
    p[0] = create_ioport(p[1], p[3], width=p[2], dimensions=p[4], lineno=p.lineno(3))
    p.set_lineno(0, p.lineno(1))


def p_ioport_portname(p):
    'ioport : portname'
    p[0] = p[1]
    p.set_lineno(0, p.lineno(1))


def p_width(p):
    'width : LBRACKET expression COLON expression RBRACKET'
    p[0] = Width(p[2], p[4], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_length(p):
    'length : LBRACKET expression COLON expression RBRACKET'
    p[0] = Length(p[2], p[4], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_dimensions(p):
    'dimensions : dimensions length'
    dims = p[1].lengths + [p[2]]
    p[0] = Dimensions(dims, lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_dimensions_one(p):
    'dimensions : length'
    dims = [p[1]]
    p[0] = Dimensions(dims, lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_items(p):
    'items : items item'
    p[0] = p[1] + (p[2],)
    p.set_lineno(0, p.lineno(1))


def p_items_one(p):
    'items : item'
    p[0] = (p[1],)
    p.set_lineno(0, p.lineno(1))


def p_items_empty(p):
    'items : empty'
    p[0] = ()


def p_item(p):
    """item : standard_item
    | generate
    """
    p[0] = p[1]
    p.set_lineno(0, p.lineno(1))


def p_standard_item(p):
    """standard_item : decl
    | integerdecl
    | realdecl
    | declassign
    | parameterdecl
    | localparamdecl
    | genvardecl
    | assignment
    | always
    | always_ff
    | always_comb
    | always_latch
    | initial
    | instance
    | function
    | task
    | pragma
    """
    p[0] = p[1]
    p.set_lineno(0, p.lineno(1))


# Signal Decl
def create_decl(sigtypes, name, width=None, dimensions=None, lineno=0):
    typecheck_decl(sigtypes, dimensions)
    decls = []
    signed = False
    if 'signed' in sigtypes:
        signed = True
    if 'input' in sigtypes:
        decls.append(Input(name=name, width=width,
                           signed=signed, lineno=lineno, dimensions=dimensions))
    if 'output' in sigtypes:
        decls.append(Output(name=name, width=width,
                            signed=signed, lineno=lineno, dimensions=dimensions))
    if 'inout' in sigtypes:
        decls.append(Inout(name=name, width=width,
                           signed=signed, lineno=lineno, dimensions=dimensions))
    if 'wire' in sigtypes:
        decls.append(Wire(name=name, width=width,
                          signed=signed, lineno=lineno, dimensions=dimensions))
    if 'reg' in sigtypes:
        decls.append(Reg(name=name, width=width,
                         signed=signed, lineno=lineno, dimensions=dimensions))
    if 'tri' in sigtypes:
        decls.append(Tri(name=name, width=width,
                         signed=signed, lineno=lineno, dimensions=dimensions))
    if 'supply0' in sigtypes:
        decls.append(Supply(name=name, value=IntConst('0', lineno=lineno),
                            width=width, signed=signed, lineno=lineno))
    if 'supply1' in sigtypes:
        decls.append(Supply(name=name, value=IntConst('1', lineno=lineno),
                            width=width, signed=signed, lineno=lineno))
    return decls


def typecheck_decl(sigtypes, dimensions=None):
    if ('supply0' in sigtypes or 'supply1' in sigtypes) and \
            dimensions is not None:
        raise ParseError("SyntaxError")
    if len(sigtypes) == 1 and 'signed' in sigtypes:
        raise ParseError("Syntax Error")
    if 'input' in sigtypes and 'output' in sigtypes:
        raise ParseError("Syntax Error")
    if 'inout' in sigtypes and 'output' in sigtypes:
        raise ParseError("Syntax Error")
    if 'inout' in sigtypes and 'input' in sigtypes:
        raise ParseError("Syntax Error")
    if 'input' in sigtypes and 'reg' in sigtypes:
        raise ParseError("Syntax Error")
    if 'inout' in sigtypes and 'reg' in sigtypes:
        raise ParseError("Syntax Error")
    if 'input' in sigtypes and 'tri' in sigtypes:
        raise ParseError("Syntax Error")
    if 'output' in sigtypes and 'tri' in sigtypes:
        raise ParseError("Syntax Error")


def p_decl(p):
    'decl : sigtypes declnamelist SEMICOLON'
    decllist = []
    for rname, rdimensions in p[2]:
        decllist.extend(create_decl(p[1], rname, dimensions=rdimensions,
                                         lineno=p.lineno(2)))
    p[0] = Decl(tuple(decllist), lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_decl_width(p):
    'decl : sigtypes width declnamelist SEMICOLON'
    decllist = []
    for rname, rdimensions in p[3]:
        decllist.extend(create_decl(p[1], rname, width=p[2], dimensions=rdimensions,
                                         lineno=p.lineno(3)))
    p[0] = Decl(tuple(decllist), lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_declnamelist(p):
    'declnamelist : declnamelist COMMA declname'
    p[0] = p[1] + (p[3],)
    p.set_lineno(0, p.lineno(1))


def p_declnamelist_one(p):
    'declnamelist : declname'
    p[0] = (p[1],)
    p.set_lineno(0, p.lineno(1))


def p_declname(p):
    'declname : ID'
    p[0] = (p[1], None)
    p.set_lineno(0, p.lineno(1))


def p_declarray(p):
    'declname : ID dimensions'
    p[0] = (p[1], p[2])
    p.set_lineno(0, p.lineno(1))


# Decl and Assign
def create_declassign(sigtypes, name, assign, width=None, lineno=0):
    typecheck_declassign(sigtypes)
    decls = []
    signed = False
    if 'signed' in sigtypes:
        signed = True
    if 'input' in sigtypes:
        decls.append(Input(name=name, width=width,
                           signed=signed, lineno=lineno))
    if 'output' in sigtypes:
        decls.append(Output(name=name, width=width,
                            signed=signed, lineno=lineno))
    if 'inout' in sigtypes:
        decls.append(Inout(name=name, width=width,
                           signed=signed, lineno=lineno))
    if 'wire' in sigtypes:
        decls.append(Wire(name=name, width=width,
                          signed=signed, lineno=lineno))
    if 'reg' in sigtypes:
        decls.append(Reg(name=name, width=width,
                         signed=signed, lineno=lineno))
    decls.append(assign)
    return decls


def typecheck_declassign(sigtypes):
    if len(sigtypes) == 1 and 'signed' in sigtypes:
        raise ParseError("Syntax Error")
    if 'reg' not in sigtypes and 'wire' not in sigtypes:
        raise ParseError("Syntax Error")
    if 'input' in sigtypes and 'output' in sigtypes:
        raise ParseError("Syntax Error")
    if 'inout' in sigtypes and 'output' in sigtypes:
        raise ParseError("Syntax Error")
    if 'inout' in sigtypes and 'input' in sigtypes:
        raise ParseError("Syntax Error")
    if 'input' in sigtypes and 'reg' in sigtypes:
        raise ParseError("Syntax Error")
    if 'inout' in sigtypes and 'reg' in sigtypes:
        raise ParseError("Syntax Error")
    if 'supply0' in sigtypes and len(sigtypes) != 1:
        raise ParseError("Syntax Error")
    if 'supply1' in sigtypes and len(sigtypes) != 1:
        raise ParseError("Syntax Error")


def p_declassign(p):
    'declassign : sigtypes declassign_element SEMICOLON'
    decllist = create_declassign(
        p[1], p[2][0], p[2][1], lineno=p.lineno(2))
    p[0] = Decl(decllist, lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_declassign_width(p):
    'declassign : sigtypes width declassign_element SEMICOLON'
    decllist = create_declassign(
        p[1], p[3][0], p[3][1], width=p[2], lineno=p.lineno(3))
    p[0] = Decl(tuple(decllist), lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_declassign_element(p):
    'declassign_element : ID EQUALS rvalue'
    assign = Assign(Lvalue(Identifier(p[1], lineno=p.lineno(1)), lineno=p.lineno(1)),
                    p[3], lineno=p.lineno(1))
    p[0] = (p[1], assign)
    p.set_lineno(0, p.lineno(1))


def p_declassign_element_delay(p):
    'declassign_element : delays ID EQUALS delays rvalue'
    assign = Assign(Lvalue(Identifier(p[2], lineno=p.lineno(1)), lineno=p.lineno(2)),
                    p[5], p[1], p[4], lineno=p.lineno(2))
    p[0] = (p[1], assign)
    p.set_lineno(0, p.lineno(2))


# Integer
def p_integerdecl(p):
    'integerdecl : INTEGER integernamelist SEMICOLON'
    intlist = [Integer(rname,
                       Width(msb=IntConst('31', lineno=p.lineno(2)),
                             lsb=IntConst('0', lineno=p.lineno(2)),
                             lineno=p.lineno(2)),
                       signed=True,
                       value=rvalue,
                       lineno=p.lineno(2)) for rname, rvalue in p[2]]
    p[0] = Decl(tuple(intlist), lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_integerdecl_signed(p):
    'integerdecl : INTEGER SIGNED integernamelist SEMICOLON'
    intlist = [Integer(rname,
                       Width(msb=IntConst('31', lineno=p.lineno(3)),
                             lsb=IntConst('0', lineno=p.lineno(3)),
                             lineno=p.lineno(3)),
                       signed=True,
                       value=rvalue,
                       lineno=p.lineno(3)) for rname, rvalue in p[2]]
    p[0] = Decl(tuple(intlist), lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_integernamelist(p):
    'integernamelist : integernamelist COMMA integername'
    p[0] = p[1] + (p[3],)
    p.set_lineno(0, p.lineno(1))


def p_integernamelist_one(p):
    'integernamelist : integername'
    p[0] = (p[1],)
    p.set_lineno(0, p.lineno(1))


def p_integername_init(p):
    'integername : ID EQUALS rvalue'
    p[0] = (p[1], p[3])
    p.set_lineno(0, p.lineno(1))


def p_integername(p):
    'integername : ID'
    p[0] = (p[1], None)
    p.set_lineno(0, p.lineno(1))


# Real
def p_realdecl(p):
    'realdecl : REAL realnamelist SEMICOLON'
    reallist = [Real(p[1],
                     Width(msb=IntConst('31', lineno=p.lineno(2)),
                           lsb=IntConst('0', lineno=p.lineno(2)),
                           lineno=p.lineno(2)),
                     lineno=p.lineno(2)) for r in p[2]]
    p[0] = Decl(tuple(reallist), lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_realnamelist(p):
    'realnamelist : realnamelist COMMA realname'
    p[0] = p[1] + (p[3],)
    p.set_lineno(0, p.lineno(1))


def p_realnamelist_one(p):
    'realnamelist : realname'
    p[0] = (p[1],)
    p.set_lineno(0, p.lineno(1))


def p_realname(p):
    'realname : ID'
    p[0] = p[1]
    p.set_lineno(0, p.lineno(1))


# Parameter
def p_parameterdecl(p):
    'parameterdecl : PARAMETER param_substitution_list SEMICOLON'
    paramlist = [Parameter(rname, rvalue, lineno=p.lineno(2))
                 for rname, rvalue in p[2]]
    p[0] = Decl(tuple(paramlist), lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_parameterdecl_signed(p):
    'parameterdecl : PARAMETER SIGNED param_substitution_list SEMICOLON'
    paramlist = [Parameter(rname, rvalue, signed=True, lineno=p.lineno(2))
                 for rname, rvalue in p[3]]
    p[0] = Decl(tuple(paramlist), lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_parameterdecl_width(p):
    'parameterdecl : PARAMETER width param_substitution_list SEMICOLON'
    paramlist = [Parameter(rname, rvalue, p[2], lineno=p.lineno(3))
                 for rname, rvalue in p[3]]
    p[0] = Decl(tuple(paramlist), lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_parameterdecl_signed_width(p):
    'parameterdecl : PARAMETER SIGNED width param_substitution_list SEMICOLON'
    paramlist = [Parameter(rname, rvalue, p[3], signed=True, lineno=p.lineno(3))
                 for rname, rvalue in p[4]]
    p[0] = Decl(tuple(paramlist), lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_parameterdecl_integer(p):
    'parameterdecl : PARAMETER INTEGER param_substitution_list SEMICOLON'
    paramlist = [Parameter(rname, rvalue, lineno=p.lineno(3))
                 for rname, rvalue in p[3]]
    p[0] = Decl(tuple(paramlist), lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_localparamdecl(p):
    'localparamdecl : LOCALPARAM param_substitution_list SEMICOLON'
    paramlist = [Localparam(rname, rvalue, lineno=p.lineno(2))
                 for rname, rvalue in p[2]]
    p[0] = Decl(tuple(paramlist), lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_localparamdecl_signed(p):
    'localparamdecl : LOCALPARAM SIGNED param_substitution_list SEMICOLON'
    paramlist = [Localparam(rname, rvalue, signed=True, lineno=p.lineno(2))
                 for rname, rvalue in p[3]]
    p[0] = Decl(tuple(paramlist), lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_localparamdecl_width(p):
    'localparamdecl : LOCALPARAM width param_substitution_list SEMICOLON'
    paramlist = [Localparam(rname, rvalue, p[2], lineno=p.lineno(3))
                 for rname, rvalue in p[3]]
    p[0] = Decl(tuple(paramlist), lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_localparamdecl_signed_width(p):
    'localparamdecl : LOCALPARAM SIGNED width param_substitution_list SEMICOLON'
    paramlist = [Localparam(rname, rvalue, p[3], signed=True, lineno=p.lineno(3))
                 for rname, rvalue in p[4]]
    p[0] = Decl(tuple(paramlist), lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_localparamdecl_integer(p):
    'localparamdecl : LOCALPARAM INTEGER param_substitution_list SEMICOLON'
    paramlist = [Localparam(rname, rvalue, lineno=p.lineno(3))
                 for rname, rvalue in p[3]]
    p[0] = Decl(tuple(paramlist), lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_param_substitution_list(p):
    'param_substitution_list : param_substitution_list COMMA param_substitution'
    p[0] = p[1] + (p[3],)
    p.set_lineno(0, p.lineno(1))


def p_param_substitution_list_one(p):
    'param_substitution_list : param_substitution'
    p[0] = (p[1],)
    p.set_lineno(0, p.lineno(1))


def p_param_substitution(p):
    'param_substitution : ID EQUALS rvalue'
    p[0] = (p[1], p[3])
    p.set_lineno(0, p.lineno(1))


def p_assignment(p):
    'assignment : ASSIGN lvalue EQUALS rvalue SEMICOLON'
    p[0] = Assign(p[2], p[4], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_assignment_delay(p):
    'assignment : ASSIGN delays lvalue EQUALS delays rvalue SEMICOLON'
    p[0] = Assign(p[3], p[6], p[2], p[5], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


# --------------------------------------------------------------------------
def p_lpartselect_lpointer(p):
    'lpartselect : pointer LBRACKET expression COLON expression RBRACKET'
    p[0] = Partselect(p[1], p[3], p[5], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_lpartselect_lpointer_plus(p):
    'lpartselect : pointer LBRACKET expression PLUSCOLON expression RBRACKET'
    p[0] = IndexedPartselect(p[1], p[3], p[5], is_plus=True, lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_lpartselect_lpointer_minus(p):
    'lpartselect : pointer LBRACKET expression MINUSCOLON expression RBRACKET'
    p[0] = IndexedPartselect(p[1], p[3], p[5], is_plus=False, lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_lpartselect(p):
    'lpartselect : identifier LBRACKET expression COLON expression RBRACKET'
    p[0] = Partselect(p[1], p[3], p[5], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_lpartselect_plus(p):
    'lpartselect : identifier LBRACKET expression PLUSCOLON expression RBRACKET'
    p[0] = IndexedPartselect(p[1], p[3], p[5], is_plus=True, lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_lpartselect_minus(p):
    'lpartselect : identifier LBRACKET expression MINUSCOLON expression RBRACKET'
    p[0] = IndexedPartselect(p[1], p[3], p[5], is_plus=False, lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_lpointer(p):
    'lpointer : pointer'
    p[0] = p[1]
    p.set_lineno(0, p.lineno(1))


def p_lconcat(p):
    'lconcat : LBRACE lconcatlist RBRACE'
    p[0] = LConcat(p[2], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_lconcatlist(p):
    'lconcatlist : lconcatlist COMMA lconcat_one'
    p[0] = p[1] + (p[3],)
    p.set_lineno(0, p.lineno(1))


def p_lconcatlist_one(p):
    'lconcatlist : lconcat_one'
    p[0] = (p[1],)
    p.set_lineno(0, p.lineno(1))


def p_lconcat_one_identifier(p):
    'lconcat_one : identifier'
    p[0] = p[1]
    p.set_lineno(0, p.lineno(1))


def p_lconcat_one_lpartselect(p):
    'lconcat_one : lpartselect'
    p[0] = p[1]
    p.set_lineno(0, p.lineno(1))


def p_lconcat_one_lpointer(p):
    'lconcat_one : lpointer'
    p[0] = p[1]
    p.set_lineno(0, p.lineno(1))


def p_lconcat_one_lconcat(p):
    'lconcat_one : lconcat'
    p[0] = p[1]
    p.set_lineno(0, p.lineno(1))


def p_lvalue_partselect(p):
    'lvalue : lpartselect'
    p[0] = Lvalue(p[1], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_lvalue_pointer(p):
    'lvalue : lpointer'
    p[0] = Lvalue(p[1], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_lvalue_concat(p):
    'lvalue : lconcat'
    p[0] = Lvalue(p[1], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_lvalue_one(p):
    'lvalue : identifier'
    p[0] = Lvalue(p[1], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_rvalue(p):
    'rvalue : expression'
    p[0] = Rvalue(p[1], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


# --------------------------------------------------------------------------
# Level 1 (Highest Priority)
def p_expression_uminus(p):
    'expression : MINUS expression %prec UMINUS'
    p[0] = Uminus(p[2], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_expression_uplus(p):
    'expression : PLUS expression %prec UPLUS'
    p[0] = p[2]
    p.set_lineno(0, p.lineno(1))


def p_expression_ulnot(p):
    'expression : LNOT expression %prec ULNOT'
    p[0] = Ulnot(p[2], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_expression_unot(p):
    'expression : NOT expression %prec UNOT'
    p[0] = Unot(p[2], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_expression_uand(p):
    'expression : AND expression %prec UAND'
    p[0] = Uand(p[2], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_expression_unand(p):
    'expression : NAND expression %prec UNAND'
    p[0] = Unand(p[2], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_expression_unor(p):
    'expression : NOR expression %prec UNOR'
    p[0] = Unor(p[2], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_expression_uor(p):
    'expression : OR expression %prec UOR'
    p[0] = Uor(p[2], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_expression_uxor(p):
    'expression : XOR expression %prec UXOR'
    p[0] = Uxor(p[2], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_expression_uxnor(p):
    'expression : XNOR expression %prec UXNOR'
    p[0] = Uxnor(p[2], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


# --------------------------------------------------------------------------
# Level 2
def p_expression_power(p):
    'expression : expression POWER expression'
    p[0] = Power(p[1], p[3], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


# --------------------------------------------------------------------------
# Level 3
def p_expression_times(p):
    'expression : expression TIMES expression'
    p[0] = Times(p[1], p[3], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_expression_div(p):
    'expression : expression DIVIDE expression'
    p[0] = Divide(p[1], p[3], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_expression_mod(p):
    'expression : expression MOD expression'
    p[0] = Mod(p[1], p[3], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


# --------------------------------------------------------------------------
# Level 4
def p_expression_plus(p):
    'expression : expression PLUS expression'
    p[0] = Plus(p[1], p[3], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_expression_minus(p):
    'expression : expression MINUS expression'
    p[0] = Minus(p[1], p[3], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


# --------------------------------------------------------------------------
# Level 5
def p_expression_sll(p):
    'expression : expression LSHIFT expression'
    p[0] = Sll(p[1], p[3], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_expression_srl(p):
    'expression : expression RSHIFT expression'
    p[0] = Srl(p[1], p[3], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_expression_sla(p):
    'expression : expression LSHIFTA expression'
    p[0] = Sla(p[1], p[3], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_expression_sra(p):
    'expression : expression RSHIFTA expression'
    p[0] = Sra(p[1], p[3], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


# --------------------------------------------------------------------------
# Level 6
def p_expression_lessthan(p):
    'expression : expression LT expression'
    p[0] = LessThan(p[1], p[3], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_expression_greaterthan(p):
    'expression : expression GT expression'
    p[0] = GreaterThan(p[1], p[3], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_expression_lesseq(p):
    'expression : expression LE expression'
    p[0] = LessEq(p[1], p[3], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_expression_greatereq(p):
    'expression : expression GE expression'
    p[0] = GreaterEq(p[1], p[3], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


# --------------------------------------------------------------------------
# Level 7
def p_expression_eq(p):
    'expression : expression EQ expression'
    p[0] = Eq(p[1], p[3], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_expression_noteq(p):
    'expression : expression NE expression'
    p[0] = NotEq(p[1], p[3], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_expression_eql(p):
    'expression : expression EQL expression'
    p[0] = Eql(p[1], p[3], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_expression_noteql(p):
    'expression : expression NEL expression'
    p[0] = NotEql(p[1], p[3], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


# --------------------------------------------------------------------------
# Level 8
def p_expression_And(p):
    'expression : expression AND expression'
    p[0] = And(p[1], p[3], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_expression_Xor(p):
    'expression : expression XOR expression'
    p[0] = Xor(p[1], p[3], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_expression_Xnor(p):
    'expression : expression XNOR expression'
    p[0] = Xnor(p[1], p[3], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


# --------------------------------------------------------------------------
# Level 9
def p_expression_Or(p):
    'expression : expression OR expression'
    p[0] = Or(p[1], p[3], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


# --------------------------------------------------------------------------
# Level 10
def p_expression_land(p):
    'expression : expression LAND expression'
    p[0] = Land(p[1], p[3], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


# --------------------------------------------------------------------------
# Level 11
def p_expression_lor(p):
    'expression : expression LOR expression'
    p[0] = Lor(p[1], p[3], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


# --------------------------------------------------------------------------
# Level 12
def p_expression_cond(p):
    'expression : expression COND expression COLON expression'
    p[0] = Cond(p[1], p[3], p[5], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


# --------------------------------------------------------------------------
def p_expression_expr(p):
    'expression : LPAREN expression RPAREN'
    p[0] = p[2]
    p.set_lineno(0, p.lineno(2))


# --------------------------------------------------------------------------
def p_expression_concat(p):
    'expression : concat'
    p[0] = p[1]
    p.set_lineno(0, p.lineno(1))


def p_expression_repeat(p):
    'expression : repeat'
    p[0] = p[1]
    p.set_lineno(0, p.lineno(1))


def p_expression_partselect(p):
    'expression : partselect'
    p[0] = p[1]
    p.set_lineno(0, p.lineno(1))


def p_expression_pointer(p):
    'expression : pointer'
    p[0] = p[1]
    p.set_lineno(0, p.lineno(1))


def p_expression_functioncall(p):
    'expression : functioncall'
    p[0] = p[1]
    p.set_lineno(0, p.lineno(1))


def p_expression_systemcall(p):
    'expression : systemcall'
    p[0] = p[1]
    p.set_lineno(0, p.lineno(1))


def p_expression_id(p):
    'expression : identifier'
    p[0] = p[1]
    p.set_lineno(0, p.lineno(1))


def p_expression_const(p):
    'expression : const_expression'
    p[0] = p[1]
    p.set_lineno(0, p.lineno(1))


def p_concat(p):
    'concat : LBRACE concatlist RBRACE'
    p[0] = Concat(p[2], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_concatlist(p):
    'concatlist : concatlist COMMA expression'
    p[0] = p[1] + (p[3],)
    p.set_lineno(0, p.lineno(1))


def p_concatlist_one(p):
    'concatlist : expression'
    p[0] = (p[1],)
    p.set_lineno(0, p.lineno(1))


def p_repeat(p):
    'repeat : LBRACE expression concat RBRACE'
    p[0] = Repeat(p[3], p[2], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_partselect(p):
    'partselect : identifier LBRACKET expression COLON expression RBRACKET'
    p[0] = Partselect(p[1], p[3], p[5], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_partselect_plus(p):
    'partselect : identifier LBRACKET expression PLUSCOLON expression RBRACKET'
    p[0] = IndexedPartselect(p[1], p[3], p[5], is_plus=True, lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_partselect_minus(p):
    'partselect : identifier LBRACKET expression MINUSCOLON expression RBRACKET'
    p[0] = IndexedPartselect(p[1], p[3], p[5], is_plus=False, lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_partselect_pointer(p):
    'partselect : pointer LBRACKET expression COLON expression RBRACKET'
    p[0] = Partselect(p[1], p[3], p[5], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_partselect_pointer_plus(p):
    'partselect : pointer LBRACKET expression PLUSCOLON expression RBRACKET'
    p[0] = IndexedPartselect(p[1], p[3], p[5], is_plus=True, lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_partselect_pointer_minus(p):
    'partselect : pointer LBRACKET expression MINUSCOLON expression RBRACKET'
    p[0] = IndexedPartselect(p[1], p[3], p[5], is_plus=False, lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_pointer(p):
    'pointer : identifier LBRACKET expression RBRACKET'
    p[0] = Pointer(p[1], p[3], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_pointer_pointer(p):
    'pointer : pointer LBRACKET expression RBRACKET'
    p[0] = Pointer(p[1], p[3], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


# --------------------------------------------------------------------------
def p_const_expression_intnum(p):
    'const_expression : intnumber'
    p[0] = IntConst(p[1], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_const_expression_floatnum(p):
    'const_expression : floatnumber'
    p[0] = FloatConst(p[1], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_const_expression_stringliteral(p):
    'const_expression : stringliteral'
    p[0] = StringConst(p[1], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_floatnumber(p):
    'floatnumber : FLOATNUMBER'
    p[0] = p[1]
    p.set_lineno(0, p.lineno(1))


def p_intnumber(p):
    """intnumber : INTNUMBER_DEC
    | SIGNED_INTNUMBER_DEC
    | INTNUMBER_BIN
    | SIGNED_INTNUMBER_BIN
    | INTNUMBER_OCT
    | SIGNED_INTNUMBER_OCT
    | INTNUMBER_HEX
    | SIGNED_INTNUMBER_HEX
    """
    p[0] = p[1]
    p.set_lineno(0, p.lineno(1))


# --------------------------------------------------------------------------
# String Literal
def p_stringliteral(p):
    'stringliteral : STRING_LITERAL'
    p[0] = p[1][1:-1]  # strip \" and \"
    p.set_lineno(0, p.lineno(1))


# --------------------------------------------------------------------------
# Always
def p_always(p):
    'always : ALWAYS senslist always_statement'
    p[0] = Always(p[2], p[3], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_always_ff(p):
    'always_ff : ALWAYS_FF senslist always_statement'
    p[0] = AlwaysFF(p[2], p[3], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_always_comb(p):
    'always_comb : ALWAYS_COMB senslist always_statement'
    p[0] = AlwaysComb(p[2], p[3], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_always_latch(p):
    'always_latch : ALWAYS_LATCH senslist always_statement'
    p[0] = AlwaysLatch(p[2], p[3], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_sens_egde_paren(p):
    'senslist : AT LPAREN edgesigs RPAREN'
    p[0] = SensList(p[3], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_posedgesig(p):
    'edgesig : POSEDGE edgesig_base'
    p[0] = Sens(p[2], 'posedge', lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_negedgesig(p):
    'edgesig : NEGEDGE edgesig_base'
    p[0] = Sens(p[2], 'negedge', lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_edgesig_base_identifier(p):
    'edgesig_base : identifier'
    p[0] = p[1]
    p.set_lineno(0, p.lineno(1))


def p_edgesig_base_pointer(p):
    'edgesig_base : pointer'
    p[0] = p[1]
    p.set_lineno(0, p.lineno(1))


def p_edgesigs(p):
    'edgesigs : edgesigs SENS_OR edgesig'
    p[0] = p[1] + (p[3],)
    p.set_lineno(0, p.lineno(1))


def p_edgesigs_comma(p):
    'edgesigs : edgesigs COMMA edgesig'
    p[0] = p[1] + (p[3],)
    p.set_lineno(0, p.lineno(1))


def p_edgesigs_one(p):
    'edgesigs : edgesig'
    p[0] = (p[1],)
    p.set_lineno(0, p.lineno(1))


def p_sens_empty(p):
    'senslist : empty'
    p[0] = SensList(
        (Sens(None, 'all', lineno=p.lineno(1)),), lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_sens_level(p):
    'senslist : AT levelsig'
    p[0] = SensList((p[2],), lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_sens_level_paren(p):
    'senslist : AT LPAREN levelsigs RPAREN'
    p[0] = SensList(p[3], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_levelsig(p):
    'levelsig : levelsig_base'
    p[0] = Sens(p[1], 'level', lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_levelsig_base_identifier(p):
    'levelsig_base : identifier'
    p[0] = p[1]
    p.set_lineno(0, p.lineno(1))


def p_levelsig_base_pointer(p):
    'levelsig_base : pointer'
    p[0] = p[1]
    p.set_lineno(0, p.lineno(1))


def p_levelsig_base_partselect(p):
    'levelsig_base : partselect'
    p[0] = p[1]
    p.set_lineno(0, p.lineno(1))


def p_levelsigs(p):
    'levelsigs : levelsigs SENS_OR levelsig'
    p[0] = p[1] + (p[3],)
    p.set_lineno(0, p.lineno(1))


def p_levelsigs_comma(p):
    'levelsigs : levelsigs COMMA levelsig'
    p[0] = p[1] + (p[3],)
    p.set_lineno(0, p.lineno(1))


def p_levelsigs_one(p):
    'levelsigs : levelsig'
    p[0] = (p[1],)
    p.set_lineno(0, p.lineno(1))


def p_sens_all(p):
    'senslist : AT TIMES'
    p[0] = SensList(
        (Sens(None, 'all', lineno=p.lineno(1)),), lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_sens_all_paren(p):
    'senslist : AT LPAREN TIMES RPAREN'
    p[0] = SensList(
        (Sens(None, 'all', lineno=p.lineno(1)),), lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_basic_statement(p):
    """basic_statement : if_statement
    | case_statement
    | casex_statement
    | casez_statement
    | unique_case_statement
    | for_statement
    | while_statement
    | event_statement
    | wait_statement
    | forever_statement
    | block
    | namedblock
    | parallelblock
    | blocking_substitution
    | nonblocking_substitution
    | single_statement
    """
    p[0] = p[1]
    p.set_lineno(0, p.lineno(1))


def p_always_statement(p):
    'always_statement : basic_statement'
    p[0] = p[1]
    p.set_lineno(0, p.lineno(1))


# --------------------------------------------------------------------------
def p_blocking_substitution(p):
    'blocking_substitution : delays lvalue EQUALS delays rvalue SEMICOLON'
    p[0] = BlockingSubstitution(p[2], p[5], p[1], p[4], lineno=p.lineno(2))
    p.set_lineno(0, p.lineno(2))


def p_blocking_substitution_base(p):
    'blocking_substitution_base : delays lvalue EQUALS delays rvalue'
    p[0] = BlockingSubstitution(p[2], p[5], p[1], p[4], lineno=p.lineno(2))
    p.set_lineno(0, p.lineno(2))


def p_nonblocking_substitution(p):
    'nonblocking_substitution : delays lvalue LE delays rvalue SEMICOLON'
    p[0] = NonblockingSubstitution(
        p[2], p[5], p[1], p[4], lineno=p.lineno(2))
    p.set_lineno(0, p.lineno(2))


# --------------------------------------------------------------------------
def p_delays(p):
    'delays : DELAY LPAREN expression RPAREN'
    p[0] = DelayStatement(p[3], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_delays_identifier(p):
    'delays : DELAY identifier'
    p[0] = DelayStatement(p[2], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_delays_intnumber(p):
    'delays : DELAY intnumber'
    p[0] = DelayStatement(
        IntConst(p[2], lineno=p.lineno(1)), lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_delays_floatnumber(p):
    'delays : DELAY floatnumber'
    p[0] = DelayStatement(FloatConst(
        p[2], lineno=p.lineno(1)), lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_delays_empty(p):
    'delays : empty'
    p[0] = None


# --------------------------------------------------------------------------
def p_block(p):
    'block : BEGIN block_statements END'
    p[0] = Block(p[2], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_block_empty(p):
    'block : BEGIN END'
    p[0] = Block((), lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_block_statements(p):
    'block_statements : block_statements block_statement'
    p[0] = p[1] + (p[2],)
    p.set_lineno(0, p.lineno(1))


def p_block_statements_one(p):
    'block_statements : block_statement'
    p[0] = (p[1],)
    p.set_lineno(0, p.lineno(1))


def p_block_statement(p):
    'block_statement : basic_statement'
    p[0] = p[1]
    p.set_lineno(0, p.lineno(1))


# --------------------------------------------------------------------------
def p_namedblock(p):
    'namedblock : BEGIN COLON ID namedblock_statements END'
    p[0] = Block(p[4], p[3], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_namedblock_empty(p):
    'namedblock : BEGIN COLON ID END'
    p[0] = Block((), p[3], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_namedblock_statements(p):
    'namedblock_statements : namedblock_statements namedblock_statement'
    p[0] = p[1] + (p[2],)
    p.set_lineno(0, p.lineno(1))


def p_namedblock_statements_one(p):
    'namedblock_statements : namedblock_statement'
    p[0] = (p[1],)
    p.set_lineno(0, p.lineno(1))


def p_namedblock_statement(p):
    """namedblock_statement : basic_statement
    | decl
    | integerdecl
    | realdecl
    | parameterdecl
    | localparamdecl
    """
    if isinstance(p[1], Decl):
        for r in p[1].list:
            if (not isinstance(r, Reg) and not isinstance(r, Wire) and
                    not isinstance(r, Integer) and not isinstance(r, Real) and
                    not isinstance(r, Parameter) and not isinstance(r, Localparam)):
                raise ParseError("Syntax Error")
    p[0] = p[1]
    p.set_lineno(0, p.lineno(1))


# --------------------------------------------------------------------------
def p_parallelblock(p):
    'parallelblock : FORK block_statements JOIN'
    p[0] = ParallelBlock(p[2], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_parallelblock_empty(p):
    'parallelblock : FORK JOIN'
    p[0] = ParallelBlock((), lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


# --------------------------------------------------------------------------
def p_if_statement(p):
    'if_statement : IF LPAREN cond RPAREN true_statement ELSE else_statement'
    p[0] = IfStatement(p[3], p[5], p[7], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_if_statement_woelse(p):
    'if_statement : IF LPAREN cond RPAREN true_statement'
    p[0] = IfStatement(p[3], p[5], None, lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_if_statement_delay(p):
    'if_statement : delays IF LPAREN cond RPAREN true_statement ELSE else_statement'
    p[0] = IfStatement(p[4], p[6], p[8], lineno=p.lineno(2))
    p.set_lineno(0, p.lineno(2))


def p_if_statement_woelse_delay(p):
    'if_statement : delays IF LPAREN cond RPAREN true_statement'
    p[0] = IfStatement(p[4], p[6], None, lineno=p.lineno(2))
    p.set_lineno(0, p.lineno(2))


def p_cond(p):
    'cond : expression'
    p[0] = p[1]
    p.set_lineno(0, p.lineno(1))


def p_ifcontent_statement(p):
    'ifcontent_statement : basic_statement'
    p[0] = p[1]
    p.set_lineno(0, p.lineno(1))


def p_true_statement(p):
    'true_statement : ifcontent_statement'
    p[0] = p[1]
    p.set_lineno(0, p.lineno(1))


def p_else_statement(p):
    'else_statement : ifcontent_statement'
    p[0] = p[1]
    p.set_lineno(0, p.lineno(1))


# --------------------------------------------------------------------------
def p_for_statement(p):
    'for_statement : FOR LPAREN forpre forcond forpost RPAREN forcontent_statement'
    p[0] = ForStatement(p[3], p[4], p[5], p[7], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_forpre(p):
    'forpre : blocking_substitution'
    p[0] = p[1]
    p.set_lineno(0, p.lineno(1))


def p_forpre_empty(p):
    'forpre : SEMICOLON'
    p[0] = None
    p.set_lineno(0, p.lineno(1))


def p_forcond(p):
    'forcond : cond SEMICOLON'
    p[0] = p[1]
    p.set_lineno(0, p.lineno(1))


def p_forcond_empty(p):
    'forcond : SEMICOLON'
    p[0] = None
    p.set_lineno(0, p.lineno(1))


def p_forpost(p):
    'forpost : blocking_substitution_base'
    p[0] = p[1]
    p.set_lineno(0, p.lineno(1))


def p_forpost_empty(p):
    'forpost : empty'
    p[0] = None


def p_forcontent_statement(p):
    'forcontent_statement : basic_statement'
    p[0] = p[1]
    p.set_lineno(0, p.lineno(1))


# --------------------------------------------------------------------------
def p_while_statement(p):
    'while_statement : WHILE LPAREN cond RPAREN whilecontent_statement'
    p[0] = WhileStatement(p[3], p[5], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_whilecontent_statement(p):
    'whilecontent_statement : basic_statement'
    p[0] = p[1]
    p.set_lineno(0, p.lineno(1))


# --------------------------------------------------------------------------
def p_case_statement(p):
    'case_statement : CASE LPAREN case_comp RPAREN casecontent_statements ENDCASE'
    p[0] = CaseStatement(p[3], p[5], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_casex_statement(p):
    'casex_statement : CASEX LPAREN case_comp RPAREN casecontent_statements ENDCASE'
    p[0] = CasexStatement(p[3], p[5], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_casez_statement(p):
    'casez_statement : CASEZ LPAREN case_comp RPAREN casecontent_statements ENDCASE'
    p[0] = CasezStatement(p[3], p[5], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_unique_case_statement(p):
    'unique_case_statement : UNIQUE CASE LPAREN case_comp RPAREN casecontent_statements ENDCASE'
    p[0] = UniqueCaseStatement(p[3], p[5], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_case_comp(p):
    'case_comp : expression'
    p[0] = p[1]
    p.set_lineno(0, p.lineno(1))


def p_casecontent_statements(p):
    'casecontent_statements : casecontent_statements casecontent_statement'
    p[0] = p[1] + (p[2],)
    p.set_lineno(0, p.lineno(1))


def p_casecontent_statements_one(p):
    'casecontent_statements : casecontent_statement'
    p[0] = (p[1],)
    p.set_lineno(0, p.lineno(1))


def p_casecontent_statement(p):
    'casecontent_statement : casecontent_condition COLON basic_statement'
    p[0] = Case(p[1], p[3], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_casecontent_condition_single(p):
    'casecontent_condition : casecontent_condition COMMA expression'
    p[0] = p[1] + (p[3],)
    p.set_lineno(0, p.lineno(1))


def p_casecontent_condition_one(p):
    'casecontent_condition : expression'
    p[0] = (p[1],)
    p.set_lineno(0, p.lineno(1))


def p_casecontent_statement_default(p):
    'casecontent_statement : DEFAULT COLON basic_statement'
    p[0] = Case(None, p[3], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


# --------------------------------------------------------------------------
def p_initial(p):
    'initial : INITIAL initial_statement'
    p[0] = Initial(p[2], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_initial_statement(p):
    'initial_statement : basic_statement'
    p[0] = p[1]
    p.set_lineno(0, p.lineno(1))


# --------------------------------------------------------------------------
def p_event_statement(p):
    'event_statement : senslist SEMICOLON'
    p[0] = EventStatement(p[1], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


# --------------------------------------------------------------------------
def p_wait_statement(p):
    'wait_statement : WAIT LPAREN cond RPAREN waitcontent_statement'
    p[0] = WaitStatement(p[3], p[5], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_waitcontent_statement(p):
    'waitcontent_statement : basic_statement'
    p[0] = p[1]
    p.set_lineno(0, p.lineno(1))


def p_waitcontent_statement_empty(p):
    'waitcontent_statement : SEMICOLON'
    p[0] = None
    p.set_lineno(0, p.lineno(1))


# --------------------------------------------------------------------------
def p_forever_statement(p):
    'forever_statement : FOREVER basic_statement'
    p[0] = ForeverStatement(p[2], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


# --------------------------------------------------------------------------
def p_instance(p):
    'instance : ID parameterlist instance_bodylist SEMICOLON'
    instancelist = []
    for instance_name, instance_ports, instance_array in p[3]:
        instancelist.append(Instance(p[1], instance_name, instance_ports,
                                     p[2], instance_array, lineno=p.lineno(1)))
    p[0] = InstanceList(p[1], p[2], tuple(
        instancelist), lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_instance_or(p):
    'instance : SENS_OR parameterlist instance_bodylist SEMICOLON'
    instancelist = []
    for instance_name, instance_ports, instance_array in p[3]:
        instancelist.append(Instance(p[1], instance_name, instance_ports,
                                     p[2], instance_array, lineno=p.lineno(1)))
    p[0] = InstanceList(p[1], p[2], tuple(
        instancelist), lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_instance_bodylist(p):
    'instance_bodylist : instance_bodylist COMMA instance_body'
    p[0] = p[1] + (p[3],)
    p.set_lineno(0, p.lineno(1))


def p_instance_bodylist_one(p):
    'instance_bodylist : instance_body'
    p[0] = (p[1],)
    p.set_lineno(0, p.lineno(1))


def p_instance_body(p):
    'instance_body : ID LPAREN instance_ports RPAREN'
    p[0] = (p[1], p[3], None)
    p.set_lineno(0, p.lineno(1))


def p_instance_body_array(p):
    'instance_body : ID width LPAREN instance_ports RPAREN'
    p[0] = (p[1], p[4], p[2])
    p.set_lineno(0, p.lineno(1))


def p_instance_noname(p):
    'instance : ID instance_bodylist_noname SEMICOLON'
    instancelist = []
    for instance_name, instance_ports, instance_array in p[2]:
        instancelist.append(Instance(p[1], instance_name, instance_ports,
                                     (), instance_array, lineno=p.lineno(1)))
    p[0] = InstanceList(p[1], (), tuple(instancelist), lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_instance_or_noname(p):
    'instance : SENS_OR instance_bodylist_noname SEMICOLON'
    instancelist = []
    for instance_name, instance_ports, instance_array in p[2]:
        instancelist.append(Instance(p[1], instance_name, instance_ports,
                                     (), instance_array, lineno=p.lineno(1)))
    p[0] = InstanceList(p[1], (), tuple(instancelist), lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_instance_bodylist_noname(p):
    'instance_bodylist_noname : instance_bodylist_noname COMMA instance_body_noname'
    p[0] = p[1] + (p[3],)
    p.set_lineno(0, p.lineno(1))


def p_instance_bodylist_one_noname(p):
    'instance_bodylist_noname : instance_body_noname'
    p[0] = (p[1],)
    p.set_lineno(0, p.lineno(1))


def p_instance_body_noname(p):
    'instance_body_noname : LPAREN instance_ports RPAREN'
    p[0] = ('', p[2], None)
    p.set_lineno(0, p.lineno(1))


def p_parameterlist(p):
    'parameterlist : DELAY LPAREN param_args RPAREN'
    p[0] = p[3]
    p.set_lineno(0, p.lineno(1))


def p_parameterlist_noname(p):
    'parameterlist : DELAY LPAREN param_args_noname RPAREN'
    p[0] = p[3]
    p.set_lineno(0, p.lineno(1))


def p_parameterlist_empty(p):
    'parameterlist : empty'
    p[0] = ()


def p_param_args_noname(p):
    'param_args_noname : param_args_noname COMMA param_arg_noname'
    p[0] = p[1] + (p[3],)
    p.set_lineno(0, p.lineno(1))


def p_param_args_noname_one(p):
    'param_args_noname : param_arg_noname'
    p[0] = (p[1],)
    p.set_lineno(0, p.lineno(1))


def p_param_args(p):
    'param_args : param_args COMMA param_arg'
    p[0] = p[1] + (p[3],)
    p.set_lineno(0, p.lineno(1))


def p_param_args_one(p):
    'param_args : param_arg'
    p[0] = (p[1],)
    p.set_lineno(0, p.lineno(1))


def p_param_args_empty(p):
    'param_args : empty'
    p[0] = ()


def p_param_arg_noname_exp(p):
    'param_arg_noname : expression'
    p[0] = ParamArg(None, p[1], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_param_arg_exp(p):
    'param_arg : DOT ID LPAREN expression RPAREN'
    p[0] = ParamArg(p[2], p[4], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_instance_ports(p):
    """instance_ports : instance_ports_list
    | instance_ports_arg
    """
    p[0] = p[1]
    p.set_lineno(0, p.lineno(1))


def p_instance_ports_list(p):
    'instance_ports_list : instance_ports_list COMMA instance_port_list'
    p[0] = p[1] + (p[3],)
    p.set_lineno(0, p.lineno(1))


def p_instance_ports_list_one(p):
    'instance_ports_list : instance_port_list'
    p[0] = (p[1],)
    p.set_lineno(0, p.lineno(1))


def p_instance_ports_list_empty(p):
    'instance_ports_list : empty'
    p[0] = ()
    p.set_lineno(0, p.lineno(1))


def p_instance_port_list(p):
    'instance_port_list : expression'
    p[0] = PortArg(None, p[1], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_instance_ports_arg(p):
    'instance_ports_arg : instance_ports_arg COMMA instance_port_arg'
    p[0] = p[1] + (p[3],)
    p.set_lineno(0, p.lineno(1))


def p_instance_ports_arg_one(p):
    'instance_ports_arg : instance_port_arg'
    p[0] = (p[1],)
    p.set_lineno(0, p.lineno(1))


def p_instance_port_arg(p):
    'instance_port_arg : DOT ID LPAREN identifier RPAREN'
    p[0] = PortArg(p[2], p[4], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_instance_port_arg_exp(p):
    'instance_port_arg : DOT ID LPAREN expression RPAREN'
    p[0] = PortArg(p[2], p[4], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_instance_port_arg_none(p):
    'instance_port_arg : DOT ID LPAREN RPAREN'
    p[0] = PortArg(p[2], None, lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


# --------------------------------------------------------------------------
def p_genvardecl(p):
    'genvardecl : GENVAR genvarlist SEMICOLON'
    p[0] = Decl(p[2], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_genvarlist(p):
    'genvarlist : genvarlist COMMA genvar'
    p[0] = p[1] + (p[3],)
    p.set_lineno(0, p.lineno(1))


def p_genvarlist_one(p):
    'genvarlist : genvar'
    p[0] = (p[1],)
    p.set_lineno(0, p.lineno(1))


def p_genvar(p):
    'genvar : ID'
    p[0] = Genvar(name=p[1],
                  width=Width(msb=IntConst('31', lineno=p.lineno(1)),
                              lsb=IntConst('0', lineno=p.lineno(1)),
                              lineno=p.lineno(1)),
                  lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_generate(p):
    'generate : GENERATE generate_items ENDGENERATE'
    p[0] = GenerateStatement(p[2], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_generate_items_empty(p):
    'generate_items : empty'
    p[0] = ()
    p.set_lineno(0, p.lineno(1))


def p_generate_items(p):
    'generate_items : generate_items generate_item'
    p[0] = p[1] + (p[2],)
    p.set_lineno(0, p.lineno(1))


def p_generate_items_one(p):
    'generate_items : generate_item'
    p[0] = (p[1],)
    p.set_lineno(0, p.lineno(1))


def p_generate_item(p):
    """generate_item : standard_item
    | generate_if
    | generate_for
    """
    p[0] = p[1]
    p.set_lineno(0, p.lineno(1))


def p_generate_block(p):
    'generate_block : BEGIN generate_items END'
    p[0] = Block(p[2], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_generate_named_block(p):
    'generate_block : BEGIN COLON ID generate_items END'
    p[0] = Block(p[4], p[3], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_generate_if(p):
    'generate_if : IF LPAREN cond RPAREN gif_true_item ELSE gif_false_item'
    p[0] = IfStatement(p[3], p[5], p[7], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_generate_if_woelse(p):
    'generate_if : IF LPAREN cond RPAREN gif_true_item'
    p[0] = IfStatement(p[3], p[5], None, lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_generate_if_true_item(p):
    """gif_true_item : generate_item
    | generate_block
    """
    p[0] = p[1]
    p.set_lineno(0, p.lineno(1))


def p_generate_if_false_item(p):
    """gif_false_item : generate_item
    | generate_block
    """
    p[0] = p[1]
    p.set_lineno(0, p.lineno(1))


def p_generate_for(p):
    'generate_for : FOR LPAREN forpre forcond forpost RPAREN generate_forcontent'
    p[0] = ForStatement(p[3], p[4], p[5], p[7], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_generate_forcontent(p):
    """generate_forcontent : generate_item
    | generate_block
    """
    p[0] = p[1]
    p.set_lineno(0, p.lineno(1))


# --------------------------------------------------------------------------
def p_systemcall_noargs(p):
    'systemcall : DOLLER ID'
    p[0] = SystemCall(p[2], (), lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_systemcall(p):
    'systemcall : DOLLER ID LPAREN sysargs RPAREN'
    p[0] = SystemCall(p[2], p[4], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_systemcall_signed(p):  # for $signed system task
    'systemcall : DOLLER SIGNED LPAREN sysargs RPAREN'
    p[0] = SystemCall(p[2], p[4], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_sysargs(p):
    'sysargs : sysargs COMMA sysarg'
    p[0] = p[1] + (p[3],)
    p.set_lineno(0, p.lineno(1))


def p_sysargs_one(p):
    'sysargs : sysarg'
    p[0] = (p[1],)
    p.set_lineno(0, p.lineno(1))


def p_sysargs_empty(p):
    'sysargs : empty'
    p[0] = ()


def p_sysarg(p):
    'sysarg : expression'
    p[0] = p[1]
    p.set_lineno(0, p.lineno(1))


# --------------------------------------------------------------------------
def p_function(p):
    'function : FUNCTION width ID SEMICOLON function_statement ENDFUNCTION'
    p[0] = Function(p[3], p[2], p[5], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_function_nowidth(p):
    'function : FUNCTION ID SEMICOLON function_statement ENDFUNCTION'
    p[0] = Function(p[2],
                    Width(IntConst('0', lineno=p.lineno(1)),
                          IntConst('0', lineno=p.lineno(1)),
                          lineno=p.lineno(1)),
                    p[4], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_function_integer(p):
    'function : FUNCTION INTEGER ID SEMICOLON function_statement ENDFUNCTION'
    p[0] = Function(p[3],
                    Width(IntConst('31', lineno=p.lineno(1)),
                          IntConst('0', lineno=p.lineno(1)),
                          lineno=p.lineno(1)),
                    p[5], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_function_statement(p):
    'function_statement : funcvardecls function_calc'
    p[0] = p[1] + (p[2],)
    p.set_lineno(0, p.lineno(1))


def p_funcvardecls(p):
    'funcvardecls : funcvardecls funcvardecl'
    p[0] = p[1] + (p[2],)
    p.set_lineno(0, p.lineno(1))


def p_funcvardecls_one(p):
    'funcvardecls : funcvardecl'
    p[0] = (p[1],)
    p.set_lineno(0, p.lineno(1))


def p_funcvardecl(p):
    """funcvardecl : decl
    | integerdecl
    """
    if isinstance(p[1], Decl):
        for r in p[1].list:
            if (not isinstance(r, Input) and not isinstance(r, Reg) and
                    not isinstance(r, Integer)):
                raise ParseError("Syntax Error")
    p[0] = p[1]
    p.set_lineno(0, p.lineno(1))


def p_function_calc(p):
    """function_calc : blocking_substitution
    | if_statement
    | for_statement
    | while_statement
    | case_statement
    | casex_statement
    | casez_statement
    | block
    | namedblock
    """
    p[0] = p[1]
    p.set_lineno(0, p.lineno(1))


def p_functioncall(p):
    'functioncall : identifier LPAREN func_args RPAREN'
    p[0] = FunctionCall(p[1], p[3], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_func_args(p):
    'func_args : func_args COMMA expression'
    p[0] = p[1] + (p[3],)
    p.set_lineno(0, p.lineno(1))


def p_func_args_one(p):
    'func_args : expression'
    p[0] = (p[1],)
    p.set_lineno(0, p.lineno(1))


def p_func_args_empty(p):
    'func_args : empty'
    p[0] = ()


# --------------------------------------------------------------------------
def p_task(p):
    'task : TASK ID SEMICOLON task_statement ENDTASK'
    p[0] = Task(p[2], p[4], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_task_statement(p):
    'task_statement : taskvardecls task_calc'
    p[0] = p[1] + (p[2],)
    p.set_lineno(0, p.lineno(1))


def p_taskvardecls(p):
    'taskvardecls : taskvardecls taskvardecl'
    p[0] = p[1] + (p[2],)
    p.set_lineno(0, p.lineno(1))


def p_taskvardecls_one(p):
    'taskvardecls : taskvardecl'
    p[0] = (p[1],)
    p.set_lineno(0, p.lineno(1))


def p_taskvardecls_empty(p):
    'taskvardecls : empty'
    p[0] = ()


def p_taskvardecl(p):
    """taskvardecl : decl
    | integerdecl
    """
    if isinstance(p[1], Decl):
        for r in p[1].list:
            if (not isinstance(r, Input) and not isinstance(r, Reg) and
                    not isinstance(r, Integer)):
                raise ParseError("Syntax Error")
    p[0] = p[1]
    p.set_lineno(0, p.lineno(1))


def p_task_calc(p):
    """task_calc : blocking_substitution
    | if_statement
    | for_statement
    | while_statement
    | case_statement
    | casex_statement
    | casez_statement
    | block
    | namedblock
    """
    p[0] = p[1]
    p.set_lineno(0, p.lineno(1))


# --------------------------------------------------------------------------
def p_identifier(p):
    'identifier : ID'
    p[0] = Identifier(p[1], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_scope_identifier(p):
    'identifier : scope ID'
    p[0] = Identifier(p[2], p[1], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


# --------------------------------------------------------------------------
def p_scope(p):
    'scope : identifier DOT'
    scope = () if p[1].scope is None else p[1].scope.labellist
    p[0] = IdentifierScope(
        scope + (IdentifierScopeLabel(p[1].name, lineno=p.lineno(1)),), lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_scope_pointer(p):
    'scope : pointer DOT'
    scope = () if p[1].var.scope is None else p[1].var.scope.labellist
    p[0] = IdentifierScope(scope + (IdentifierScopeLabel(p[1].var.name,
                                                         p[1].ptr, lineno=p.lineno(1)),), lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


# --------------------------------------------------------------------------
def p_disable(p):
    'disable : DISABLE ID'
    p[0] = Disable(p[2], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


# --------------------------------------------------------------------------
def p_single_statement_delays(p):
    'single_statement : DELAY expression SEMICOLON'
    p[0] = SingleStatement(DelayStatement(
        p[2], lineno=p.lineno(1)), lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_single_statement_systemcall(p):
    'single_statement : systemcall SEMICOLON'
    p[0] = SingleStatement(p[1], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


def p_single_statement_disable(p):
    'single_statement : disable SEMICOLON'
    p[0] = SingleStatement(p[1], lineno=p.lineno(1))
    p.set_lineno(0, p.lineno(1))


# fix me: to support task-call-statement
# def p_single_statement_taskcall(p):
#    'single_statement : functioncall SEMICOLON'
#    p[0] = SingleStatement(p[1], lineno=p.lineno(1))
#    p.set_lineno(0, p.lineno(1))

# def p_single_statement_taskcall_empty(p):
#    'single_statement : taskcall SEMICOLON'
#    p[0] = SingleStatement(p[1], lineno=p.lineno(1))
#    p.set_lineno(0, p.lineno(1))

# def p_taskcall_empty(p):
#    'taskcall : identifier'
#    p[0] = FunctionCall(p[1], (), lineno=p.lineno(1))
#    p.set_lineno(0, p.lineno(1))

# --------------------------------------------------------------------------
def p_empty(p):
    'empty : '
    pass


# --------------------------------------------------------------------------
def p_error(p):
    p.lexer._raise_parser_error(p)

# import token list for parser generator
from .lexer import tokens

# create one prototypical parser instance
_parser = yacc(method="LALR", debug=True, tabmodule="ply_parsetab")


#################################################
# Lexer Class
#################################################

class VerilogParser(object):
    'Verilog HDL Parser'


    def __init__(self):
        self.lexer = VerilogLexer(error_func=self._lexer_error_func)
        # we _hackily_ inject the parser error function into the lexer to make it available during parsing
        self.lexer.lexer._raise_parser_error = self._raise_error
        self.parser = _parser

    def _lexer_error_func(self, msg, line, column):
        coord = self._coord(line, column)
        raise ParseError('%s: %s' % (coord, msg))

    def get_directives(self):
        return self.lexer.get_directives()

    # Returns AST
    def parse(self, text, debug=0):
        return self.parser.parse(text, lexer=self.lexer.lexer, debug=debug)

    # --------------------------------------------------------------------------
    def _raise_error(self, p):
        if p:
            msg = 'before: "%s"' % p.value
            coord = self._coord(p.lineno)
        else:
            msg = 'at end of input'
            coord = None

        raise ParseError("%s: %s" % (coord, msg))

    def _coord(self, lineno, column=None):
        ret = [self.lexer.filename, 'line:%s' % lineno]
        if column is not None:
            ret.append('column:%s' % column)
        return ' '.join(ret)


class ParseError(Exception):
    pass


class VerilogCodeParser(object):

    def __init__(self, filelist, preprocess_output=None,
                 preprocess_include=None, preprocess_define=None):
        self.directives = ()
        self.preprocessor = VerilogPreprocessor(filelist, preprocess_output,
                                                preprocess_include,
                                                preprocess_define)
        self.parser = VerilogParser()

    def preprocess(self):
        self.preprocessor.preprocess()
        return self.preprocessor.read_output(remove=True)

    def parse(self, preprocess_output='preprocess.output', debug=0):
        text = self.preprocess()
        ast = self.parser.parse(text, debug=debug)
        self.directives = self.parser.get_directives()
        return ast

    def get_directives(self):
        return self.directives


def parse(
    filelist,
    preprocess_include=None,
    preprocess_define=None,
):
    codeparser = VerilogCodeParser(
        filelist,
        preprocess_include=preprocess_include,
        preprocess_define=preprocess_define,
    )
    ast = codeparser.parse()
    directives = codeparser.get_directives()
    return ast, directives
