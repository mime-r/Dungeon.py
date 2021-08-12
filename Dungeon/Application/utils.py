import random
from .config import config

random_yx = lambda: (random.randint(1, config.map.max_y), random.randint(1, config.map.max_x))
style_text = lambda t, s: f"[{s}]{t}[/{s}]"
controls_style = lambda t: style_text(chr(92)+f"[{t}]", 'controls')