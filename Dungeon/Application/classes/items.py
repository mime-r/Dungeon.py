
class DungeonItem:
	def __init__(self, name, description, cost, actions):
		self.name = name
		self.description = description
		self.cost = cost
		self.actions = actions

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

class DungeonItemDatabase:
	potions = [
		DungeonPotion(
			name="Weak Healing Potion",
			description="This berry-flavoured weak healing potion increases your health by 7",
			cost=2,
			hp_change=7
		),
		DungeonPotion(
			name="Medium Healing Potion",
			description="This concentrated berry-flavoured medium healing potion increases your health by 15.",
			cost=6,
			hp_change=15
		),
		DungeonPotion(
			name="Strong Healing Potion",
			description="This super-concentrated berry-flavoured strong healing potion increases your health by 25.",
			cost=12,
			hp_change=25
		)
	]
	items = [
		DungeonInventory(
			name="Cloth Bag",
			description="This useful cloth bag increases your inventory storage by 4.",
			cost=5,
			inventory=4
		)
	] + potions

	@classmethod
	def search_item(cls, name):
		results = list(filter(
			lambda item: item.name == name,
			cls.items
		))
		if len(results) == 0:
			return None
		return results[0]