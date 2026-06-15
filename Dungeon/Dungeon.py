# Standard Imports
import os, sys

# Ensure unicode glyphs (block bars, box drawing) never crash on legacy code pages.
for _stream in (sys.stdout, sys.stderr):
	try:
		_stream.reconfigure(encoding="utf-8", errors="replace")
	except Exception:
		pass

# App Imports
from Application.modules import check_modules
from Application.loggers import Logger


dependencies = {
	"required": [
		"tinydb",
		"rich"
	],
	"optional": []
}

if __name__ == "__main__":
	logger = Logger()
	logger.debug(f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
	check_modules(
		modules=dependencies,
		name="dungeon",
		logger=logger
	)

	from Application.wrapper import GameWrapper
	GameWrapper(logger=logger)
