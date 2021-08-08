# https://github.com/The-Duck-Syndicate/encry-duck/blob/master/encry-duck.py
from importlib import import_module
import os
from Application.loggers import Logger


logger = Logger()


def check(modules, name):
    """String[] modules"""
    logger.log("Importing libraries...")
    all_modules = modules["required"] + modules["optional"]
    for module in all_modules:
        logger.log(f"Trying to import {module}")
        try:
            globals()[module] = import_module(module)
            logger.log(f"Successfully imported {module}")
        except ModuleNotFoundError:
            while True:
                prompt_msg = f"{name} requires \"{module}\" to run." if module in modules["required"] else f"{module} is optional."
                kb = input(f"The module \"{module}\" not found, {prompt_msg}\nDo you want to install it? (y/n): ")
                os.system("cls")

                if kb.lower() in ["y", "n"]:
                    if kb.lower() == "n":
                        if module in modules["required"]:
                            logger.fatal(f"{module} install denied. {name} cannot run without {module}. Please install it manually and run {name} again!")
                        else:
                            break
                    else:
                        logger.log(f"attempting to install {module}")
                        try:
                            os.system(f"python -m pip install {module}")
                            os.system("cls")
                            globals()[module] = import_module(module)
                        except:
                            logger.fatal(
                                f"{module} failed to install. {name} cannot run without {module}. Please install it manually and run {name} again!")
                            logger.log(f"Successfully install and imported {module}")
                        break
                else:
                    print("Please enter either y/n!")
                    continue

