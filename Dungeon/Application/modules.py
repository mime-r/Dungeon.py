# https://github.com/The-Duck-Syndicate/encry-duck/blob/master/encry-duck.py
import importlib
import os
import platform
import subprocess
import sys
from importlib import import_module


def _clear():
    os.system("cls" if platform.system() == "Windows" else "clear")


def _pip_install(module, logger) -> bool:
    """Install *module* into the interpreter that is actually running the game.

    Uses ``sys.executable`` (not a bare ``python``/``python3`` from PATH, which may be a
    different, pip-less interpreter) and bootstraps pip via ensurepip when it is missing.
    """
    exe = sys.executable
    if subprocess.run([exe, "-m", "pip", "--version"]).returncode != 0:
        logger.info("pip not found in this interpreter; bootstrapping with ensurepip")
        subprocess.run([exe, "-m", "ensurepip", "--upgrade"])
    result = subprocess.run([exe, "-m", "pip", "install", module])
    importlib.invalidate_caches()
    return result.returncode == 0


def check_modules(modules, name, logger):
    """Ensure every required (and offered optional) module can be imported."""
    logger.debug(f"starting import checks with {sys.executable} ({platform.python_version()})")
    logger.info("Importing libraries...")
    all_modules = modules["required"] + modules["optional"]
    for module in all_modules:
        logger.info(f"Trying to import {module}")
        try:
            globals()[module] = import_module(module)
            logger.info(f"Successfully imported {module}")
            continue
        except ModuleNotFoundError:
            pass

        required = module in modules["required"]
        while True:
            prompt_msg = f"{name} requires \"{module}\" to run." if required else f"\"{module}\" is optional."
            kb = input(f"The module \"{module}\" was not found. {prompt_msg}\nInstall it now? (y/n): ").strip().lower()
            if kb not in ("y", "n"):
                print("Please enter either y or n.")
                continue
            _clear()
            if kb == "n":
                if required:
                    logger.fatal(
                        f"{module} is required and was not installed.\n"
                        f"Install it manually with:\n    \"{sys.executable}\" -m pip install {module}\n"
                        f"or run the game with the 'py' launcher (py Dungeon.py)."
                    )
                else:
                    logger.info(f"{module} install declined; {name} can run without it.")
                break

            logger.info(f"attempting to install {module} into {sys.executable}")
            installed = False
            try:
                installed = _pip_install(module, logger)
                if installed:
                    globals()[module] = import_module(module)
                    logger.info(f"Successfully installed and imported {module}")
            except Exception as exc:
                logger.info(f"{module} install raised: {exc}")
                installed = False
            _clear()
            if not installed and required:
                logger.fatal(
                    f"Could not install {module} automatically (this interpreter may lack pip).\n"
                    f"Install it manually with:\n    \"{sys.executable}\" -m pip install {module}\n"
                    f"or run the game with the 'py' launcher (py Dungeon.py), which uses a Python that has it."
                )
            break
