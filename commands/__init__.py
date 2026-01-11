from ..lib import fusionAddInUtils as futil

# Here you define the commands that will be added to your add-in.

# TODO Import the modules corresponding to the commands you created.
# If you want to add an additional command, duplicate one of the existing directories and import it here.
# You need to use aliases (import "entry" as "my_module") assuming you have the default module named "entry".
from .commandDialog import entry as commandDialog
from .paletteShow import entry as paletteShow
from .paletteSend import entry as paletteSend
from .steelPlateModule import entry as steelPlateModule
from .steelTab import entry as steelTab
from .splicePlate import entry as splicePlate
from .gussetPlate import entry as gussetPlate

# TODO add your imported modules to this list.
# Fusion will automatically call the start() and stop() functions.
commands = [
    commandDialog,
    paletteShow,
    paletteSend,
    steelPlateModule,
    steelTab,
    # splicePlate,  # Disabled
    # gussetPlate   # Disabled
]


# Assumes you defined a "start" function in each of your modules.
# The start function will be run when the add-in is started.
def start():
    for command in commands:
        try:
            command.start()
            futil.log(f'command started: {command.__name__}', force_console=True)
        except Exception:
            futil.handle_error(f'{command.__name__}.start', show_message_box=False)

    # Diagnostic: log command definitions' resource folders to help icon troubleshooting
    try:
        import adsk.core
        app = adsk.core.Application.get()
        ui = app.userInterface
        cmd_ids = [
            'ACME_SteelHelper_SteelPlateModule',
            # 'ACME_SteelHelper_SplicePlate',  # Disabled
            # 'ACME_SteelHelper_GussetPlate',  # Disabled
            'ACME_SteelHelper_PaletteShow',
            'ACME_SteelHelper_PaletteSend',
            'ACME_SteelHelper_CommandDialog'
        ]
        for cid in cmd_ids:
            try:
                cd = ui.commandDefinitions.itemById(cid)
                if cd:
                    try:
                        # Some Fusion versions may not expose resourceFolder; guard it
                        rf = getattr(cd, 'resourceFolder', None)
                        futil.log(f'CMD {cid}: resourceFolder={rf}', force_console=True)
                    except Exception:
                        futil.log(f'CMD {cid}: resourceFolder unavailable', force_console=True)
                else:
                    futil.log(f'CMD {cid}: definition not found', force_console=True)
            except Exception as e:
                futil.log(f'CMD {cid}: error reading definition: {e}', force_console=True)
    except Exception as e:
        futil.log(f'command resource diagnostic failed: {e}', force_console=True)


# Assumes you defined a "stop" function in each of your modules.
# The stop function will be run when the add-in is stopped.
def stop():
    for command in commands:
        try:
            command.stop()
            futil.log(f'command stopped: {command.__name__}', force_console=True)
        except Exception:
            futil.handle_error(f'{command.__name__}.stop', show_message_box=False)