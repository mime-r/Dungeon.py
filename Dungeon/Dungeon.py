# Workflow


import os
import Application.checkmodules as c
dependencies = ["fuckit", "pandas", "tinydb", "termcolor", "keyboard"]


c.check(dependencies, "dungeon")
os.system("cls")

# only start the application after modules are checked.
import Application.main as m
