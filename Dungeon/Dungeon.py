# Workflow
from subprocess import call
import os
import Application.checkmodules as c
dependencies = ["fuckit", "pandas", "tinydb", "termcolor", "keyboard", "rich"]


c.check(dependencies, "dungeon")
os.system("cls")

call(["python", "Application/main.py"])
