import time
import sys

import keyboard
from rich.console import Console
from rich.theme import Theme

from .config import config
from .utils import style_text, controls_style, clear_screen
from .main import Dungeon

class GameWrapper:
	def __init__(self, logger):
		self.logger = logger
		self.rich_console = Console(
			theme=Theme(config.styles)
		)
		self.print = self.rich_console.print

		clear_screen()
		self.print(r"""
      _                                          
     | |                                         
   __| | _   _  _ __    __ _   ___   ___   _ __  
  / _` || | | || '_ \  / _` | / _ \ / _ \ | '_ \ 
 | (_| || |_| || | | || (_| ||  __/| (_) || | | |
  \__,_| \__,_||_| |_| \__, | \___| \___/ |_| |_|
                        __/ |                    
                       |___/                     
""", highlight=False)
		self.print(f"""
Welcome to dungeon.py!
Press {controls_style('enter')} to {style_text('start', 'action')}.
Press {controls_style('esc')} to {style_text('exit', 'action')}.
""", highlight=False)
		while True:
			if keyboard.read_key():
				if keyboard.is_pressed("enter"):
					input()
					time.sleep(.2)
					Dungeon.__start__(
						logger=self.logger,
						rich_console=self.rich_console
					)
				elif keyboard.is_pressed("esc"):
					print("Exiting [Dungeon]...")
					self.logger.info(f"game exited at {time.time():.2f}")
					sys.exit()
