import json
import collections

from .enemies import DungeonEnemyLoader
from .people import DungeonPeopleLoader

class DungeonJSONDecoder:
	def __init__(self, game):
		self.game = game

	def load(self, file):
		with open(file, 'r') as f:
			data = json.load(f)
		return data

	def fetch_loaders(self, data_file, loader_class):
		data_list = self.load(data_file)
		decoded = []
		for data in data_list:
			decoded.append(loader_class(
				game=self.game,
				data=collections.namedtuple("Data", data.keys())(*data.values())
			))
		return decoded

	def fetch_enemies(self):
		return self.fetch_loaders(
			data_file="data/enemies.json",
			loader_class=DungeonEnemyLoader
		)

	def fetch_people(self):
		return self.fetch_loaders(
			data_file="data/people.json",
			loader_class=DungeonPeopleLoader
		)
