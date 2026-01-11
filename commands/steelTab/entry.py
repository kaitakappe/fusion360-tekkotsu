import adsk.core
import adsk.fusion
from ...lib import fusionAddInUtils as futil

app = adsk.core.Application.get()
ui = app.userInterface

PANEL_ID = 'SteelPanel'
PANEL_NAME = '鋼材'
WORKSPACE_ID = 'FusionSolidEnvironment'


def start():
    try:
        workspace = ui.workspaces.itemById(WORKSPACE_ID)
        if not workspace:
            futil.log(f'Workspace not found: {WORKSPACE_ID}')
            return

        panel = workspace.toolbarPanels.itemById(PANEL_ID)
        if not panel:
            try:
                panel = workspace.toolbarPanels.add(PANEL_ID, PANEL_NAME, 'SolidCreatePanel', False)
            except Exception as e:
                futil.log(f'パネル作成に失敗しました: {e}', force_console=True)
                return

        # 既存の steelPlateModule コマンドを参照してコントロールを追加
        cmd_id = 'ACME_SteelHelper_SteelPlateModule'
        existing = panel.controls.itemById(cmd_id)
        if existing:
            existing.deleteMe()
        try:
            cmd_def = ui.commandDefinitions.itemById(cmd_id)
            if not cmd_def:
                futil.log(f'コマンド定義が見つかりません: {cmd_id}', force_console=True)
            else:
                try:
                    ctrl = panel.controls.addCommand(cmd_def, '', False)
                except Exception:
                    ctrl = panel.controls.addCommand(cmd_def, '', False)
                ctrl.isPromoted = True
        except Exception as e:
            futil.log(f'コントロールの追加に失敗しました: {e}', force_console=True)

    except Exception:
        futil.handle_error('steelTab.start')


def stop():
    try:
        workspace = ui.workspaces.itemById(WORKSPACE_ID)
        if not workspace:
            return
        panel = workspace.toolbarPanels.itemById(PANEL_ID)
        if panel:
            cmd_ctrl = panel.controls.itemById('ACME_SteelHelper_SteelPlateModule')
            if cmd_ctrl:
                cmd_ctrl.deleteMe()
            try:
                panel.deleteMe()
            except Exception:
                pass
    except Exception:
        futil.handle_error('steelTab.stop')
