import adsk.core
import adsk.fusion
import os
import json
import shutil
from ...lib import fusionAddInUtils as futil
from ... import config
from pathlib import Path
import math

app = adsk.core.Application.get()
ui = app.userInterface

CMD_ID = 'ACME_SteelHelper_SplicePlate'
CMD_NAME = 'スプライスプレート作成'
CMD_Description = 'H形鋼用スプライスプレートを作成します'

IS_PROMOTED = True

WORKSPACE_ID = 'FusionSolidEnvironment'
PANEL_ID = 'SolidCreatePanel'
COMMAND_BESIDE_ID = ''

local_handlers = []

def load_splice_models():
    models = {}
    cfg = Path(__file__).parent / 'splice_models.json'
    if cfg.exists():
        try:
            with open(cfg, 'r', encoding='utf-8') as f:
                models = json.load(f)
        except Exception as e:
            futil.log(f'スプライスモデル設定の読み込みエラー: {e}')
    return models

SPLICE_PLATE_MODELS = load_splice_models()

# スプライスプレートの種類と寸法データ（H鋼フランジ部用）
SPLICE_PLATE_TYPES = {
    # H200用
    'H200用A1': {'width': 285, 'height': 100, 'thickness': 9, 'hole_dia': 18, 
                 'holes': [(40,18), (100,18), (185,18), (245,18), (40,82), (100,82), (185,82), (245,82)]},
    'H200用A2': {'width': 285, 'height': 100, 'thickness': 12, 'hole_dia': 18, 
                 'holes': [(40,18), (100,18), (185,18), (245,18), (40,82), (100,82), (185,82), (245,82)]},
    
    # H250用
    'H250用A3': {'width': 285, 'height': 125, 'thickness': 9, 'hole_dia': 18, 
                 'holes': [(40,25), (100,25), (185,25), (245,25), (40,100), (100,100), (185,100), (245,100)]},
    'H250用A4': {'width': 285, 'height': 125, 'thickness': 12, 'hole_dia': 18, 
                 'holes': [(40,25), (100,25), (185,25), (245,25), (40,100), (100,100), (185,100), (245,100)]},
    'H250用B3': {'width': 285, 'height': 50, 'thickness': 9, 'hole_dia': 18, 
                 'holes': [(40,25), (100,25), (185,25), (245,25)]},
    
    # H300用
    'H300用A5': {'width': 285, 'height': 150, 'thickness': 9, 'hole_dia': 22, 
                 'holes': [(40,30), (100,30), (185,30), (245,30), (40,120), (100,120), (185,120), (245,120)]},
    'H300用A6': {'width': 405, 'height': 150, 'thickness': 9, 'hole_dia': 22, 
                 'holes': [(40,30), (100,30), (160,30), (245,30), (305,30), (365,30), 
                          (40,120), (100,120), (160,120), (245,120), (305,120), (365,120)]},
    'H300用A7': {'width': 405, 'height': 150, 'thickness': 12, 'hole_dia': 22, 
                 'holes': [(40,30), (100,30), (160,30), (245,30), (305,30), (365,30), 
                          (40,120), (100,120), (160,120), (245,120), (305,120), (365,120)]},
    'H300用B5': {'width': 285, 'height': 60, 'thickness': 9, 'hole_dia': 22, 
                 'holes': [(40,30), (100,30), (185,30), (245,30)]},
    'H300用B6': {'width': 405, 'height': 60, 'thickness': 9, 'hole_dia': 22, 
                 'holes': [(40,30), (100,30), (160,30), (245,30), (305,30), (365,30)]},
    
    # H350用
    'H350用A8': {'width': 285, 'height': 175, 'thickness': 9, 'hole_dia': 22, 
                 'holes': [(40,35), (100,35), (185,35), (245,35), (40,140), (100,140), (185,140), (245,140)]},
    'H350用A9': {'width': 405, 'height': 175, 'thickness': 9, 'hole_dia': 22, 
                 'holes': [(40,35), (100,35), (160,35), (245,35), (305,35), (365,35), 
                          (40,140), (100,140), (160,140), (245,140), (305,140), (365,140)]},
    'H350用A10': {'width': 405, 'height': 175, 'thickness': 12, 'hole_dia': 22, 
                  'holes': [(40,35), (100,35), (160,35), (245,35), (305,35), (365,35), 
                           (40,140), (100,140), (160,140), (245,140), (305,140), (365,140)]},
    'H350用B8': {'width': 285, 'height': 70, 'thickness': 9, 'hole_dia': 22, 
                 'holes': [(40,35), (100,35), (185,35), (245,35)]},
    'H350用B9': {'width': 405, 'height': 70, 'thickness': 9, 'hole_dia': 22, 
                 'holes': [(40,35), (100,35), (160,35), (245,35), (305,35), (365,35)]},
    
    # H400用
    'H400用A11': {'width': 405, 'height': 200, 'thickness': 9, 'hole_dia': 22, 
                  'holes': [(40,40), (100,40), (160,40), (245,40), (305,40), (365,40), 
                           (40,160), (100,160), (160,160), (245,160), (305,160), (365,160)]},
    'H400用A12': {'width': 405, 'height': 200, 'thickness': 12, 'hole_dia': 22, 
                  'holes': [(40,40), (100,40), (160,40), (245,40), (305,40), (365,40), 
                           (40,160), (100,160), (160,160), (245,160), (305,160), (365,160)]},
    'H400用B11': {'width': 405, 'height': 75, 'thickness': 9, 'hole_dia': 22, 
                  'holes': [(40,37), (100,37), (160,37), (245,37), (305,37), (365,37)]},
    'H400用B12': {'width': 405, 'height': 75, 'thickness': 12, 'hole_dia': 22, 
                  'holes': [(40,37), (100,37), (160,37), (245,37), (305,37), (365,37)]},
    
    # H400・500用
    'H400・500用A13': {'width': 525, 'height': 200, 'thickness': 12, 'hole_dia': 22, 
                      'holes': [(40,40), (100,40), (160,40), (220,40), (305,40), (365,40), (425,40), (485,40), 
                               (40,160), (100,160), (160,160), (220,160), (305,160), (365,160), (425,160), (485,160)]},
    'H400・500用A14': {'width': 525, 'height': 200, 'thickness': 16, 'hole_dia': 22, 
                      'holes': [(40,40), (100,40), (160,40), (220,40), (305,40), (365,40), (425,40), (485,40), 
                               (40,160), (100,160), (160,160), (220,160), (305,160), (365,160), (425,160), (485,160)]},
    'H400・500用B13': {'width': 525, 'height': 80, 'thickness': 12, 'hole_dia': 22, 
                      'holes': [(40,40), (100,40), (160,40), (220,40), (305,40), (365,40), (425,40), (485,40)]},
    'H400・500用B14': {'width': 525, 'height': 80, 'thickness': 16, 'hole_dia': 22, 
                      'holes': [(40,40), (100,40), (160,40), (220,40), (305,40), (365,40), (425,40), (485,40)]},
    
    # H鋼ウェブ部用
    'H200用W1': {'width': 165, 'height': 140, 'thickness': 6, 'hole_dia': 18, 
                 'holes': [(40,40), (85,40), (125,40), (40,100), (85,100), (125,100)]},
    'H250用W2': {'width': 165, 'height': 200, 'thickness': 6, 'hole_dia': 18, 
                 'holes': [(40,40), (85,40), (125,40), (40,100), (85,100), (125,100), (40,160), (85,160), (125,160)]},
    'H300用W3': {'width': 165, 'height': 200, 'thickness': 6, 'hole_dia': 22, 
                 'holes': [(40,40), (85,40), (125,40), (40,100), (85,100), (125,100), (40,160), (85,160), (125,160)]},
    'H300用W4': {'width': 165, 'height': 220, 'thickness': 6, 'hole_dia': 22, 
                 'holes': [(40,40), (85,40), (125,40), (40,100), (85,100), (125,100), (40,160), (85,160), (125,160), (40,220), (85,220), (125,220)]},
    'H350用W5': {'width': 165, 'height': 260, 'thickness': 6, 'hole_dia': 22, 
                 'holes': [(40,40), (85,40), (125,40), (40,100), (85,100), (125,100), (40,160), (85,160), (125,160), (40,220), (85,220), (125,220)]},
    'H350用W6': {'width': 165, 'height': 260, 'thickness': 9, 'hole_dia': 22, 
                 'holes': [(40,40), (85,40), (125,40), (40,100), (85,100), (125,100), (40,160), (85,160), (125,160), (40,220), (85,220), (125,220)]},
    'H400用W7': {'width': 165, 'height': 290, 'thickness': 9, 'hole_dia': 22, 
                 'holes': [(40,40), (85,40), (125,40), (40,100), (85,100), (125,100), (40,160), (85,160), (125,160), (40,220), (85,220), (125,220), (40,250), (85,250), (125,250)]},
    'H450用W8': {'width': 165, 'height': 320, 'thickness': 9, 'hole_dia': 22, 
                 'holes': [(40,40), (85,40), (125,40), (40,100), (85,100), (125,100), (40,160), (85,160), (125,160), (40,220), (85,220), (125,220), (40,280), (85,280), (125,280)]},
    'H500用W9': {'width': 165, 'height': 360, 'thickness': 9, 'hole_dia': 22, 
                 'holes': [(40,40), (85,40), (125,40), (40,100), (85,100), (125,100), (40,160), (85,160), (125,160), (40,220), (85,220), (125,220), (40,280), (85,280), (125,280), (40,320), (85,320), (125,320)]},
    'H600用W10': {'width': 165, 'height': 440, 'thickness': 9, 'hole_dia': 22, 
                  'holes': [(40,40), (85,40), (125,40), (40,100), (85,100), (125,100), (40,160), (85,160), (125,160), (40,220), (85,220), (125,220), (40,280), (85,280), (125,280), (40,340), (85,340), (125,340), (40,400), (85,400), (125,400)]},
}

def start():
    cmd_def = ui.commandDefinitions.itemById(CMD_ID)
    if not cmd_def:
        cmd_def = ui.commandDefinitions.addButtonDefinition(CMD_ID, CMD_NAME, CMD_Description, '')
        futil.add_handler(cmd_def.commandCreated, command_created)

    workspace = ui.workspaces.itemById(WORKSPACE_ID)
    if not workspace:
        futil.log(f'Workspace not found: {WORKSPACE_ID}')
        return

    # 複数のパネル候補に追加して見える場所を増やす
    panel_ids = [PANEL_ID, 'SolidScriptsAddinsPanel', 'SolidCreatePanel']
    added = False
    for pid in panel_ids:
        panel = workspace.toolbarPanels.itemById(pid)
        if not panel:
            futil.log(f'Panel not found: {pid}')
            continue

        # 既存コントロールが残っている場合は削除
        existing_control = panel.controls.itemById(CMD_ID)
        if existing_control:
            existing_control.deleteMe()

        try:
            # 可能なら既存の配置IDで追加、無ければ末尾追加
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
        command_control = panel.controls.itemById(CMD_ID)
        if command_control:
            command_control.deleteMe()

    command_definition = ui.commandDefinitions.itemById(CMD_ID)
    if command_definition:
        command_definition.deleteMe()

def refresh_model_list(model_input: adsk.core.DropDownCommandInput):
    model_input.listItems.clear()
    global SPLICE_PLATE_MODELS
    SPLICE_PLATE_MODELS = load_splice_models()
    if SPLICE_PLATE_MODELS:
        for name in SPLICE_PLATE_MODELS.keys():
            model_input.listItems.add(name, False)
        model_input.listItems.item(0).isSelected = True
        model_input.isEnabled = True
    else:
        model_input.listItems.add('モデルが登録されていません', True)
        model_input.isEnabled = False

def set_visibility(inputs: adsk.core.CommandInputs, mode: str):
    register_inputs = ['register_name', 'register_desc', 'register_path', 'browse_file']
    place_inputs = ['model', 'target_sel']
    standard_inputs = ['plate_type', 'thickness', 'hole_diameter', 'plate_preview', 'target_sel']
    for i in register_inputs:
        inp = inputs.itemById(i)
        if inp:
            inp.isVisible = (mode == 'ファイルから登録')
    for i in place_inputs:
        inp = inputs.itemById(i)
        if inp:
            inp.isVisible = (mode == '登録済みモデル配置')
    for i in standard_inputs:
        inp = inputs.itemById(i)
        if inp:
            inp.isVisible = (mode == '標準プレート作成')

def command_created(args: adsk.core.CommandCreatedEventArgs):
    futil.log(f'{CMD_NAME} コマンドが作成されました')
    
    inputs = args.command.commandInputs

    mode_input = inputs.addDropDownCommandInput('mode', 'モード', adsk.core.DropDownStyles.TextListDropDownStyle)
    mode_input.listItems.add('標準プレート作成', True)
    mode_input.listItems.add('登録済みモデル配置', False)
    mode_input.listItems.add('ファイルから登録', False)

    inputs.addStringValueInput('register_name', '登録名', '')
    inputs.addStringValueInput('register_desc', '説明', '')
    inputs.addStringValueInput('register_path', 'ファイルパス', '')
    inputs.addBoolValueInput('browse_file', 'ファイルを選択...', False, '', False)

    plate_type_input = inputs.addDropDownCommandInput('plate_type', 'プレートタイプ', 
                                                      adsk.core.DropDownStyles.TextListDropDownStyle)
    for plate_type in SPLICE_PLATE_TYPES.keys():
        plate_type_input.listItems.add(plate_type, False)
    plate_type_input.listItems.item(0).isSelected = True

    default_plate = list(SPLICE_PLATE_TYPES.values())[0]

    inputs.addValueInput('thickness', '板厚', 'mm', 
                         adsk.core.ValueInput.createByReal(default_plate['thickness'] / 10.0))
    inputs.addValueInput('hole_diameter', 'ボルト穴径', 'mm',
                         adsk.core.ValueInput.createByReal(default_plate['hole_dia'] / 10.0))

    model_input = inputs.addDropDownCommandInput('model', 'スプライスプレートモデル', adsk.core.DropDownStyles.TextListDropDownStyle)
    refresh_model_list(model_input)

    target_sel = inputs.addSelectionInput('target_sel', '配置先', '面/点/エッジを選択')
    target_sel.addSelectionFilter('PlanarFaces')
    target_sel.addSelectionFilter('Vertices')
    target_sel.addSelectionFilter('Edges')
    target_sel.setSelectionLimits(0, 1)

    preview_path = _build_preview_png(default_plate)
    preview_input = inputs.addImageCommandInput('plate_preview', 'プレビュー', preview_path.replace('\\','/'))
    preview_input.isFullWidth = True

    set_visibility(inputs, '標準プレート作成')

    futil.add_handler(args.command.execute, command_execute, local_handlers=local_handlers)
    futil.add_handler(args.command.inputChanged, command_input_changed, local_handlers=local_handlers)
    futil.add_handler(args.command.destroy, command_destroy, local_handlers=local_handlers)

def command_execute(args: adsk.core.CommandEventArgs):
    inputs = args.command.commandInputs
    mode = inputs.itemById('mode').selectedItem.name

    if mode == 'ファイルから登録':
        reg_name_input = inputs.itemById('register_name')
        reg_name = reg_name_input.value.strip()
        reg_desc = inputs.itemById('register_desc').value.strip()
        reg_path = inputs.itemById('register_path').value.strip()
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
    elif mode == '登録済みモデル配置':
        model_name = inputs.itemById('model').selectedItem.name
        target_sel = inputs.itemById('target_sel')
        placement_point = adsk.core.Point3D.create(0, 0, 0)
        if target_sel and target_sel.selectionCount > 0:
            try:
                placement_point = target_sel.selection(0).point
            except Exception:
                placement_point = adsk.core.Point3D.create(0, 0, 0)
        place_splice_model(model_name, placement_point)
    else:
        plate_type = inputs.itemById('plate_type').selectedItem.name
        thickness = inputs.itemById('thickness').value
        hole_diameter = inputs.itemById('hole_diameter').value
        target_sel = inputs.itemById('target_sel')
        placement_point = adsk.core.Point3D.create(0, 0, 0)
        if target_sel and target_sel.selectionCount > 0:
            try:
                placement_point = target_sel.selection(0).point
            except Exception:
                placement_point = adsk.core.Point3D.create(0, 0, 0)

        create_splice_plate(plate_type, thickness, hole_diameter, placement_point)

def command_input_changed(args: adsk.core.InputChangedEventArgs):
    changed_input = args.input
    inputs = args.inputs
    if changed_input.id == 'mode':
        set_visibility(inputs, changed_input.selectedItem.name)
    if changed_input.id == 'browse_file' and changed_input.value:
        path = _open_file_dialog()
        if path:
            inputs.itemById('register_path').value = path
            name_input = inputs.itemById('register_name')
            if name_input and not name_input.value.strip():
                name_input.value = Path(path).stem
        changed_input.value = False
    if changed_input.id == 'plate_type':
        plate_type = changed_input.selectedItem.name
        plate_data = SPLICE_PLATE_TYPES.get(plate_type)
        if plate_data:
            thickness_input = inputs.itemById('thickness')
            thickness_input.value = plate_data['thickness'] / 10.0
            hole_diameter_input = inputs.itemById('hole_diameter')
            hole_diameter_input.value = plate_data['hole_dia'] / 10.0
            _update_preview(inputs, plate_data)

def command_destroy(args: adsk.core.CommandEventArgs):
    global local_handlers
    local_handlers = []

def register_model_to_json(model_name: str, model_path: str, description: str = ''):
    try:
        base_dir = Path(__file__).parent
        cfg = base_dir / 'splice_models.json'
        models_dir = base_dir / 'models'
        models_dir.mkdir(exist_ok=True)

        src_path = Path(model_path)
        if not src_path.exists():
            ui.messageBox(f'ソースファイルが見つかりません:\n{model_path}')
            return

        local_file_name = src_path.name
        local_file_path = models_dir / local_file_name

        shutil.copy2(str(src_path), str(local_file_path))
        futil.log(f'モデルファイルをコピー: {src_path} -> {local_file_path}')

        relative_path = str(local_file_path.relative_to(base_dir)).replace('\\', '/')

        models = {}
        if cfg.exists():
            with open(cfg, 'r', encoding='utf-8') as f:
                models = json.load(f)

        models[model_name] = {'path': relative_path, 'description': description or 'ユーザー登録モデル'}

        with open(cfg, 'w', encoding='utf-8') as f:
            json.dump(models, f, ensure_ascii=False, indent=2)

        global SPLICE_PLATE_MODELS
        SPLICE_PLATE_MODELS = models
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

def place_splice_model(model_name: str, placement_point: adsk.core.Point3D):
    try:
        design = adsk.fusion.Design.cast(app.activeProduct)
        if not design:
            ui.messageBox('アクティブなデザインがありません')
            return
        model_info = SPLICE_PLATE_MODELS.get(model_name)
        if not model_info:
            ui.messageBox(f'モデル {model_name} が見つかりません')
            return
        model_path = model_info.get('path')
        if not model_path:
            ui.messageBox(f'モデル {model_name} のパスが設定されていません')
            return

        model_path_obj = Path(model_path)
        if not model_path_obj.is_absolute():
            base_dir = Path(__file__).parent
            model_path_obj = base_dir / model_path_obj

        if not model_path_obj.exists():
            ui.messageBox(f'モデルファイルが見つかりません:\n{model_path_obj}')
            return

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
            ui.messageBox(f'スプライスプレート"{model_name}"を配置しました')
        except Exception as e1:
            ui.messageBox(f'モデルの配置に失敗しました:\n{e1}')
            futil.log(f'モデル配置エラー: {e1}')
    except Exception as e:
        ui.messageBox(f'エラーが発生しました: {e}')
        futil.log(f'エラー: {e}')

def create_splice_plate(plate_type: str, thickness: float, hole_diameter: float, placement_point: adsk.core.Point3D):
    """スプライスプレートを作成"""
    try:
        design = adsk.fusion.Design.cast(app.activeProduct)
        root_comp = design.rootComponent
        
        base_pt = placement_point or adsk.core.Point3D.create(0, 0, 0)
        matrix = adsk.core.Matrix3D.create()
        matrix.translation = adsk.core.Vector3D.create(base_pt.x, base_pt.y, base_pt.z)

        occurrence = root_comp.occurrences.addNewComponent(matrix)
        component = occurrence.component
        clean_plate = plate_type.replace('用', ' ').replace('_', ' ')
        comp_name = f'SPL {clean_plate}'
        component.name = comp_name
        
        plate_data = SPLICE_PLATE_TYPES.get(plate_type)
        if not plate_data:
            ui.messageBox(f'プレートタイプ {plate_type} が見つかりません')
            return
        
        # スケッチを作成
        sketches = component.sketches
        xy_plane = component.xYConstructionPlane
        sketch = sketches.add(xy_plane)
        
        # 矩形を描画 (寸法をmmからcmに変換)
        width = plate_data['width'] / 10.0
        height = plate_data['height'] / 10.0
        
        lines = sketch.sketchCurves.sketchLines
        rect = lines.addTwoPointRectangle(
            adsk.core.Point3D.create(0, 0, 0),
            adsk.core.Point3D.create(width, height, 0)
        )
        
        # ボルト穴を追加
        circles = sketch.sketchCurves.sketchCircles
        for hole_pos in plate_data['holes']:
            x = hole_pos[0] / 10.0
            y = hole_pos[1] / 10.0
            center = adsk.core.Point3D.create(x, y, 0)
            circles.addByCenterRadius(center, hole_diameter / 2.0)
        
        # プロファイルを取得して押し出し（最大面積＝外形）
        max_area = 0
        profile = None
        for prof in sketch.profiles:
            area = prof.areaProperties().area
            if area > max_area:
                max_area = area
                profile = prof

        if profile is not None:
            extrudes = component.features.extrudeFeatures
            extrude_input = extrudes.createInput(profile, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
            distance = adsk.core.ValueInput.createByReal(thickness)
            extrude_input.setDistanceExtent(False, distance)
            extrude = extrudes.add(extrude_input)
        
        ui.messageBox(f'{plate_type} を作成しました')
        
    except Exception as e:
        ui.messageBox(f'エラーが発生しました: {str(e)}')
        futil.log(f'エラー: {str(e)}')


def _build_preview_png(plate_data: dict) -> str:
    """選択中プレートの簡易プレビューPNGを生成し、パスを返す"""
    width = float(plate_data['width'])
    height = float(plate_data['height'])
    thickness = float(plate_data['thickness'])
    holes = plate_data['holes']

    W, H = 320, 240
    margin = 20

    # 背景
    bg = (245, 248, 252)
    plate_fill = (233, 244, 251)
    plate_stroke = (31, 105, 150)
    hole_stroke = (31, 105, 150)
    dim_color = (80, 80, 80)

    buf = bytearray([bg[0], bg[1], bg[2]] * W * H)

    def set_px(x, y, color):
        if 0 <= x < W and 0 <= y < H:
            i = (y * W + x) * 3
            buf[i:i+3] = bytes(color)

    def draw_line(x1, y1, x2, y2, color):
        steps = max(abs(x2 - x1), abs(y2 - y1)) + 1
        for t in range(steps):
            x = int(x1 + (x2 - x1) * t / steps)
            y = int(y1 + (y2 - y1) * t / steps)
            set_px(x, y, color)

    def draw_text(x, y, text, color):
        # 簡易テキスト描画（5x7 ピクセルフォント風）
        font = {
            '0': [[1,1,1],[1,0,1],[1,0,1],[1,0,1],[1,1,1]],
            '1': [[0,1,0],[1,1,0],[0,1,0],[0,1,0],[1,1,1]],
            '2': [[1,1,1],[0,0,1],[1,1,1],[1,0,0],[1,1,1]],
            '3': [[1,1,1],[0,0,1],[1,1,1],[0,0,1],[1,1,1]],
            '4': [[1,0,1],[1,0,1],[1,1,1],[0,0,1],[0,0,1]],
            '5': [[1,1,1],[1,0,0],[1,1,1],[0,0,1],[1,1,1]],
            '6': [[1,1,1],[1,0,0],[1,1,1],[1,0,1],[1,1,1]],
            '7': [[1,1,1],[0,0,1],[0,0,1],[0,0,1],[0,0,1]],
            '8': [[1,1,1],[1,0,1],[1,1,1],[1,0,1],[1,1,1]],
            '9': [[1,1,1],[1,0,1],[1,1,1],[0,0,1],[1,1,1]],
            'm': [[0,0,0],[1,0,1],[1,1,1],[1,0,1],[1,0,1]],
            't': [[0,1,0],[1,1,1],[0,1,0],[0,1,0],[0,1,1]],
            'φ': [[0,1,0],[1,1,1],[1,1,1],[1,1,1],[0,1,0]],
        }
        cx = x
        for ch in text:
            if ch in font:
                for dy, row in enumerate(font[ch]):
                    for dx, px in enumerate(row):
                        if px:
                            set_px(cx + dx, y + dy, color)
                cx += 4
            elif ch == ' ':
                cx += 3

    # 版面スケール
    sx = (W - margin * 3) / width
    sy = (H - margin * 3) / height
    s = min(sx, sy)
    pw = int(width * s)
    ph = int(height * s)
    x0 = (W - pw) // 2
    y0 = (H - ph) // 2

    # プレート塗りつぶし
    for yy in range(y0, y0 + ph):
        for xx in range(x0, x0 + pw):
            set_px(xx, yy, plate_fill)

    # 外形ストローク
    for xx in range(x0, x0 + pw):
        set_px(xx, y0, plate_stroke)
        set_px(xx, y0 + ph - 1, plate_stroke)
    for yy in range(y0, y0 + ph):
        set_px(x0, yy, plate_stroke)
        set_px(x0 + pw - 1, yy, plate_stroke)

    # 穴の円弧（半径は見やすさ重視で4px）
    r = 4
    first_hole = None
    for hx, hy in holes:
        cx = int(x0 + hx * s)
        cy = int(y0 + ph - hy * s)  # 上下反転
        if first_hole is None:
            first_hole = (cx, cy)
        for yy in range(cy - r - 1, cy + r + 2):
            for xx in range(cx - r - 1, cx + r + 2):
                dist = math.hypot(xx - cx, yy - cy)
                if abs(dist - r) <= 0.8:
                    set_px(xx, yy, hole_stroke)
    
    # 寸法線（幅）
    y_dim = y0 - 8
    draw_line(x0, y_dim, x0 + pw, y_dim, dim_color)
    draw_line(x0, y_dim - 3, x0, y_dim + 3, dim_color)
    draw_line(x0 + pw, y_dim - 3, x0 + pw, y_dim + 3, dim_color)
    draw_text(x0 + pw // 2 - 10, y_dim - 10, f'{int(width)}', dim_color)
    
    # 寸法線（高さ）
    x_dim = x0 + pw + 8
    draw_line(x_dim, y0, x_dim, y0 + ph, dim_color)
    draw_line(x_dim - 3, y0, x_dim + 3, y0, dim_color)
    draw_line(x_dim - 3, y0 + ph, x_dim + 3, y0 + ph, dim_color)
    draw_text(x_dim + 5, y0 + ph // 2 - 3, f'{int(height)}', dim_color)
    
    # 板厚表示
    draw_text(x0 + 2, y0 + ph + 5, f't{int(thickness)}', dim_color)
    
    # 穴径表示（最初の穴の近く）
    if first_hole:
        hole_dia = plate_data.get('hole_dia', 18)
        draw_text(first_hole[0] + 8, first_hole[1] - 3, f'φ{int(hole_dia)}', dim_color)

    # PNG書き出し
    import struct, zlib

    def chunk(tag, data):
        return (struct.pack('>I', len(data)) + tag + data +
                struct.pack('>I', zlib.crc32(tag + data) & 0xFFFFFFFF))

    raw = bytearray()
    for y in range(H):
        raw.append(0)
        row = buf[y*W*3:(y+1)*W*3]
        raw.extend(row)

    ihdr = struct.pack('>IIBBBBB', W, H, 8, 2, 0, 0, 0)
    comp = zlib.compress(bytes(raw))
    png = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', ihdr) + chunk(b'IDAT', comp) + chunk(b'IEND', b'')

    out_path = Path(__file__).parent / 'resources' / 'preview.png'
    with open(out_path, 'wb') as f:
        f.write(png)
    return str(out_path)


def _update_preview(inputs: adsk.core.CommandInputs, plate_data: dict) -> None:
    """プレビュー画像を再生成してImageCommandInputに反映"""
    preview_input = inputs.itemById('plate_preview')
    if not preview_input:
        return

    try:
        preview_path = _build_preview_png(plate_data)
    except Exception as exc:  # 生成失敗時は既存画像を使う
        futil.log(f'プレビュー生成に失敗: {exc}', force_console=True)
        preview_path = str(Path(__file__).parent / 'resources' / 'preview.png')

    preview_input.imageFile = preview_path.replace('\\','/')
