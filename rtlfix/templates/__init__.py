# Copyright 2022 The Regents of the University of California
# released under BSD 3-Clause License
# author: Kevin Laeufer <laeufer@cs.berkeley.edu>

# export for outside world
from rtlfix.templates.add_inversions import add_inversions
from rtlfix.templates.replace_literals import replace_literals
from rtlfix.templates.replace_variables import replace_variables

# Template Ideas:
# - assign constant to variable in same always@ block that it is normally assigned under a synthesized condition
#   (this might help with some of the counter overflow things)
# -
