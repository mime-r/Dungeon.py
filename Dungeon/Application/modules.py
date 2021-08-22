# https://github.com/The-Duck-Syndicate/encry-duck/blob/master/encry-duck.py
from importlib import import_module
from subprocess import getoutput
import os
import platform

from Application.loggers import LogType

def check_modules(modules, name, logger):
    """String[] modules"""
    logger.debug(f"starting import checks with {getoutput('python3 --version') if platform.system() == 'Linux' else getoutput('python --version')}")
    logger.info("Importing libraries...")
    all_modules = modules["required"] + modules["optional"]
    for module in all_modules:
        logger.info(f"Trying to import {module}")
        try:
            globals()[module] = import_module(module)
            logger.info(f"Successfully imported {module}")
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
                            logger.info(f"{module} install denied. {name} can run without the optional {module}.")
                            break
                    else:
                        logger.info(f"attempting to install {module}")
                        try:
                            os.system(f"{'python3' if platform.system() == 'Linux' else 'python'} -m pip install {module}")
                            os.system("cls")
                            globals()[module] = import_module(module)
                            logger.info(f"Successfully install and imported {module}")
                        except:
                            logger.info(f"{module} failed to install. {name} cannot run without {module}. Please install it manually and run {name} again!")
                        break
                else:
                    print("Please enter either y/n!")
                    continue

