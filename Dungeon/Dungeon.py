# Standard Imports
import os, sys

# App Imports
from Application.modules import check_modules
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
	logger.debug(f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
	check_modules(
		modules=dependencies,
		name="dungeon",
		logger=logger
	)

	import Application.main as dungeon
	dungeon.main(
		logger=logger
	)
