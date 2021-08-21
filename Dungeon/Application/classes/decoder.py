import json
import collections

from .enemies import DungeonEnemyLoader

class DungeonJSONDecoder:
	def __init__(self, game):
		self.game = game

	def load(self, file):
		with open(file, 'r') as f:
			data = json.load(f)
		return data

	def fetch_enemies(self):
		enemy_data_list = self.load("data/enemies.json")
		decoded = []
		for data in enemy_data_list:
			decoded.append(DungeonEnemyLoader(
				game=self.game,
				enemy_data=collections.namedtuple('EnemyData', data.keys())(*data.values())
			))
		return decoded








