# A temp file I use for building the database
from tinydb import TinyDB, Query
weapons = TinyDB('weapons.json')
weapons.truncate()
weapons.insert({
    "name": "fists",
    "type": "melee",
    "base-attack": 2,
    "random-attack": [0, 1],
    "chance-of-hit": 50,
    "cost": 0,
    "text-critical": "You deliver a smashing blow with your {}.",
    "text-normal": "You hit the {0} with your {1}.",
    "text-miss": "You flail your arms, failing to even touch the {}."
})
weapons.insert({

    "name": "dagger",
    "type": "melee",
    "base-attack": 1,
    "random-attack": [0, 5],
    "chance-of-hit": 50,
    "cost": 4,
    "text-critical": "You stab viciously with your {}.",
    "text-normal": "You hit the {0} with your {1}.",
    "text-miss": "You flail your dagger, failing to even touch the {}."

})
"""
{
    "name": "fists",
    "type": "melee",
    "base-attack": 2,
    "random-attack": [0, 1],
    "chance-of-hit": 50,
    "cost": 0,
    "text-critical": "You deliver a smashing blow with your {}.",
    "text-normal": "You hit the {0} with your {1}.",
    "text-miss": "You flail your arms, failing to even touch the {}."
}

{
    
    "name": "dagger",
    "type": "melee",
    "base-attack": 1,
    "random-attack": [0, 5],
    "chance-of-hit": 50,
    "cost": 4,
    "text-critical": "You stab viciously with your {}.",
    "text-normal": "You hit the {0} with your {1}.",
    "text-miss": "You flail your dagger, failing to even touch the {}."
}

"""
