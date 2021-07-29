# https://github.com/The-Duck-Syndicate/encry-duck/blob/master/encry-duck.py
from importlib import import_module
import os
from Application.loggers import Logger


logger = Logger()


def check(modules, name):
    """String[] modules"""
    logger.log("Importing libraries...")
    for library in modules:
        logger.log(f"Trying to import {library}")
        try:
            globals()[library] = import_module(library)
            logger.log(f"Successfully imported {library}")
        except ModuleNotFoundError:
            while True:
                kb = input(
                    f"The module \"{library}\" not found, {name} requires \"{library}\" to run.\nDo you want to install it? (y/n): ")
                os.system("cls")

                if kb.lower() in ["y", "n"]:
                    if kb.lower() == "n":
                        logger.fatal(
                            f"{library} install denied. {name} cannot run without {library}. Please install it manually and run {name} again!")
                    else:
                        break
                else:
                    print("Please enter either y/n!")
                    continue
            logger.log(f"attempting to install {library}")
            try:
                os.system(f"python -m pip install {library}")
                os.system("cls")
                globals()[library] = import_module(library)
            except:
                logger.fatal(
                    f"{library} failed to install. {name} cannot run without {library}. Please install it manually and run {name} again!")
                logger.log(f"Successfully install and imported {library}")
