from .weapons import *

class DungeonItem:
	def __init__(self, name, description, cost, actions):
		self.name = name
		self.description = description
		self.cost = cost
		self.actions = actions

class DungeonWeapon(DungeonItem):
	def __init__(self, name, description, cost, type, base_attack, attack_range, accuracy, texts):
		super().__init__(
			name=name,
			description=description,
			cost=cost,
			actions=[ItemUseType.EQUIP]
		)
		self.type = type
		self.base_attack = base_attack
		self.attack_range = attack_range
		self.accuracy = accuracy
		self.texts = texts

class DungeonInventory(DungeonItem):
	def __init__(self, name, description, cost, inventory):
		super().__init__(
			name=name,
			description=description,
			cost=cost,
			actions=[ItemUseType.EQUIP]
		)
		self.inventory = inventory

class DungeonPotion(DungeonItem):
	def __init__(self, name, description, cost, hp_change):
		super().__init__(
			name=name,
			description=description,
			cost=cost,
			actions=[ItemUseType.USE]
		)
		self.hp_change = hp_change


class ItemUseType:
	EQUIP = "equip"
	USE = "use"

