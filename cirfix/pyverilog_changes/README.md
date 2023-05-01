# There are some changes needed to the off-the-shelf PyVerilog to work with Cirfix:

You need to replace the files in <home>/.local/lib/python3.6/site-packages/pyverilog/ (or equivalent directory where Python stores the site packages).
  
The following files need to be replaced:

    codegen.py -> <home>/.local/lib/python3.6/site-packages/pyverilog/ast_code_generator/codegen.py
    ast.py -> <home>/.local/lib/python3.6/site-packages/pyverilog/vparser/ast.py
    parser.py -> <home>/.local/lib/python3.6/site-packages/pyverilog/vparser/parser.py
    ast_classes.txt -> <home>/.local/lib/python3.6/site-packages/pyverilog/vparser/ast_classes.txt
