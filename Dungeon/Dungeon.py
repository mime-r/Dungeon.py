# Standard Imports
import os

# App Imports
from Application.checkmodules import check_modules
from Application.loggers import Logger


dependencies = {
	"required": [
		"pandas",
		"tinydb",
		"keyboard",
		"rich"
	],
	"optional": [
		"names"
	]
}

if __name__ == "__main__":
	logger = Logger()
	check_modules(
		modules=dependencies,
		name="dungeon",
		logger=logger
	)

	import Application.main as dungeon
	dungeon.main(
		logger=logger
	)
