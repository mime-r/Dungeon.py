# Workflow

import Application.main as m
import os
import Application.checkmodules as c
dependencies = ["fuckit", "pandas", "tinydb", "termcolor", "keyboard"]


c.check(dependencies, "dungeon")
os.system("cls")
