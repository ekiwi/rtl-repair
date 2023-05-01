#!/usr/bin/env bash

# create virtual environment
python3 -m venv venv

# install pyverilog
source venv/bin/activate
pip install wheel # for some reason pyverilog installation fails on some machines without
pip install pyverilog==1.2.1
pip install tomli # for benchmark descriptions in TOML format
pip install psutil # kills_vcs.py

# patch pyverilog
cp pyverilog_changes/codegen.py venv/lib/python3.*/site-packages/pyverilog/ast_code_generator/
cp pyverilog_changes/ast.py venv/lib/python3.*/site-packages/pyverilog/vparser/
cp pyverilog_changes/parser.py venv/lib/python3.*/site-packages/pyverilog/vparser/
cp pyverilog_changes/ast_classes.txt venv/lib/python3.*/site-packages/pyverilog/vparser/

