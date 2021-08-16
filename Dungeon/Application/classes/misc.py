import time
from ..utils import style_text, controls_style
import keyboard

class DungeonTimeData:
	def __init__(self, game):
		self.game = game
		self.init = time.time()
		self.game.log.info(f"timer init at {self.init}")
		self.start = self.init
		self.elapsed = 0

	def add(self):
		self.elapsed += time.time() - self.start
		self.game.log.info(f"timer elapsed at {time.time()}")
		self.reset()

	def reset(self):
		self.start = time.time()
		self.game.log.info(f"timer resetted at {self.start}")

	def pause_menu(self):
		self.add()
		self.game.map.ui()
		self.game.print(f"""
Game is paused.
Press {controls_style('p')} to {style_text('unpause', 'action')}
""")
		time.sleep(.2)
		while True:
			if keyboard.is_pressed("p"):
				self.reset()
				self.game.map.print()
				break