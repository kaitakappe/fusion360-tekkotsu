# Assuming you have not changed the general structure of the template no modification is needed in this file.
from . import commands
from .lib import fusionAddInUtils as futil
from pathlib import Path
import base64
import os
# icon_binaries may not be present in this distribution; we don't require it.


def _ensure_png_icons():
    try:
        base = Path(__file__).parent
        icons_dir = base / 'resources' / 'icons'
        icons_dir.mkdir(parents=True, exist_ok=True)
        # If icon binaries module is not available, assume icons are shipped
        # under resources/icons. Nothing more to do here.
        return
    except Exception:
        # best-effort only
        return


def run(context):
    try:
        _ensure_png_icons()
        # This will run the start function in each of your commands as defined in commands/__init__.py
        commands.start()

    except:
        futil.handle_error('run')


def stop(context):
    try:
        # Remove all of the event handlers your app has created
        futil.clear_handlers()

        # This will run the start function in each of your commands as defined in commands/__init__.py
        commands.stop()

    except:
        futil.handle_error('stop')