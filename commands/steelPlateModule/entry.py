import adsk.core
import adsk.fusion
import os
import json
import shutil
from ...lib import fusionAddInUtils as futil
from ... import config
from pathlib import Path
import math
import struct
import zlib

app = adsk.core.Application.get()
ui = app.userInterface

CMD_ID = 'ACME_SteelHelper_SteelPlateModule'
CMD_NAME = '鉄骨設計支援ツール'
CMD_Description = 'スプライスプレートとガセットプレートの統合コマンド'

IS_PROMOTED = True

WORKSPACE_ID = 'FusionSolidEnvironment'
PANEL_ID = 'SolidCreatePanel'
COMMAND_BESIDE_ID = ''

local_handlers = []

# ============================================================================
# モデル管理
# ============================================================================

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

SPLICE_PLATE_MODELS = load_splice_models()
GUSSET_PLATE_MODELS = load_gusset_models()

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
    'H400用A11': {'width': 525, 'height': 200, 'thickness': 9, 'hole_dia': 22, 
                  'holes': [(40,40), (100,40), (160,40), (220,40), (305,40), (365,40), (425,40), (485,40), 
                           (40,160), (100,160), (160,160), (220,160), (305,160), (365,160), (425,160), (485,160)]},
    'H400用A12': {'width': 525, 'height': 200, 'thickness': 12, 'hole_dia': 22, 
                  'holes': [(40,40), (100,40), (160,40), (220,40), (305,40), (365,40), (425,40), (485,40), 
                           (40,160), (100,160), (160,160), (220,160), (305,160), (365,160), (425,160), (485,160)]},
    'H400用B11': {'width': 525, 'height': 80, 'thickness': 9, 'hole_dia': 22, 
                  'holes': [(40,40), (100,40), (160,40), (220,40), (305,40), (365,40), (425,40), (485,40)]},
    'H400用B12': {'width': 525, 'height': 80, 'thickness': 12, 'hole_dia': 22, 
                  'holes': [(40,40), (100,40), (160,40), (220,40), (305,40), (365,40), (425,40), (485,40)]},
    
    # H400・500用
    'H400・500用A13': {'width': 525, 'height': 200, 'thickness': 16, 'hole_dia': 22, 
                      'holes': [(40,40), (100,40), (160,40), (220,40), (305,40), (365,40), (425,40), (485,40), 
                               (40,160), (100,160), (160,160), (220,160), (305,160), (365,160), (425,160), (485,160)]},
    'H400・500用B13': {'width': 525, 'height': 80, 'thickness': 12, 'hole_dia': 22, 
                      'holes': [(40,40), (100,40), (160,40), (220,40), (305,40), (365,40), (425,40), (485,40)]},
    'H400・500用B14': {'width': 525, 'height': 80, 'thickness': 16, 'hole_dia': 22, 
                      'holes': [(40,40), (100,40), (160,40), (220,40), (305,40), (365,40), (425,40), (485,40)]},
    
    # H鋼ウェブ部用
    'H200用W1': {'width': 165, 'height': 140, 'thickness': 6, 'hole_dia': 18, 
                 'holes': [(40,40), (125,40), (40,100), (125,100)]},
    'H250用W2': {'width': 165, 'height': 200, 'thickness': 6, 'hole_dia': 18, 
                 'holes': [(40,40), (125,40), (40,100), (125,100), (40,160), (125,160)]},
    'H300用W3': {'width': 165, 'height': 200, 'thickness': 6, 'hole_dia': 22, 
                 'holes': [(40,40), (125,40), (40,100), (125,100), (40,160), (125,160)]},
    'H300用W4': {'width': 165, 'height': 220, 'thickness': 6, 'hole_dia': 22, 
                 'holes': [(40,40), (125,40), (40,130), (125,130), (40,220), (125,220)]},
    'H350用W5': {'width': 165, 'height': 260, 'thickness': 6, 'hole_dia': 22, 
                 'holes': [(40,40), (125,40), (40,100), (125,100), (40,160), (125,160), (40,220), (125,220)]},
    'H350用W6': {'width': 165, 'height': 260, 'thickness': 9, 'hole_dia': 22, 
                 'holes': [(40,40), (125,40), (40,100), (125,100), (40,160), (125,160), (40,220), (125,220)]},
    'H400用W7': {'width': 165, 'height': 290, 'thickness': 9, 'hole_dia': 22, 
                 'holes': [(40,40), (125,40), (40,110), (125,110), (40,180), (125,180), (40,250), (125,250)]},
    'H450用W8': {'width': 165, 'height': 320, 'thickness': 9, 'hole_dia': 22, 
                 'holes': [(40,40), (125,40), (40,100), (125,100), (40,160), (125,160), (40,220), (125,220), (40,280), (125,280)]},
    'H500用W9': {'width': 165, 'height': 360, 'thickness': 9, 'hole_dia': 22, 
                 'holes': [(40,40), (125,40), (40,110), (125,110), (40,180), (125,180), (40,250), (125,250), (40,320), (125,320)]},
    'H600用W10': {'width': 165, 'height': 440, 'thickness': 9, 'hole_dia': 22, 
                  'holes': [(40,40), (125,40), (40,100), (125,100), (40,160), (125,160), (40,220), (125,220), (40,280), (125,280), (40,340), (125,340), (40,400), (125,400)]},
}

# ============================================================================
# コマンド開始/停止
# ============================================================================

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

        existing_control = panel.controls.itemById(CMD_ID)
        if existing_control:
            existing_control.deleteMe()

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
        command_control = panel.controls.itemById(CMD_ID)
        if command_control:
            command_control.deleteMe()

    command_definition = ui.commandDefinitions.itemById(CMD_ID)
    if command_definition:
        command_definition.deleteMe()

# ============================================================================
# UIダイアログ関連
# ============================================================================

def command_created(args: adsk.core.CommandCreatedEventArgs):
    futil.log(f'{CMD_NAME} コマンドが作成されました')
    
    inputs = args.command.commandInputs

    # タブ: スプライス / ガセット / カスタム
    tab_splice = inputs.addTabCommandInput('tab_splice', 'スプライスプレート')
    tab_gusset = inputs.addTabCommandInput('tab_gusset', 'ガセットプレート')
    tab_custom = inputs.addTabCommandInput('tab_custom', 'カスタムプレート')

    # --- スプライスタブ ---
    splice_inputs = tab_splice.children

    splice_plate_type_input = splice_inputs.addDropDownCommandInput('splice_plate_type', 'プレートタイプ', 
                                                                     adsk.core.DropDownStyles.TextListDropDownStyle)
    for plate_type in SPLICE_PLATE_TYPES.keys():
        splice_plate_type_input.listItems.add(plate_type, False)
    splice_plate_type_input.listItems.item(0).isSelected = True

    default_plate = list(SPLICE_PLATE_TYPES.values())[0]

    splice_inputs.addValueInput('splice_thickness', '板厚', 'mm', 
                                adsk.core.ValueInput.createByReal(default_plate['thickness'] / 10.0))
    splice_inputs.addValueInput('splice_hole_diameter', 'ボルト穴径', 'mm',
                                adsk.core.ValueInput.createByReal(default_plate['hole_dia'] / 10.0))

    preview_path = _build_preview_png(default_plate)
    splice_inputs.addImageCommandInput('splice_plate_preview', 'プレビュー', preview_path.replace('\\','/'))

    splice_target = splice_inputs.addSelectionInput('splice_target_sel', '配置先', '面/点/エッジを選択')
    splice_target.addSelectionFilter('PlanarFaces')
    splice_target.addSelectionFilter('Vertices')
    splice_target.addSelectionFilter('Edges')
    splice_target.setSelectionLimits(0, 1)

    # --- ガセットタブ ---
    gusset_inputs = tab_gusset.children
    gusset_model_input = gusset_inputs.addDropDownCommandInput('gusset_model', 'ガセットプレートモデル', 
                                                               adsk.core.DropDownStyles.TextListDropDownStyle)
    refresh_gusset_model_list(gusset_model_input)

    gusset_target = gusset_inputs.addSelectionInput('gusset_target_sel', '配置先', '面/点/エッジを選択')
    gusset_target.addSelectionFilter('PlanarFaces')
    gusset_target.addSelectionFilter('Vertices')
    gusset_target.addSelectionFilter('Edges')
    gusset_target.setSelectionLimits(0, 1)

    # --- カスタムタブ（ファイル登録） ---
    custom_inputs = tab_custom.children
    custom_inputs.addStringValueInput('custom_register_name', '登録名', '')
    custom_inputs.addStringValueInput('custom_register_desc', '説明', '')
    custom_inputs.addStringValueInput('custom_register_path', 'ファイルパス', '')
    custom_inputs.addBoolValueInput('custom_browse_file', 'ファイルを選択...', False, '', False)

    set_splice_visibility(inputs, '標準作成')
    futil.add_handler(args.command.inputChanged, command_input_changed, local_handlers=local_handlers)
    futil.add_handler(args.command.destroy, command_destroy, local_handlers=local_handlers)

def set_splice_visibility(inputs: adsk.core.CommandInputs, splice_mode: str):
    """スプライスタブ内のモードに応じて表示を切替"""
    splice_standard = ['splice_plate_type', 'splice_thickness', 'splice_hole_diameter', 'splice_plate_preview']
    splice_register = ['splice_model']
    for i in splice_standard:
        inp = inputs.itemById(i)
        if inp:
            inp.isVisible = (splice_mode == '標準作成')
    for i in splice_register:
        inp = inputs.itemById(i)
        if inp:
            inp.isVisible = (splice_mode == '登録モデル配置')

def command_execute(args: adsk.core.CommandEventArgs):
    inputs = args.command.commandInputs

    try:
        tab_splice = inputs.itemById('tab_splice')
        tab_gusset = inputs.itemById('tab_gusset')
        tab_custom = inputs.itemById('tab_custom')

        if tab_splice and tab_splice.isActive:
            plate_type = inputs.itemById('splice_plate_type').selectedItem.name
            thickness = inputs.itemById('splice_thickness').value
            hole_diameter = inputs.itemById('splice_hole_diameter').value
            target_sel = inputs.itemById('splice_target_sel')
            placement_point = adsk.core.Point3D.create(0, 0, 0)
            if target_sel and target_sel.selectionCount > 0:
                try:
                    placement_point = target_sel.selection(0).point
                except Exception:
                    placement_point = adsk.core.Point3D.create(0, 0, 0)
            create_splice_plate(plate_type, thickness, hole_diameter, placement_point)

        elif tab_gusset and tab_gusset.isActive:
            model_name = inputs.itemById('gusset_model').selectedItem.name
            target_sel = inputs.itemById('gusset_target_sel')
            placement_point = adsk.core.Point3D.create(0, 0, 0)
            if target_sel and target_sel.selectionCount > 0:
                try:
                    placement_point = target_sel.selection(0).point
                except Exception:
                    placement_point = adsk.core.Point3D.create(0, 0, 0)
            place_gusset_model(model_name, placement_point)

        elif tab_custom and tab_custom.isActive:
            reg_name_input = inputs.itemById('custom_register_name')
            reg_name = reg_name_input.value.strip()
            reg_desc = inputs.itemById('custom_register_desc').value.strip()
            reg_path = inputs.itemById('custom_register_path').value.strip()

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
                inputs.itemById('custom_register_path').value = reg_path

            if not Path(reg_path).exists():
                ui.messageBox(f'指定のファイルが見つかりません:\n{reg_path}')
                return

            register_gusset_model_to_json(reg_name, reg_path, reg_desc or 'ユーザー登録モデル')
            ui.messageBox(f'モデル"{reg_name}"を登録しました')
            refresh_gusset_model_list(inputs.itemById('gusset_model'))

    except Exception as e:
        ui.messageBox(f'エラーが発生しました: {str(e)}')
        futil.log(f'実行エラー: {str(e)}')

def command_input_changed(args: adsk.core.InputChangedEventArgs):
    changed_input = args.input
    inputs = args.inputs
    
    if changed_input.id == 'splice_plate_type':
        plate_type = changed_input.selectedItem.name
        plate_data = SPLICE_PLATE_TYPES.get(plate_type)
        if plate_data:
            thickness_input = inputs.itemById('splice_thickness')
            thickness_input.value = plate_data['thickness'] / 10.0
            hole_diameter_input = inputs.itemById('splice_hole_diameter')
            hole_diameter_input.value = plate_data['hole_dia'] / 10.0
            _update_preview(inputs, plate_data)
    
    if changed_input.id == 'custom_browse_file' and changed_input.value:
        path = _open_file_dialog()
        if path:
            inputs.itemById('custom_register_path').value = path
            name_input = inputs.itemById('custom_register_name')
            if name_input and not name_input.value.strip():
                name_input.value = Path(path).stem
        changed_input.value = False

def command_destroy(args: adsk.core.CommandEventArgs):
    global local_handlers
    local_handlers = []

# ============================================================================
# モデル管理関数
# ============================================================================

def refresh_splice_model_list(model_input: adsk.core.DropDownCommandInput):
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

def refresh_gusset_model_list(model_input: adsk.core.DropDownCommandInput):
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

def register_gusset_model_to_json(model_name: str, model_path: str, description: str = ''):
    try:
        base_dir = Path(__file__).parent
        cfg = base_dir / 'gusset_models.json'
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

        global GUSSET_PLATE_MODELS
        GUSSET_PLATE_MODELS = models
        futil.log(f'ガセットプレートモデル登録完了: {model_name}')
    except Exception as e:
        ui.messageBox(f'モデル登録に失敗しました: {e}')
        futil.log(f'登録エラー: {e}')

# ============================================================================
# ファイルダイアログ
# ============================================================================

def _open_file_dialog() -> str:
    try:
        dlg = ui.createFileDialog()
        dlg.isMultiSelectEnabled = False
        dlg.title = 'モデルファイルを選択 (f3d/step/iges)'
        dlg.filter = 'Fusion 360 Archive (*.f3d);;STEP Files (*.step; *.stp);;IGES Files (*.iges; *.igs);;All Files (*.*)'
        dlg.filterIndex = 0
        res = dlg.showOpen()
        if res == adsk.core.DialogResults.DialogOK:
            return dlg.filename
    except Exception as e:
        futil.log(f'ファイルダイアログエラー: {e}')
    return ''

# ============================================================================
# プレート作成関数
# ============================================================================

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
        
        # 矩形を描画
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
        
        # プロファイルを取得して押し出し
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

def place_splice_model(model_name: str, placement_point: adsk.core.Point3D):
    """登録されたスプライスプレートモデルを配置"""
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

        _place_model_impl(design, model_name, model_path_obj, placement_point)
        ui.messageBox(f'スプライスプレート"{model_name}"を配置しました')
        
    except Exception as e:
        ui.messageBox(f'エラーが発生しました: {e}')
        futil.log(f'エラー: {e}')

def place_gusset_model(model_name: str, placement_point: adsk.core.Point3D):
    """登録されたガセットプレートモデルを配置"""
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
        
        model_path_obj = Path(model_path)
        if not model_path_obj.is_absolute():
            base_dir = Path(__file__).parent
            model_path_obj = base_dir / model_path_obj
        
        if not model_path_obj.exists():
            ui.messageBox(f'モデルファイルが見つかりません:\n{model_path_obj}')
            return

        _place_model_impl(design, model_name, model_path_obj, placement_point)
        ui.messageBox(f'ガセットプレート"{model_name}"を配置しました')
        
    except Exception as e:
        ui.messageBox(f'エラーが発生しました: {e}')
        futil.log(f'エラー: {e}')

def _place_model_impl(design: adsk.fusion.Design, model_name: str, model_path_obj: Path, placement_point: adsk.core.Point3D):
    """モデル配置の実装"""
    base_pt = placement_point or adsk.core.Point3D.create(0, 0, 0)
    matrix = adsk.core.Matrix3D.create()
    matrix.translation = adsk.core.Vector3D.create(base_pt.x, base_pt.y, base_pt.z)

    occs = design.rootComponent.occurrences
    before_count = occs.count
    
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

# ============================================================================
# プレビュー関連
# ============================================================================

def _build_preview_png(plate_data: dict) -> str:
    """選択中プレートの簡易プレビューPNGを生成し、パスを返す"""
    width = float(plate_data['width'])
    height = float(plate_data['height'])
    thickness = float(plate_data['thickness'])
    holes = plate_data['holes']

    W, H = 320, 240
    margin = 20

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

    sx = (W - margin * 3) / width
    sy = (H - margin * 3) / height
    s = min(sx, sy)
    pw = int(width * s)
    ph = int(height * s)
    x0 = (W - pw) // 2
    y0 = (H - ph) // 2

    for yy in range(y0, y0 + ph):
        for xx in range(x0, x0 + pw):
            set_px(xx, yy, plate_fill)

    for xx in range(x0, x0 + pw):
        set_px(xx, y0, plate_stroke)
        set_px(xx, y0 + ph - 1, plate_stroke)
    for yy in range(y0, y0 + ph):
        set_px(x0, yy, plate_stroke)
        set_px(x0 + pw - 1, yy, plate_stroke)

    r = 4
    first_hole = None
    for hx, hy in holes:
        cx = int(x0 + hx * s)
        cy = int(y0 + ph - hy * s)
        if first_hole is None:
            first_hole = (cx, cy)
        for yy in range(cy - r - 1, cy + r + 2):
            for xx in range(cx - r - 1, cx + r + 2):
                dist = math.hypot(xx - cx, yy - cy)
                if abs(dist - r) <= 0.8:
                    set_px(xx, yy, hole_stroke)
    
    y_dim = y0 - 8
    draw_line(x0, y_dim, x0 + pw, y_dim, dim_color)
    draw_line(x0, y_dim - 3, x0, y_dim + 3, dim_color)
    draw_line(x0 + pw, y_dim - 3, x0 + pw, y_dim + 3, dim_color)
    draw_text(x0 + pw // 2 - 10, y_dim - 10, f'{int(width)}', dim_color)
    
    x_dim = x0 + pw + 8
    draw_line(x_dim, y0, x_dim, y0 + ph, dim_color)
    draw_line(x_dim - 3, y0, x_dim + 3, y0, dim_color)
    draw_line(x_dim - 3, y0 + ph, x_dim + 3, y0 + ph, dim_color)
    draw_text(x_dim + 5, y0 + ph // 2 - 3, f'{int(height)}', dim_color)
    
    draw_text(x0 + 2, y0 + ph + 5, f't{int(thickness)}', dim_color)
    
    if first_hole:
        hole_dia = plate_data.get('hole_dia', 18)
        draw_text(first_hole[0] + 8, first_hole[1] - 3, f'φ{int(hole_dia)}', dim_color)

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
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, 'wb') as f:
        f.write(png)
    return str(out_path)


def _update_preview(inputs: adsk.core.CommandInputs, plate_data: dict) -> None:
    """プレビュー画像を再生成してImageCommandInputに反映"""
    preview_input = inputs.itemById('splice_plate_preview')
    if not preview_input:
        return

    try:
        preview_path = _build_preview_png(plate_data)
    except Exception as exc:
        futil.log(f'プレビュー生成に失敗: {exc}', force_console=True)
        preview_path = str(Path(__file__).parent / 'resources' / 'preview.png')

    preview_input.imageFile = preview_path.replace('\\','/')
