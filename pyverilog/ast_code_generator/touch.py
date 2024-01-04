import os
import sys
import subprocess

with open('list_ast.txt', 'r') as f:
    text = f.read()
lines = text.split('\n')
for line in lines:
    if line != '':
        subprocess.call('touch template/' + line.lower() + '.txt', shell=True)
