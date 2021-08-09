# https://github.com/The-Duck-Syndicate/encry-duck/blob/master/encry-duck.py
from importlib import import_module
import os

from Application.loggers import LogType

def check_modules(modules, name, logger):
    """String[] modules"""
    logger.log(LogType.INFO, "Importing libraries...")
    all_modules = modules["required"] + modules["optional"]
    for module in all_modules:
        logger.log(LogType.INFO, f"Trying to import {module}")
        try:
            globals()[module] = import_module(module)
            logger.log(LogType.INFO, f"Successfully imported {module}")
        except ModuleNotFoundError:
            while True:
                prompt_msg = f"{name} requires \"{module}\" to run." if module in modules["required"] else f"{module} is optional."
                kb = input(f"The module \"{module}\" not found, {prompt_msg}\nDo you want to install it? (y/n): ")
                os.system("cls")

                if kb.lower() in ["y", "n"]:
                    if kb.lower() == "n":
                        if module in modules["required"]:
                            logger.log(LogType.FATAL, f"{module} install denied. {name} cannot run without {module}. Please install it manually and run {name} again!")
                        else:
                            logger.log(LogType.INFO, f"{module} install denied. {name} can run without the optional {module}.")
                            break
                    else:
                        logger.log(LogType.INFO, f"attempting to install {module}")
                        try:
                            os.system(f"python -m pip install {module}")
                            os.system("cls")
                            globals()[module] = import_module(module)
                            logger.log(LogType.INFO, f"Successfully install and imported {module}")
                        except:
                            logger.log(LogType.FATAL, f"{module} failed to install. {name} cannot run without {module}. Please install it manually and run {name} again!")
                        break
                else:
                    print("Please enter either y/n!")
                    continue

