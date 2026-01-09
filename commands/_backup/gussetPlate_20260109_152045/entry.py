import adsk.core
import adsk.fusion
import json
import math
import shutil
from pathlib import Path
from ...lib import fusionAddInUtils as futil

app = adsk.core.Application.get()
ui = app.userInterface

CMD_ID = 'ACME_SteelHelper_GussetPlate'
CMD_NAME = 'ガセットプレート配置'
CMD_Description = 'ユーザー作成モデルの登録/配置'

IS_PROMOTED = True
WORKSPACE_ID = 'FusionSolidEnvironment'
PANEL_ID = 'SolidCreatePanel'
COMMAND_BESIDE_ID = ''

local_handlers = []

def load_gusset_models():
    models = {}
    cfg = Path(__file__).parent / 'gusset_models.json'
    if cfg.exists():
        try:
            with open(cfg, 'r', encoding='utf-8') as f:
                models = json.load(f)
        except Exception as e:
            futil.log(f'ガセットモデル設定の読み込みエラー: {e}')
    return models

GUSSET_PLATE_MODELS = load_gusset_models()

def start():
    cmd_def = ui.commandDefinitions.itemById(CMD_ID)
    if not cmd_def:
        cmd_def = ui.commandDefinitions.addButtonDefinition(CMD_ID, CMD_NAME, CMD_Description, '')
        futil.add_handler(cmd_def.commandCreated, command_created)

    workspace = ui.workspaces.itemById(WORKSPACE_ID)
    if not workspace:
        futil.log(f'Workspace not found: {WORKSPACE_ID}')
        return

    panel_ids = [PANEL_ID, 'SolidScriptsAddinsPanel', 'SolidCreatePanel']
    added = False
    for pid in panel_ids:
        panel = workspace.toolbarPanels.itemById(pid)
        if not panel:
            futil.log(f'Panel not found: {pid}')
            continue
        existing = panel.controls.itemById(CMD_ID)
        if existing:
            existing.deleteMe()
        try:
            control = panel.controls.addCommand(cmd_def, COMMAND_BESIDE_ID or '', False)
        except Exception:
            try:
                control = panel.controls.addCommand(cmd_def, '', False)
            except Exception as e:
                futil.log(f'Failed to add control to panel {pid}: {e}', force_console=True)
                continue
        control.isPromoted = IS_PROMOTED
        added = True
    if not added:
        futil.log('Failed to add command to any known panels', force_console=True)

def stop():
    workspace = ui.workspaces.itemById(WORKSPACE_ID)
    if not workspace:
        return
    panel = workspace.toolbarPanels.itemById(PANEL_ID)
    if not panel:
        panel = workspace.toolbarPanels.itemById('SolidScriptsAddinsPanel')
    if panel:
        ctrl = panel.controls.itemById(CMD_ID)
        if ctrl:
            ctrl.deleteMe()
    cmd_def = ui.commandDefinitions.itemById(CMD_ID)
    if cmd_def:
        cmd_def.deleteMe()

def command_created(args: adsk.core.CommandCreatedEventArgs):
    futil.log(f'{CMD_NAME} コマンドが作成されました')
    inputs = args.command.commandInputs

    mode_input = inputs.addDropDownCommandInput('mode', 'モード', adsk.core.DropDownStyles.TextListDropDownStyle)
    mode_input.listItems.add('登録済みモデル配置', True)
    mode_input.listItems.add('ファイルから登録', False)

    inputs.addStringValueInput('register_name', '登録名', '')
    inputs.addStringValueInput('register_desc', '説明', '')
    inputs.addStringValueInput('register_path', 'ファイルパス', '')
    inputs.addBoolValueInput('browse_file', 'ファイルを選択...', False, '', False)

    model_input = inputs.addDropDownCommandInput('model', 'ガセットプレートモデル', adsk.core.DropDownStyles.TextListDropDownStyle)
    refresh_model_list(model_input)

    inputs.addSelectionInput('target_sel', '配置先', '面/点/エッジを選択')
    inputs.itemById('target_sel').addSelectionFilter('PlanarFaces')
    inputs.itemById('target_sel').addSelectionFilter('Vertices')
    inputs.itemById('target_sel').addSelectionFilter('Edges')
    inputs.itemById('target_sel').setSelectionLimits(0, 1)

    # 初期表示: 配置モードを表示
    set_visibility(inputs, '登録済みモデル配置')

    futil.add_handler(args.command.execute, command_execute, local_handlers=local_handlers)
    futil.add_handler(args.command.inputChanged, command_input_changed, local_handlers=local_handlers)
    futil.add_handler(args.command.destroy, command_destroy, local_handlers=local_handlers)

def refresh_model_list(model_input: adsk.core.DropDownCommandInput):
    model_input.listItems.clear()
    global GUSSET_PLATE_MODELS
    GUSSET_PLATE_MODELS = load_gusset_models()
    if GUSSET_PLATE_MODELS:
        for name in GUSSET_PLATE_MODELS.keys():
            model_input.listItems.add(name, False)
        model_input.listItems.item(0).isSelected = True
        model_input.isEnabled = True
    else:
        model_input.listItems.add('モデルが登録されていません', True)
        model_input.isEnabled = False

def set_visibility(inputs: adsk.core.CommandInputs, mode: str):
    register_inputs = ['register_name', 'register_desc', 'register_path', 'browse_file']
    place_inputs = ['model', 'target_sel']
    for i in register_inputs:
        inp = inputs.itemById(i)
        if inp:
            inp.isVisible = (mode == 'ファイルから登録')
    for i in place_inputs:
        inp = inputs.itemById(i)
        if inp:
            inp.isVisible = (mode == '登録済みモデル配置')

def command_execute(args: adsk.core.CommandEventArgs):
    inputs = args.command.commandInputs
    mode = inputs.itemById('mode').selectedItem.name

    if mode == 'ファイルから登録':
        reg_name_input = inputs.itemById('register_name')
        reg_name = reg_name_input.value.strip()
        reg_desc = inputs.itemById('register_desc').value.strip()
        reg_path = inputs.itemById('register_path').value.strip()
        # パスがあればデフォルト登録名を自動付与（ファイル名＝登録名）
        if reg_path and not reg_name:
            reg_name = Path(reg_path).stem
            reg_name_input.value = reg_name
        if not reg_name:
            ui.messageBox('登録名を入力してください')
            return
        if not reg_path:
            reg_path = _open_file_dialog()
            if not reg_path:
                return
            inputs.itemById('register_path').value = reg_path
        if not Path(reg_path).exists():
            ui.messageBox(f'指定のファイルが見つかりません:\n{reg_path}')
            return
        register_model_to_json(reg_name, reg_path, reg_desc or 'ユーザー登録モデル')
        ui.messageBox(f'モデル"{reg_name}"を登録しました')
        refresh_model_list(inputs.itemById('model'))
    else:
        model_name = inputs.itemById('model').selectedItem.name
        target_sel = inputs.itemById('target_sel')
        placement_point = adsk.core.Point3D.create(0, 0, 0)
        if target_sel and target_sel.selectionCount > 0:
            try:
                placement_point = target_sel.selection(0).point
            except Exception:
                placement_point = adsk.core.Point3D.create(0, 0, 0)
        place_gusset_model(model_name, placement_point)

def command_input_changed(args: adsk.core.InputChangedEventArgs):
    changed = args.input
    inputs = args.inputs
    if changed.id == 'mode':
        set_visibility(inputs, changed.selectedItem.name)
    if changed.id == 'browse_file' and changed.value:
        path = _open_file_dialog()
        if path:
            inputs.itemById('register_path').value = path
            name_input = inputs.itemById('register_name')
            if name_input and not name_input.value.strip():
                name_input.value = Path(path).stem
        changed.value = False

def command_destroy(args: adsk.core.CommandEventArgs):
    global local_handlers
    local_handlers = []

def register_model_to_json(model_name: str, model_path: str, description: str = ''):
    try:
        base_dir = Path(__file__).parent
        cfg = base_dir / 'gusset_models.json'
        models_dir = base_dir / 'models'
        models_dir.mkdir(exist_ok=True)
        
        # モデルファイルをローカルディレクトリにコピー
        src_path = Path(model_path)
        if not src_path.exists():
            ui.messageBox(f'ソースファイルが見つかりません:\n{model_path}')
            return
        
        # ファイル名を保持してコピー
        local_file_name = src_path.name
        local_file_path = models_dir / local_file_name
        
        # 同じ名前のファイルが既に存在する場合は上書き
        shutil.copy2(str(src_path), str(local_file_path))
        futil.log(f'モデルファイルをコピー: {src_path} -> {local_file_path}')
        
        # JSON に相対パスで保存
        relative_path = str(local_file_path.relative_to(base_dir)).replace('\\', '/')
        
        # JSON ファイルを読み込んで更新
        models = {}
        if cfg.exists():
            with open(cfg, 'r', encoding='utf-8') as f:
                models = json.load(f)
        
        models[model_name] = {'path': relative_path, 'description': description or 'ユーザー登録モデル'}
        
        with open(cfg, 'w', encoding='utf-8') as f:
            json.dump(models, f, ensure_ascii=False, indent=2)
        
        global GUSSET_PLATE_MODELS
        GUSSET_PLATE_MODELS = models
        futil.log(f'モデル登録完了: {model_name}')
    except Exception as e:
        ui.messageBox(f'モデル登録に失敗しました: {e}')
        futil.log(f'登録エラー: {e}')

def _open_file_dialog() -> str:
    try:
        dlg = ui.createFileDialog()
        dlg.isMultiSelectEnabled = False
        dlg.title = 'モデルファイルを選択 (f3d/step/iges)'
        dlg.filter = 'Fusion 360 Archive (*.f3d);;STEP Files (*.step; *.stp);;IGES Files (*.iges; *.igs);;All Files (*.*)'
        dlg.filterIndex = 0
        dlg.initialDirectory = str((Path(__file__).parent / 'models').resolve())
        res = dlg.showOpen()
        if res == adsk.core.DialogResults.DialogOK:
            return dlg.filename
    except Exception as e:
        futil.log(f'ファイルダイアログエラー: {e}')
    return ''

def place_gusset_model(model_name: str, placement_point: adsk.core.Point3D):
    try:
        design = adsk.fusion.Design.cast(app.activeProduct)
        if not design:
            ui.messageBox('アクティブなデザインがありません')
            return
        model_info = GUSSET_PLATE_MODELS.get(model_name)
        if not model_info:
            ui.messageBox(f'モデル {model_name} が見つかりません')
            return
        model_path = model_info.get('path')
        if not model_path:
            ui.messageBox(f'モデル {model_name} のパスが設定されていません')
            return
        
        # 相対パスの場合は絶対パスに変換
        model_path_obj = Path(model_path)
        if not model_path_obj.is_absolute():
            base_dir = Path(__file__).parent
            model_path_obj = base_dir / model_path_obj
        
        if not model_path_obj.exists():
            ui.messageBox(f'モデルファイルが見つかりません:\n{model_path_obj}')
            return

        # 配置位置（選択点をそのまま使用）
        base_pt = placement_point or adsk.core.Point3D.create(0, 0, 0)
        matrix = adsk.core.Matrix3D.create()
        matrix.translation = adsk.core.Vector3D.create(base_pt.x, base_pt.y, base_pt.z)

        occs = design.rootComponent.occurrences
        before_count = occs.count
        try:
            import_manager = app.importManager
            opts = None
            ext = model_path_obj.suffix.lower()
            if ext == '.f3d':
                opts = import_manager.createFusionArchiveImportOptions(str(model_path_obj))
            elif ext in ('.step', '.stp'):
                opts = import_manager.createSTEPImportOptions(str(model_path_obj))
            elif ext in ('.iges', '.igs'):
                opts = import_manager.createIGESImportOptions(str(model_path_obj))
            else:
                opts = import_manager.createImportOptions(str(model_path_obj))

            import_manager.importToTarget(opts, design.rootComponent)
            after_count = occs.count
            if after_count > before_count:
                occ = occs.item(after_count - 1)
                occ.transform = matrix
                try:
                    occ.name = model_name
                    if occ.component:
                        occ.component.name = model_name
                except Exception as rename_err:
                    futil.log(f'モデル名設定エラー: {rename_err}')
            ui.messageBox(f'ガセットプレート"{model_name}"を配置しました')
        except Exception as e1:
            ui.messageBox(f'モデルの配置に失敗しました:\n{e1}')
            futil.log(f'モデル配置エラー: {e1}')
    except Exception as e:
        ui.messageBox(f'エラーが発生しました: {e}')
        futil.log(f'エラー: {e}')