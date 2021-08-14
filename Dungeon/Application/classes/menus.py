import os
import time
import keyboard
from ..utils import style_text, controls_style
from .items import DungeonInventory, DungeonPotion

class DungeonMenu:
	def __init__(self, game):
		self.game = game
		self.header = DungeonHeaders(game=self.game)
		self.function = DungeonMenuFunctions
		self.context = lambda function, header, footer=None, trader=None: (
			DungeonMenuContext(
				game=self.game,
				header=header,
				footer=footer,
				function=function,
				trader=trader
			)
		)

	def inventory(self, menu_context):
		footer, header = menu_context.footer, menu_context.header
		inventory = menu_context.trader.stuff if menu_context.trader else self.game.player.inventory
		header()
		footer()
		while True:
			pressed = keyboard.read_key()
			if pressed.isnumeric():
				pressed = int(pressed)
				header()
				if not ((pressed < len(inventory)+1) and (1 <= pressed)):
					print("You have chosen an invalid choice.\n")
					time.sleep(0.2)
					footer()
					continue
				selected_item = inventory[pressed-1]
				menu_context.function(ctx=DungeonMenuFunctionContext(
					game=self.game,
					selected_item=selected_item,
					pressed=pressed,
					header=header
				))
				time.sleep(0.2)
				footer()
			if pressed == "e":
				break

class DungeonMenuFunctions:
	@staticmethod
	def trader(ctx):
		item, game = ctx.selected_item, ctx.game
		if game.player.coins >= item.cost:
			if len(game.player.inventory) == game.player.max_inventory:
				print("Your inventory is full.\n")
			else:
				print("You have bought the {}\n".format(item.name))
				game.player.inventory.append(item)
				game.player.coins -= item.cost
		else:
			game.print("You do not have enough money to buy the {}.\n".format(style_text(item.name, 'item')))

	@staticmethod
	def equip(ctx):
		item, game = ctx.selected_item, ctx.game
		if isinstance(item, DungeonInventory):
			game.print("You sling the {} over your shoulders.\n".format(
				style_text(item.name, 'item')))
			del game.player.inventory[ctx.pressed-1]
			game.player.max_inventory += item.inventory
		elif isinstance(item, DungeonPotion):
			if game.player.health == game.player.max_health:
				print(
					"You are already at maximum health. Try drinking a maximum-health increasing potion.\n")
			else:
				if (game.player.health + item.hp_change) > game.player.max_health:
					game.player.health = game.player.max_health
				else:
					game.player.health += item.hp_change
				game.print("You drink the {}. The strong elixir makes you feel rejuvenated.\n".format(style_text(item.name, 'item')))
				del game.player.inventory[ctx.pressed-1]

	@staticmethod
	def drop(ctx):
		item, game = ctx.selected_item, ctx.game
		game.print(f"Do you want to drop the {style_text(item.name, 'item')}?\nPress {controls_style('y')} for {style_text('Yes', 'action')} and {controls_style('n')} for {style_text('No', 'action')}.", highlight=False)
		while True:
			if keyboard.is_pressed("y"):
				ctx.header()
				del game.player.inventory[ctx.pressed-1]
				game.print(f"You have dropped the {style_text(item.name, 'item')}!\n")
				break
			elif keyboard.is_pressed("n"):
				ctx.header()
				game.print(f"You do not drop the {style_text(item.name, 'item')}.\n")
				break

class DungeonMenuContext:
	def __init__(self, game, header, footer, function, trader):
		self.game = game
		self.header = header
		self.footer = footer if footer else lambda: (
			self.game.player.print_inventory(),
			self.game.print(f"\nPress {controls_style('e')} to {style_text('exit', 'action')}.", highlight=False)
		)
		self.function = function
		self.trader = trader

class DungeonMenuFunctionContext:
	def __init__(self, game, selected_item, pressed, header):
		self.game = game
		self.selected_item = selected_item
		self.pressed = pressed
		self.header = header

class DungeonHeaders:
	def __init__(self, game):
		self.game = game

	def menu(self, menu_name):
		os.system('cls')
		self.game.print(f"{menu_name} Menu\n", style="menu_header", highlight=False)

	def trader(self, trader):
		os.system('cls')
		self.game.print(f"{style_text(trader.name, 'name')} - {style_text(trader.occupation, 'occupation')}\n", highlight=False)
		for index, item in enumerate(trader.stuff):
			self.game.print(f"{index+1}: {style_text(item.name, 'item')} {style_text(item.cost, 'coin')}", highlight=False)
			self.game.print(f"\t {item.description}")
		print("\n")
