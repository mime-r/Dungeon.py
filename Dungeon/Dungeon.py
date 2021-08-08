# Workflow
from subprocess import call
import os
import Application.checkmodules as c
dependencies = {
	"required": [
		"fuckit",
		"pandas",
		"tinydb",
		"termcolor",
		"keyboard",
		"rich"
	],
	"optional": [
		"names"
	]
}


c.check(dependencies, "dungeon")
os.system("cls")

call(["python", "Application/main.py"])
