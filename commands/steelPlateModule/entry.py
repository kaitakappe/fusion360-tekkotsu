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
_executing = False  # 二重実行防止フラグ

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

# 形鋼カテゴリ
SECTION_STEEL_CATEGORIES = [
    'H形鋼', '溝形鋼', 'Lアングル', 'Lアングル(不等辺)',
    '角型鋼(正方形)', '角型鋼(長方形)', 'ハット形鋼',
    'リップ溝形鋼', 'リップZ形鋼', 'Cチャンネル'
]

def load_section_models():
    models = {}
    cfg = Path(__file__).parent / 'section_steel_models.json'
    if cfg.exists():
        try:
            with open(cfg, 'r', encoding='utf-8') as f:
                models = json.load(f)
        except Exception as e:
            futil.log(f'形鋼モデル設定の読み込みエラー: {e}')
    # カテゴリの初期化（欠けているカテゴリを空で用意）
    for cat in SECTION_STEEL_CATEGORIES:
        if cat not in models:
            models[cat] = {"models": {}}
    return models

SECTION_STEEL_MODELS = load_section_models()

# 配管接手カテゴリ
PIPING_FITTINGS_CATEGORIES = [
    '90°エルボ', '45°エルボ', '同径ティー', '径違いティー',
    '同心レジューサ', '偏心レジューサ', 'キャップ'
]

def load_piping_fittings_models():
    models = {}
    cfg = Path(__file__).parent / 'piping_fittings_models.json'
    if cfg.exists():
        try:
            with open(cfg, 'r', encoding='utf-8') as f:
                models = json.load(f)
        except Exception as e:
            futil.log(f'配管接手モデル設定の読み込みエラー: {e}')
    # カテゴリの初期化（欠けているカテゴリを空で用意）
    for cat in PIPING_FITTINGS_CATEGORIES:
        if cat not in models:
            models[cat] = {"models": {}}
    return models

PIPING_FITTINGS_MODELS = load_piping_fittings_models()

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
        resources_folder = str(Path(__file__).parent / 'resources')
        cmd_def = ui.commandDefinitions.addButtonDefinition(CMD_ID, CMD_NAME, CMD_Description, resources_folder)
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
    tab_section = inputs.addTabCommandInput('tab_section', '形鋼')

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

    # --- ガセットタブ（配置 / 登録 切替） ---
    gusset_inputs = tab_gusset.children
    
    # モード選択（配置 / 登録）
    gusset_mode = gusset_inputs.addDropDownCommandInput('gusset_mode', 'モード', adsk.core.DropDownStyles.TextListDropDownStyle)
    gusset_mode.listItems.add('配置', True)
    gusset_mode.listItems.add('登録', False)
    
    # 配置用グループ
    gusset_place_grp = gusset_inputs.addGroupCommandInput('gusset_place_grp', '配置')
    gusset_place_children = gusset_place_grp.children
    gusset_model_input = gusset_place_children.addDropDownCommandInput('gusset_model', 'ガセットプレートモデル', 
                                                               adsk.core.DropDownStyles.TextListDropDownStyle)
    refresh_gusset_model_list(gusset_model_input)

    gusset_target = gusset_place_children.addSelectionInput('gusset_target_sel', '配置先', '面/点/エッジを選択')
    gusset_target.addSelectionFilter('PlanarFaces')
    gusset_target.addSelectionFilter('Vertices')
    gusset_target.addSelectionFilter('Edges')
    gusset_target.setSelectionLimits(0, 1)
    
    # 登録用グループ
    gusset_reg_grp = gusset_inputs.addGroupCommandInput('gusset_reg_grp', 'ファイル登録')
    gusset_reg_children = gusset_reg_grp.children
    gusset_reg_children.addStringValueInput('gusset_register_name', '登録名', '')
    gusset_reg_children.addStringValueInput('gusset_register_desc', '説明', '')
    gusset_reg_children.addStringValueInput('gusset_register_path', 'ファイルパス', '')
    gusset_reg_children.addBoolValueInput('gusset_browse_file', 'ファイルを選択...', False, '', False)
    
    # 初期表示（デフォルトは「配置」のみ）
    gusset_place_grp.isVisible = True
    gusset_reg_grp.isVisible = False

    # --- カスタムタブ（配置 / 登録 切替） ---
    custom_inputs = tab_custom.children
    # モード選択（配置 / 登録）
    custom_mode = custom_inputs.addDropDownCommandInput('custom_mode', 'モード', adsk.core.DropDownStyles.TextListDropDownStyle)
    custom_mode.listItems.add('配置', True)
    custom_mode.listItems.add('登録', False)

    # 配置用グループ
    custom_place_grp = custom_inputs.addGroupCommandInput('custom_place_grp', '配置')
    custom_place_children = custom_place_grp.children
    custom_model_input = custom_place_children.addDropDownCommandInput('custom_model', 'モデル', adsk.core.DropDownStyles.TextListDropDownStyle)
    refresh_custom_model_list(custom_model_input)
    custom_target = custom_place_children.addSelectionInput('custom_target_sel', '配置先', '面/点/エッジを選択')
    custom_target.addSelectionFilter('PlanarFaces')
    custom_target.addSelectionFilter('Vertices')
    custom_target.addSelectionFilter('Edges')
    custom_target.setSelectionLimits(0, 1)

    # 登録用グループ
    custom_reg_grp = custom_inputs.addGroupCommandInput('custom_reg_grp', 'ファイル登録')
    custom_reg_children = custom_reg_grp.children
    custom_reg_children.addStringValueInput('custom_register_name', '登録名', '')
    custom_reg_children.addStringValueInput('custom_register_desc', '説明', '')
    custom_reg_children.addStringValueInput('custom_register_path', 'ファイルパス', '')
    custom_reg_children.addBoolValueInput('custom_browse_file', 'ファイルを選択...', False, '', False)

    # 初期表示（デフォルトは「配置」のみ）
    custom_place_grp.isVisible = True
    custom_reg_grp.isVisible = False

    # --- 形鋼タブ ---
    section_inputs = tab_section.children
    # モード選択（配置 / 登録）
    section_mode = section_inputs.addDropDownCommandInput('section_mode', 'モード', adsk.core.DropDownStyles.TextListDropDownStyle)
    section_mode.listItems.add('配置', True)
    section_mode.listItems.add('登録', False)

    # 配置用グループ
    section_place_grp = section_inputs.addGroupCommandInput('section_place_grp', '配置')
    section_place_children = section_place_grp.children
    section_cat_input = section_place_children.addDropDownCommandInput('section_category', 'カテゴリ', adsk.core.DropDownStyles.TextListDropDownStyle)
    for cat in SECTION_STEEL_CATEGORIES:
        section_cat_input.listItems.add(cat, False)
    section_cat_input.listItems.item(0).isSelected = True

    section_model_input = section_place_children.addDropDownCommandInput('section_model', 'モデル', adsk.core.DropDownStyles.TextListDropDownStyle)
    refresh_section_model_list(section_model_input, SECTION_STEEL_CATEGORIES[0])

    section_target = section_place_children.addSelectionInput('section_target_sel', '配置先', '面/点/エッジを選択')
    section_target.addSelectionFilter('PlanarFaces')
    section_target.addSelectionFilter('Vertices')
    section_target.addSelectionFilter('Edges')
    section_target.setSelectionLimits(0, 1)

    # 高さ入力（mm）
    section_place_children.addValueInput(
        'section_height', '高さ', 'mm', adsk.core.ValueInput.createByReal(100.0)
    )

    # 登録用グループ
    section_reg_grp = section_inputs.addGroupCommandInput('section_reg_grp', 'ファイル登録')
    section_reg_children = section_reg_grp.children
    section_reg_cat = section_reg_children.addDropDownCommandInput('section_reg_category', 'カテゴリ', adsk.core.DropDownStyles.TextListDropDownStyle)
    for cat in SECTION_STEEL_CATEGORIES:
        section_reg_cat.listItems.add(cat, False)
    section_reg_cat.listItems.item(0).isSelected = True
    section_reg_children.addStringValueInput('section_register_name', '登録名', '')
    section_reg_children.addStringValueInput('section_register_desc', '説明', '')
    section_reg_children.addStringValueInput('section_register_path', 'ファイルパス', '')
    section_reg_children.addBoolValueInput('section_browse_file', 'ファイルを選択...', False, '', False)

    # 初期表示（デフォルトは「配置」のみ）
    section_place_grp.isVisible = True
    section_reg_grp.isVisible = False

    # --- 配管接手タブ ---
    tab_piping = inputs.addTabCommandInput('tab_piping', '配管接手')
    piping_inputs = tab_piping.children
    # モード選択（配置 / 登録）
    piping_mode = piping_inputs.addDropDownCommandInput('piping_mode', 'モード', adsk.core.DropDownStyles.TextListDropDownStyle)
    piping_mode.listItems.add('配置', True)
    piping_mode.listItems.add('登録', False)

    # 配置用グループ
    piping_place_grp = piping_inputs.addGroupCommandInput('piping_place_grp', '配置')
    piping_place_children = piping_place_grp.children
    piping_cat_input = piping_place_children.addDropDownCommandInput('piping_category', 'カテゴリ', adsk.core.DropDownStyles.TextListDropDownStyle)
    for cat in PIPING_FITTINGS_CATEGORIES:
        piping_cat_input.listItems.add(cat, False)
    piping_cat_input.listItems.item(0).isSelected = True

    piping_model_input = piping_place_children.addDropDownCommandInput('piping_model', 'モデル', adsk.core.DropDownStyles.TextListDropDownStyle)
    refresh_piping_model_list(piping_model_input, PIPING_FITTINGS_CATEGORIES[0])

    piping_target = piping_place_children.addSelectionInput('piping_target_sel', '配置先', '面/点/エッジを選択')
    piping_target.addSelectionFilter('PlanarFaces')
    piping_target.addSelectionFilter('Vertices')
    piping_target.addSelectionFilter('Edges')
    piping_target.setSelectionLimits(0, 1)

    # 登録用グループ
    piping_reg_grp = piping_inputs.addGroupCommandInput('piping_reg_grp', 'ファイル登録')
    piping_reg_children = piping_reg_grp.children
    piping_reg_cat = piping_reg_children.addDropDownCommandInput('piping_reg_category', 'カテゴリ', adsk.core.DropDownStyles.TextListDropDownStyle)
    for cat in PIPING_FITTINGS_CATEGORIES:
        piping_reg_cat.listItems.add(cat, False)
    piping_reg_cat.listItems.item(0).isSelected = True
    piping_reg_children.addStringValueInput('piping_register_name', '登録名', '')
    piping_reg_children.addStringValueInput('piping_register_desc', '説明', '')
    piping_reg_children.addStringValueInput('piping_register_path', 'ファイルパス', '')
    piping_reg_children.addBoolValueInput('piping_browse_file', 'ファイルを選択...', False, '', False)

    # 初期表示（デフォルトは「配置」のみ）
    piping_place_grp.isVisible = True
    piping_reg_grp.isVisible = False

    set_splice_visibility(inputs, '標準作成')
    futil.add_handler(args.command.inputChanged, command_input_changed, local_handlers=local_handlers)
    # OK押下時の実行イベント（未登録だと何も起きない）
    futil.add_handler(args.command.execute, command_execute, local_handlers=local_handlers)
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
    global _executing
    if _executing:
        futil.log('command_execute: 既に実行中のため無視', force_console=True)
        return
    
    _executing = True
    try:
        inputs = args.command.commandInputs

        tab_splice = inputs.itemById('tab_splice')
        tab_gusset = inputs.itemById('tab_gusset')
        tab_custom = inputs.itemById('tab_custom')
        tab_section = inputs.itemById('tab_section')

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
            mode_input = inputs.itemById('gusset_mode')
            if mode_input and mode_input.selectedItem and mode_input.selectedItem.name == '配置':
                model_name = inputs.itemById('gusset_model').selectedItem.name
                target_sel = inputs.itemById('gusset_target_sel')
                placement_point = adsk.core.Point3D.create(0, 0, 0)
                if target_sel and target_sel.selectionCount > 0:
                    try:
                        placement_point = target_sel.selection(0).point
                    except Exception:
                        placement_point = adsk.core.Point3D.create(0, 0, 0)
                place_gusset_model(model_name, placement_point)
            else:
                # 登録処理
                reg_name_input = inputs.itemById('gusset_register_name')
                reg_name = reg_name_input.value.strip() if reg_name_input else ''
                reg_desc = inputs.itemById('gusset_register_desc').value.strip()
                reg_path = inputs.itemById('gusset_register_path').value.strip()

                if reg_path and not reg_name:
                    reg_name = Path(reg_path).stem
                    if reg_name_input:
                        reg_name_input.value = reg_name

                if not reg_name:
                    ui.messageBox('登録名を入力してください')
                    return

                if not reg_path:
                    reg_path = _open_file_dialog()
                    if not reg_path:
                        return
                    inputs.itemById('gusset_register_path').value = reg_path

                if not Path(reg_path).exists():
                    ui.messageBox(f'指定のファイルが見つかりません:\n{reg_path}')
                    return

                register_gusset_model_to_json(reg_name, reg_path, reg_desc or 'ユーザー登録モデル')
                ui.messageBox(f'モデル"{reg_name}"を登録しました')
                refresh_gusset_model_list(inputs.itemById('gusset_model'))
                # 入力欄をクリア
                inputs.itemById('gusset_register_name').value = ''
                inputs.itemById('gusset_register_path').value = ''
                inputs.itemById('gusset_register_desc').value = ''

        elif tab_custom and tab_custom.isActive:
            # カスタムタブ: モードに応じて配置または登録を実行
            mode_input = inputs.itemById('custom_mode')
            if mode_input and mode_input.selectedItem and mode_input.selectedItem.name == '配置':
                model_input = inputs.itemById('custom_model')
                model_name = model_input.selectedItem.name if model_input and model_input.selectedItem else None
                target_sel = inputs.itemById('custom_target_sel')
                placement_point = adsk.core.Point3D.create(0, 0, 0)
                if target_sel and target_sel.selectionCount > 0:
                    try:
                        placement_point = target_sel.selection(0).point
                    except Exception:
                        placement_point = adsk.core.Point3D.create(0, 0, 0)
                if not model_name:
                    ui.messageBox('配置するモデルを選択してください')
                    return
                place_gusset_model(model_name, placement_point)
            else:
                # 登録処理（既存の挙動を保持）
                reg_name_input = inputs.itemById('custom_register_name')
                reg_name = reg_name_input.value.strip() if reg_name_input else ''
                reg_desc = inputs.itemById('custom_register_desc').value.strip()
                reg_path = inputs.itemById('custom_register_path').value.strip()

                if reg_path and not reg_name:
                    reg_name = Path(reg_path).stem
                    if reg_name_input:
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

                register_custom_model_to_json(reg_name, reg_path, reg_desc or 'ユーザー登録モデル')
                ui.messageBox(f'モデル"{reg_name}"を登録しました')
                refresh_gusset_model_list(inputs.itemById('gusset_model'))
                # カスタムタブのモデルリストも更新
                try:
                    refresh_custom_model_list(inputs.itemById('custom_model'))
                except Exception:
                    pass

        elif tab_section and tab_section.isActive:
            mode_input = inputs.itemById('section_mode')
            if mode_input.selectedItem and mode_input.selectedItem.name == '配置':
                cat = inputs.itemById('section_category').selectedItem.name
                model_name = inputs.itemById('section_model').selectedItem.name
                target_sel = inputs.itemById('section_target_sel')
                placement_point = adsk.core.Point3D.create(0, 0, 0)
                selection_entity = None
                if target_sel and target_sel.selectionCount > 0:
                    try:
                        placement_point = target_sel.selection(0).point
                        selection_entity = target_sel.selection(0).entity
                    except Exception:
                        placement_point = adsk.core.Point3D.create(0, 0, 0)
                height_in_mm = None
                h_input = inputs.itemById('section_height')
                if h_input:
                    # 内部単位(cm) -> mmに換算
                    try:
                        height_in_mm = h_input.value * 10.0
                    except Exception:
                        height_in_mm = 1000.0
                place_section_model(cat, model_name, placement_point, selection_entity=selection_entity, target_height_mm=height_in_mm or 1000.0)
            else:
                reg_cat = inputs.itemById('section_reg_category').selectedItem.name
                reg_name = inputs.itemById('section_register_name').value.strip()
                reg_desc = inputs.itemById('section_register_desc').value.strip()
                reg_path = inputs.itemById('section_register_path').value.strip()

                if reg_path and not reg_name:
                    reg_name = Path(reg_path).stem
                    inputs.itemById('section_register_name').value = reg_name

                if not reg_path:
                    sel = _open_file_dialog(multi=True)
                    if not sel:
                        return

                    # 複数選択された場合はリストで返る
                    if isinstance(sel, list) and len(sel) > 1:
                        registered = []
                        for p in sel:
                            if not Path(p).exists():
                                futil.log(f'ファイルが見つかりません: {p}', force_console=True)
                                continue
                            name = Path(p).stem
                            register_section_model_to_json(reg_cat, name, p, reg_desc or '形鋼モデル')
                            registered.append(name)

                        if registered:
                            ui.messageBox(f'形鋼モデルを登録しました: {", ".join(registered)}')
                            # カテゴリが一致していればモデルリストを更新
                            current_cat = inputs.itemById('section_category').selectedItem.name
                            if current_cat == reg_cat:
                                refresh_section_model_list(inputs.itemById('section_model'), current_cat)
                        else:
                            ui.messageBox('有効なファイルが見つからず、登録は行われませんでした。')

                        # 入力欄をクリア
                        inputs.itemById('section_register_name').value = ''
                        inputs.itemById('section_register_path').value = ''
                        return
                    else:
                        # 単一選択
                        reg_path = sel[0] if isinstance(sel, list) else sel
                        if not reg_path:
                            return
                        inputs.itemById('section_register_path').value = reg_path
                        if not reg_name:
                            reg_name = Path(reg_path).stem
                            inputs.itemById('section_register_name').value = reg_name

                if not reg_name:
                    ui.messageBox('登録名を入力してください')
                    return
                if not Path(reg_path).exists():
                    ui.messageBox(f'指定のファイルが見つかりません:\n{reg_path}')
                    return

                register_section_model_to_json(reg_cat, reg_name, reg_path, reg_desc or 'ユーザー登録モデル')
                ui.messageBox(f'形鋼モデル"{reg_name}"を登録しました')
                # カテゴリが一致していればモデルリストを更新
                current_cat = inputs.itemById('section_category').selectedItem.name
                if current_cat == reg_cat:
                    refresh_section_model_list(inputs.itemById('section_model'), current_cat)

        tab_piping = inputs.itemById('tab_piping')
        if tab_piping and tab_piping.isActive:
            mode_input = inputs.itemById('piping_mode')
            if mode_input.selectedItem and mode_input.selectedItem.name == '配置':
                cat = inputs.itemById('piping_category').selectedItem.name
                model_name = inputs.itemById('piping_model').selectedItem.name
                target_sel = inputs.itemById('piping_target_sel')
                placement_point = adsk.core.Point3D.create(0, 0, 0)
                if target_sel and target_sel.selectionCount > 0:
                    try:
                        placement_point = target_sel.selection(0).point
                    except Exception:
                        placement_point = adsk.core.Point3D.create(0, 0, 0)
                if not model_name or '登録されていません' in model_name:
                    ui.messageBox('配置するモデルを選択してください')
                    return
                place_piping_model(cat, model_name, placement_point)
            else:
                reg_cat = inputs.itemById('piping_reg_category').selectedItem.name
                reg_name = inputs.itemById('piping_register_name').value.strip()
                reg_desc = inputs.itemById('piping_register_desc').value.strip()
                reg_path = inputs.itemById('piping_register_path').value.strip()

                if reg_path and not reg_name:
                    reg_name = Path(reg_path).stem
                    inputs.itemById('piping_register_name').value = reg_name

                if not reg_path:
                    sel = _open_file_dialog(multi=True)
                    if not sel:
                        return

                    # 複数選択された場合はリストで返る
                    if isinstance(sel, list) and len(sel) > 1:
                        registered = []
                        for p in sel:
                            if not Path(p).exists():
                                futil.log(f'ファイルが見つかりません: {p}', force_console=True)
                                continue
                            name = Path(p).stem
                            register_piping_model_to_json(reg_cat, name, p, reg_desc or '配管接手モデル')
                            registered.append(name)

                        if registered:
                            ui.messageBox(f'配管接手モデルを登録しました: {", ".join(registered)}')
                            # カテゴリが一致していればモデルリストを更新
                            current_cat = inputs.itemById('piping_category').selectedItem.name
                            if current_cat == reg_cat:
                                refresh_piping_model_list(inputs.itemById('piping_model'), current_cat)
                        else:
                            ui.messageBox('有効なファイルが見つかり、登録は行われませんでした。')

                        # 入力欄をクリア
                        inputs.itemById('piping_register_name').value = ''
                        inputs.itemById('piping_register_path').value = ''
                        return
                    else:
                        # 単一選択
                        reg_path = sel[0] if isinstance(sel, list) else sel
                        if not reg_path:
                            return
                        inputs.itemById('piping_register_path').value = reg_path
                        if not reg_name:
                            reg_name = Path(reg_path).stem
                            inputs.itemById('piping_register_name').value = reg_name

                if not reg_name:
                    ui.messageBox('登録名を入力してください')
                    return
                if not Path(reg_path).exists():
                    ui.messageBox(f'指定のファイルが見つかりません:\n{reg_path}')
                    return

                register_piping_model_to_json(reg_cat, reg_name, reg_path, reg_desc or 'ユーザー登録モデル')
                ui.messageBox(f'配管接手モデル"{reg_name}"を登録しました')
                # カテゴリが一致していればモデルリストを更新
                current_cat = inputs.itemById('piping_category').selectedItem.name
                if current_cat == reg_cat:
                    refresh_piping_model_list(inputs.itemById('piping_model'), current_cat)

    except Exception as e:
        ui.messageBox(f'エラーが発生しました: {str(e)}')
        futil.log(f'実行エラー: {str(e)}')
    finally:
        _executing = False

def command_input_changed(args: adsk.core.InputChangedEventArgs):
    changed_input = args.input
    inputs = args.inputs
    futil.log(f'command_input_changed: {changed_input.id}', force_console=True)
    
    if changed_input.id == 'splice_plate_type':
        plate_type = changed_input.selectedItem.name
        plate_data = SPLICE_PLATE_TYPES.get(plate_type)
        if plate_data:
            thickness_input = inputs.itemById('splice_thickness')
            thickness_input.value = plate_data['thickness'] / 10.0
            hole_diameter_input = inputs.itemById('splice_hole_diameter')
            hole_diameter_input.value = plate_data['hole_dia'] / 10.0
            _update_preview(inputs, plate_data)
    
    

    # カスタム: モード切替で表示制御
    if changed_input.id == 'custom_mode':
        selected = changed_input.selectedItem.name if changed_input.selectedItem else '配置'
        place_grp = inputs.itemById('custom_place_grp')
        reg_grp = inputs.itemById('custom_reg_grp')
        if place_grp: place_grp.isVisible = (selected == '配置')
        if reg_grp: reg_grp.isVisible = (selected == '登録')

    # ガセット: モード切替で表示制御
    if changed_input.id == 'gusset_mode':
        selected = changed_input.selectedItem.name if changed_input.selectedItem else '配置'
        place_grp = inputs.itemById('gusset_place_grp')
        reg_grp = inputs.itemById('gusset_reg_grp')
        if place_grp: place_grp.isVisible = (selected == '配置')
        if reg_grp: reg_grp.isVisible = (selected == '登録')

    # ガセット: 登録のファイル参照ボタン
    if changed_input.id == 'gusset_browse_file' and changed_input.value:
        path = _open_file_dialog()
        if path:
            inputs.itemById('gusset_register_path').value = path
            name_input = inputs.itemById('gusset_register_name')
            if name_input and not name_input.value.strip():
                name_input.value = Path(path).stem
        changed_input.value = False

    # カスタム: 登録のファイル参照ボタン
    if changed_input.id == 'custom_browse_file' and changed_input.value:
        path = _open_file_dialog()
        if path:
            inputs.itemById('custom_register_path').value = path
            name_input = inputs.itemById('custom_register_name')
            if name_input and not name_input.value.strip():
                name_input.value = Path(path).stem
        changed_input.value = False

    # 形鋼: モード切替で表示制御
    if changed_input.id == 'section_mode':
        selected = changed_input.selectedItem.name if changed_input.selectedItem else '配置'
        place_grp = inputs.itemById('section_place_grp')
        reg_grp = inputs.itemById('section_reg_grp')
        if place_grp: place_grp.isVisible = (selected == '配置')
        if reg_grp: reg_grp.isVisible = (selected == '登録')

    # 形鋼: カテゴリ変更でモデル一覧を更新
    if changed_input.id == 'section_category':
        cat = changed_input.selectedItem.name
        model_input = inputs.itemById('section_model')
        refresh_section_model_list(model_input, cat)

    # 形鋼: 登録のファイル参照ボタン
    if changed_input.id == 'section_browse_file' and changed_input.value:
        path = _open_file_dialog()
        if path:
            inputs.itemById('section_register_path').value = path
            name_input = inputs.itemById('section_register_name')
            if name_input and not name_input.value.strip():
                name_input.value = Path(path).stem
        changed_input.value = False

    # 配管接手: モード切替で表示制御
    if changed_input.id == 'piping_mode':
        selected = changed_input.selectedItem.name if changed_input.selectedItem else '配置'
        place_grp = inputs.itemById('piping_place_grp')
        reg_grp = inputs.itemById('piping_reg_grp')
        if place_grp: place_grp.isVisible = (selected == '配置')
        if reg_grp: reg_grp.isVisible = (selected == '登録')

    # 配管接手: カテゴリ変更でモデル一覧を更新
    if changed_input.id == 'piping_category':
        cat = changed_input.selectedItem.name
        model_input = inputs.itemById('piping_model')
        refresh_piping_model_list(model_input, cat)

    # 配管接手: 登録のファイル参照ボタン
    if changed_input.id == 'piping_browse_file' and changed_input.value:
        path = _open_file_dialog()
        if path:
            inputs.itemById('piping_register_path').value = path
            name_input = inputs.itemById('piping_register_name')
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
        for name in sorted(GUSSET_PLATE_MODELS.keys()):
            model_input.listItems.add(name, False)
        model_input.listItems.item(0).isSelected = True
        model_input.isEnabled = True
    else:
        model_input.listItems.add('モデルが登録されていません', True)
        model_input.isEnabled = False

def refresh_section_model_list(model_input: adsk.core.DropDownCommandInput, category: str):
    model_input.listItems.clear()
    global SECTION_STEEL_MODELS
    SECTION_STEEL_MODELS = load_section_models()
    cat_entry = SECTION_STEEL_MODELS.get(category, {"models": {}})
    models = cat_entry.get('models', {})
    if models:
        for name in sorted(models.keys()):
            model_input.listItems.add(name, False)
        model_input.listItems.item(0).isSelected = True
        model_input.isEnabled = True
    else:
        model_input.listItems.add('モデルが登録されていません', True)
        model_input.isEnabled = False

def refresh_piping_model_list(model_input: adsk.core.DropDownCommandInput, category: str):
    model_input.listItems.clear()
    global PIPING_FITTINGS_MODELS
    PIPING_FITTINGS_MODELS = load_piping_fittings_models()
    cat_entry = PIPING_FITTINGS_MODELS.get(category, {"models": {}})
    models = cat_entry.get('models', {})
    if models:
        for name in sorted(models.keys()):
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

def refresh_custom_model_list(model_input: adsk.core.DropDownCommandInput):
    model_input.listItems.clear()
    cfg = Path(__file__).parent / 'custom_models.json'
    models = {}
    if cfg.exists():
        try:
            with open(cfg, 'r', encoding='utf-8') as f:
                models = json.load(f)
        except Exception:
            models = {}

    if models:
        for name in sorted(models.keys()):
            model_input.listItems.add(name, False)
        model_input.listItems.item(0).isSelected = True
        model_input.isEnabled = True
    else:
        model_input.listItems.add('モデルが登録されていません', True)
        model_input.isEnabled = False

def register_custom_model_to_json(model_name: str, model_path: str, description: str = ''):
    try:
        base_dir = Path(__file__).parent
        cfg = base_dir / 'custom_models.json'
        models_dir = base_dir / 'models' / 'custom'
        models_dir.mkdir(parents=True, exist_ok=True)

        src_path = Path(model_path)
        if not src_path.exists():
            ui.messageBox(f'ソースファイルが見つかりません:\n{model_path}')
            return

        local_file_name = src_path.name
        local_file_path = models_dir / local_file_name

        shutil.copy2(str(src_path), str(local_file_path))
        futil.log(f'カスタムモデルをコピー: {src_path} -> {local_file_path}')

        relative_path = str(local_file_path.relative_to(base_dir)).replace('\\', '/')

        models = {}
        if cfg.exists():
            with open(cfg, 'r', encoding='utf-8') as f:
                models = json.load(f)

        models[model_name] = {'path': relative_path, 'description': description or 'ユーザー登録モデル'}

        with open(cfg, 'w', encoding='utf-8') as f:
            json.dump(models, f, ensure_ascii=False, indent=2)

        futil.log(f'カスタムモデル登録完了: {model_name}')
    except Exception as e:
        ui.messageBox(f'モデル登録に失敗しました: {e}')
        futil.log(f'登録エラー: {e}')

def register_section_model_to_json(category: str, model_name: str, model_path: str, description: str = ''):
    try:
        base_dir = Path(__file__).parent
        cfg = base_dir / 'section_steel_models.json'
        models_root = base_dir / 'models' / 'sections' / category
        models_root.mkdir(parents=True, exist_ok=True)

        src_path = Path(model_path)
        if not src_path.exists():
            ui.messageBox(f'ソースファイルが見つかりません:\n{model_path}')
            return

        local_file_name = src_path.name
        local_file_path = models_root / local_file_name
        shutil.copy2(str(src_path), str(local_file_path))
        futil.log(f'形鋼モデルをコピー: {src_path} -> {local_file_path}')

        relative_path = str(local_file_path.relative_to(base_dir)).replace('\\', '/')

        models = load_section_models()
        if category not in models:
            models[category] = {"models": {}}
        models[category].setdefault('models', {})
        models[category]['models'][model_name] = {
            'path': relative_path,
            'description': description or 'ユーザー登録モデル'
        }

        with open(cfg, 'w', encoding='utf-8') as f:
            json.dump(models, f, ensure_ascii=False, indent=2)

        global SECTION_STEEL_MODELS
        SECTION_STEEL_MODELS = models
        futil.log(f'形鋼モデル登録完了: [{category}] {model_name}')
    except Exception as e:
        ui.messageBox(f'形鋼モデル登録に失敗しました: {e}')
        futil.log(f'形鋼登録エラー: {e}')

def register_piping_model_to_json(category: str, model_name: str, model_path: str, description: str = ''):
    try:
        base_dir = Path(__file__).parent
        cfg = base_dir / 'piping_fittings_models.json'
        models_root = base_dir / 'models' / 'piping_fittings' / category
        models_root.mkdir(parents=True, exist_ok=True)

        src_path = Path(model_path)
        if not src_path.exists():
            ui.messageBox(f'ソースファイルが見つかりません:\n{model_path}')
            return

        local_file_name = src_path.name
        local_file_path = models_root / local_file_name
        shutil.copy2(str(src_path), str(local_file_path))
        futil.log(f'配管接手モデルをコピー: {src_path} -> {local_file_path}')

        relative_path = str(local_file_path.relative_to(base_dir)).replace('\\', '/')

        models = load_piping_fittings_models()
        if category not in models:
            models[category] = {"models": {}}
        models[category].setdefault('models', {})
        models[category]['models'][model_name] = {
            'path': relative_path,
            'description': description or 'ユーザー登録モデル'
        }

        with open(cfg, 'w', encoding='utf-8') as f:
            json.dump(models, f, ensure_ascii=False, indent=2)

        global PIPING_FITTINGS_MODELS
        PIPING_FITTINGS_MODELS = models
        futil.log(f'配管接手モデル登録完了: [{category}] {model_name}')
    except Exception as e:
        ui.messageBox(f'配管接手モデル登録に失敗しました: {e}')
        futil.log(f'配管接手登録エラー: {e}')

# ============================================================================
# ファイルダイアログ
# ============================================================================

def _open_file_dialog(multi: bool = False):
    """ファイルダイアログを開く。multi=True のときは複数選択を許可し、選択されたファイルのリストを返す。
    それ以外は単一ファイルパスの文字列を返す。キャンセル時は空の文字列/空リストを返す。"""
    try:
        dlg = ui.createFileDialog()
        dlg.isMultiSelectEnabled = bool(multi)
        dlg.title = 'モデルファイルを選択 (f3d/step/iges)' + (' [複数選択可]' if multi else '')
        dlg.filter = 'Fusion 360 Archive (*.f3d);;STEP Files (*.step; *.stp);;IGES Files (*.iges; *.igs);;All Files (*.*)'
        dlg.filterIndex = 0
        res = dlg.showOpen()
        if res == adsk.core.DialogResults.DialogOK:
            if multi:
                # filenames プロパティで複数ファイルを取得
                try:
                    files = []
                    for i in range(dlg.filenames.count):
                        files.append(dlg.filenames.item(i))
                    return files if files else [dlg.filename]
                except Exception as e:
                    futil.log(f'複数ファイル取得エラー: {e}', force_console=True)
                    return [dlg.filename]
            else:
                return dlg.filename
    except Exception as e:
        futil.log(f'ファイルダイアログエラー: {e}')
    return [] if multi else ''

# ============================================================================
# プレート作成関数
# ============================================================================

def create_splice_plate(plate_type: str, thickness: float, hole_diameter: float, placement_point: adsk.core.Point3D):
    """スプライスプレートを作成"""
    try:
        design = adsk.fusion.Design.cast(app.activeProduct)
        target_comp = futil.get_target_component(design)
        
        base_pt = placement_point or adsk.core.Point3D.create(0, 0, 0)
        matrix = adsk.core.Matrix3D.create()
        matrix.translation = adsk.core.Vector3D.create(base_pt.x, base_pt.y, base_pt.z)

        occurrence = target_comp.occurrences.addNewComponent(matrix)
        component = occurrence.component
        clean_plate = plate_type.replace('用', ' ').replace('_', ' ')
        comp_name = f'SPL {clean_plate}'
        # 括弧付き数字を削除し、最後の数字の前にスペースを挿入
        comp_name = futil.format_component_name(comp_name)
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

        _place_model_impl(design, model_name, model_path_obj, placement_point, modify_extrude_height=False)
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

        # ガセットプレートは既存ボディを使用するため、modify_extrude_height=False
        # 特定モデル（GPL H200 to C150x75）は後処理をスキップ（オプションB）
        do_cleanup = True
        if model_name == 'GPL H200 to C150x75':
            do_cleanup = False
        _place_model_impl(design, model_name, model_path_obj, placement_point, transform=None, modify_extrude_height=False, do_name_cleanup=do_cleanup)
        ui.messageBox(f'ガセットプレート"{model_name}"を配置しました')
        
    except Exception as e:
        ui.messageBox(f'エラーが発生しました: {e}')
        futil.log(f'エラー: {e}')

def place_section_model(category: str, model_name: str, placement_point: adsk.core.Point3D, selection_entity=None, target_height_mm: float = 1000.0):
    """登録された形鋼モデルを配置。選択面に整列し、指定高さ(mm)にスケール。"""
    try:
        design = adsk.fusion.Design.cast(app.activeProduct)
        if not design:
            ui.messageBox('アクティブなデザインがありません')
            return

        cat_entry = SECTION_STEEL_MODELS.get(category, {"models": {}})
        model_info = cat_entry.get('models', {}).get(model_name)
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

        # 面選択があれば法線方向へ整列する行列を作成
        x_axis = adsk.core.Vector3D.create(1, 0, 0)
        y_axis = adsk.core.Vector3D.create(0, 1, 0)
        z_axis = adsk.core.Vector3D.create(0, 0, 1)
        origin = placement_point or adsk.core.Point3D.create(0, 0, 0)
        matrix = adsk.core.Matrix3D.create()
        align_applied = False
        try:
            if selection_entity and hasattr(selection_entity, 'geometry'):
                geom = selection_entity.geometry
                # Planar face の場合
                if hasattr(geom, 'normal') and hasattr(geom, 'origin'):
                    n = geom.normal
                    n.normalize()
                    # 基準upを決定
                    up = adsk.core.Vector3D.create(0, 0, 1)
                    if abs(n.dotProduct(up)) > 0.95:
                        up = adsk.core.Vector3D.create(1, 0, 0)
                    x_axis = up.crossProduct(n)
                    x_axis.normalize()
                    y_axis = n.crossProduct(x_axis)
                    y_axis.normalize()
                    z_axis = n
                    origin = placement_point or geom.origin
                    matrix.setWithCoordinateSystem(origin, x_axis, y_axis, z_axis)
                    align_applied = True
        except Exception as _:
            align_applied = False

        # 目標高さを計算
        target_h_cm = max(0.01, float(target_height_mm) / 10.0)
        
        # モデルをインポート
        occ = _place_model_impl(design, model_name, model_path_obj, origin, transform=(matrix if align_applied else None))
        if not occ:
            return

        # --- コンポーネント原点を配置点の頂点座標に移動 ---
        try:
            # 現在の回転成分を保持し、平行移動を配置点に合わせた行列を作成
            cur = occ.transform
            new_m = adsk.core.Matrix3D.create()
            # コピーして回転部を保持
            for r in range(3):
                for c in range(3):
                    new_m.setCell(r, c, cur.getCell(r, c))
            # 平行移動を配置点に設定
            if placement_point:
                new_m.setCell(0, 3, placement_point.x)
                new_m.setCell(1, 3, placement_point.y)
                new_m.setCell(2, 3, placement_point.z)
            # 最終行
            new_m.setCell(3, 0, 0)
            new_m.setCell(3, 1, 0)
            new_m.setCell(3, 2, 0)
            new_m.setCell(3, 3, 1)
            occ.transform = new_m
        except Exception as e:
            futil.log(f'コンポーネント原点移動エラー: {e}')

        # 押し出しフィーチャーを編集して高さを変更（F3Dの場合）
        futil.log(f'押し出し高さ変更: target_h_cm={target_h_cm} (from target_height_mm={target_height_mm})', force_console=True)
        extrude_updated = _try_update_extrude_height(occ.component, target_h_cm)
        
        # 押し出し編集が失敗した場合はtransformスケールを使用
        if not extrude_updated:
            futil.log(f'押し出し編集失敗、スケール適用', force_console=True)
            _apply_transform_scale(occ, target_h_cm)

        ui.messageBox(f'形鋼モデル"{model_name}"を配置しました')
    except Exception as e:
        ui.messageBox(f'エラーが発生しました: {e}')
        futil.log(f'エラー: {e}')

def place_piping_model(category: str, model_name: str, placement_point: adsk.core.Point3D):
    """登録された配管接手モデルを配置"""
    try:
        design = adsk.fusion.Design.cast(app.activeProduct)
        if not design:
            ui.messageBox('アクティブなデザインがありません')
            return

        cat_entry = PIPING_FITTINGS_MODELS.get(category, {"models": {}})
        model_info = cat_entry.get('models', {}).get(model_name)
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

        # モデルを配置
        _place_model_impl(design, model_name, model_path_obj, placement_point, modify_extrude_height=False)
        ui.messageBox(f'配管接手モデル"{model_name}"を配置しました')
    except Exception as e:
        ui.messageBox(f'エラーが発生しました: {e}')
        futil.log(f'エラー: {e}')


def _try_update_extrude_height(component: adsk.fusion.Component, target_h_cm: float) -> bool:
    """コンポーネント内の最長の押し出しを探し、入力した高さに変更する。直接編集ができない場合は、スケッチから新しい押し出しを作成する。"""
    try:
        extrudes = component.features.extrudeFeatures
        futil.log(f'_try_update_extrude_height: 押し出し数={extrudes.count}, target_h_cm={target_h_cm}', force_console=True)
        
        # 既存の押し出しがある場合
        if extrudes.count > 0:
            # 最長の押し出しを探索
            max_len = -1.0
            max_extrude = None
            max_type = None
            max_profile = None
            
            for i in range(extrudes.count):
                ext = extrudes.item(i)
                futil.log(f'押し出し[{i}]: name={ext.name if hasattr(ext, "name") else "N/A"}', force_console=True)
                try:
                    extent = ext.extentOne
                    
                    # DistanceExtentDefinitionの場合
                    dist_extent = adsk.fusion.DistanceExtentDefinition.cast(extent)
                    if dist_extent and dist_extent.distance:
                        futil.log(f'  DistanceExtent: distance.value={dist_extent.distance.value}', force_console=True)
                        if dist_extent.distance.value > max_len:
                            max_len = dist_extent.distance.value
                            max_extrude = ext
                            max_type = 'distance'
                            # プロファイルを取得
                            if ext.profile:
                                max_profile = ext.profile
                            continue
                    
                    # SymmetricExtentDefinitionの場合
                    sym_extent = adsk.fusion.SymmetricExtentDefinition.cast(extent)
                    if sym_extent and sym_extent.distance:
                        total_len = sym_extent.distance.value * 2.0
                        futil.log(f'  SymmetricExtent: total_len={total_len}', force_console=True)
                        if total_len > max_len:
                            max_len = total_len
                            max_extrude = ext
                            max_type = 'symmetric'
                            if ext.profile:
                                max_profile = ext.profile
                            continue
                    
                    futil.log(f'  未対応の押し出しタイプ', force_console=True)
                except Exception as e:
                    futil.log(f'  押し出し[{i}]の処理中にエラー: {e}', force_console=True)
                    continue

            if max_extrude and max_profile:
                # 押し出し発見。直接編集は難しいため、同じプロファイルで新しい押し出しを作成
                futil.log(f'最長押し出し発見: max_type={max_type}, max_len={max_len}', force_console=True)
                try:
                    # 新しい押し出しを同じプロファイルで作成
                    extrude_input = extrudes.createInput(max_profile, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
                    extrude_input.setDistanceExtent(False, adsk.core.ValueInput.createByReal(target_h_cm))
                    new_extrude = extrudes.add(extrude_input)
                    futil.log(f'新しい押し出しを作成: {target_h_cm}cm', force_console=True)
                    
                    # 元の押し出しを削除
                    max_extrude.deleteMe()
                    futil.log(f'元の押し出しを削除', force_console=True)
                    
                    return True
                except Exception as e:
                    futil.log(f'新しい押し出し作成失敗: {e}', force_console=True)
                    return False
        
        futil.log('押し出しが見つかりませんでした', force_console=True)
        return False
    except Exception as e:
        futil.log(f'押し出し編集エラー: {e}')
        return False


def _apply_transform_scale(occ: adsk.fusion.Occurrence, target_h_cm: float) -> None:
    """押し出し編集ができない場合のフォールバック: 再インポートでスケールする。"""
    try:
        # バウンディングボックスで現在の高さを取得
        bbox = occ.boundingBox
        size_z = abs(bbox.maxPoint.z - bbox.minPoint.z)
        size_x = abs(bbox.maxPoint.x - bbox.minPoint.x)
        size_y = abs(bbox.maxPoint.y - bbox.minPoint.y)
        current_h = size_z if size_z > 1e-6 else max(size_x, size_y, size_z)
        
        if current_h <= 1e-6:
            return
        
        scale_factor = target_h_cm / current_h
        if abs(scale_factor - 1.0) <= 1e-6:
            return
        
        # 現在のtransformを取得
        current_matrix = occ.transform
        
        # スケール済みの新しいtransformを作成
        design = adsk.fusion.Design.cast(occ.component.parentDesign)
        model_name = occ.component.name
        
        # パスを取得（再インポート用）
        # ここでは再インポートを諸める代わりに、簡略化してログだけ出力
        futil.log(f'STEP/IGESモデルのためスケールはスキップします: {scale_factor}x')
        
    except Exception as e:
        futil.log(f'スケールフォールバックエラー: {e}')

def _apply_height_scale_to_occurrence(occ: adsk.fusion.Occurrence, target_h_cm: float) -> None:
    """Occurrenceのtransformにスケールを適用して高さを変更。"""
    try:
        bbox = occ.boundingBox
        size_x = abs(bbox.maxPoint.x - bbox.minPoint.x)
        size_y = abs(bbox.maxPoint.y - bbox.minPoint.y)
        size_z = abs(bbox.maxPoint.z - bbox.minPoint.z)
        # Z方向を高さとして扱う
        current_h = size_z if size_z > 1e-6 else max(size_x, size_y, size_z)
        if current_h <= 1e-6:
            return
        scale_factor = target_h_cm / current_h
        if abs(scale_factor - 1.0) <= 1e-6:
            return
        
        # 現在のtransform2を取得（こちらの方が安全に変更できる）
        current_transform = occ.transform2
        
        # データ配列として取得
        data = []
        for row in range(4):
            for col in range(4):
                val = current_transform.getCell(row, col)
                # 回転・スケール部分（0-2行×0-2列）にスケール適用
                if row < 3 and col < 3:
                    val *= scale_factor
                data.append(val)
        
        # 新しいtransformをデータから作成
        new_transform = adsk.core.Matrix3D.create()
        new_transform.setWithArray(data)
        occ.transform2 = new_transform
        
    except Exception as e:
        futil.log(f'高さスケール適用エラー: {e}')

def _place_model_impl(design: adsk.fusion.Design, model_name: str, model_path_obj: Path, placement_point: adsk.core.Point3D, transform: adsk.core.Matrix3D = None, modify_extrude_height: bool = True, do_name_cleanup: bool = True):
    """モデル配置の実装。インポートし、必要なら変換を適用し、Occurrenceを返す。
    
    Args:
        design: デザイン
        model_name: モデル名
        model_path_obj: モデルファイルパス
        placement_point: 配置点
        transform: 適用するトランスフォーム
        modify_extrude_height: 押し出しの高さを修正するか（形鋼用、ガセット/カスタムはFalse）
    """
    base_pt = placement_point or adsk.core.Point3D.create(0, 0, 0)
    default_matrix = adsk.core.Matrix3D.create()
    default_matrix.translation = adsk.core.Vector3D.create(base_pt.x, base_pt.y, base_pt.z)

    target_comp = futil.get_target_component(design)
    futil.log(f'ターゲットコンポーネント: {target_comp.name if target_comp else "None"}', force_console=True)
    futil.log(f'ルートコンポーネント: {design.rootComponent.name}', force_console=True)
    futil.log(f'アクティブコンポーネント: {design.activeComponent.name if design.activeComponent else "None"}', force_console=True)
    
    occs = target_comp.occurrences
    before_count = occs.count
    futil.log(f'インポート前: コンポーネント数={before_count}', force_console=True)
    
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

    import_manager.importToTarget(opts, target_comp)
    after_count = occs.count
    futil.log(f'インポート後: コンポーネント数={after_count}, 差分={after_count - before_count}', force_console=True)
    
    # 追加されたコンポーネントをすべてログ出力
    if after_count > before_count:
        futil.log(f'追加されたコンポーネント一覧:', force_console=True)
        for i in range(before_count, after_count):
            comp = occs.item(i)
            futil.log(f'  [{i}]: {comp.component.name if comp.component else "N/A"}', force_console=True)
    
    if after_count > before_count:
        # 複数追加された場合、最初のものを使用（他は削除）
        added_count = after_count - before_count
        if added_count > 1:
            futil.log(f'警告: {added_count}個のコンポーネントが追加されました。最初のものを使用し、他は削除します', force_console=True)
            # 後から追加された順に逆順で削除（インデックスがズレないように）
            for i in range(after_count - 1, before_count, -1):
                comp_to_delete = occs.item(i)
                if comp_to_delete != occs.item(before_count):  # 最初のものは削除しない
                    futil.log(f'削除: {comp_to_delete.component.name if comp_to_delete.component else "N/A"}', force_console=True)
                    comp_to_delete.deleteMe()
        
        occ = occs.item(before_count)  # 最初に追加されたコンポーネントを取得
        futil.log(f'使用するコンポーネント: {occ.component.name if occ.component else "N/A"}', force_console=True)
        
        # コンポーネント内の情報ログや名前クリーンアップは必要な場合のみ実施
        if occ.component and do_name_cleanup:
            body_count = occ.component.bRepBodies.count
            futil.log(f'コンポーネント内のボディ数: {body_count}', force_console=True)
            for i in range(body_count):
                body = occ.component.bRepBodies.item(i)
                futil.log(f'  ボディ[{i}]: {body.name if hasattr(body, "name") else "N/A"}', force_console=True)
            
            comp_count = occ.component.occurrences.count
            futil.log(f'コンポーネント内の子コンポーネント数: {comp_count}', force_console=True)
            if comp_count > 0 and body_count == 0:
                futil.log(f'警告: ネストされたコンポーネント構造が検出されました', force_console=True)
                for i in range(comp_count):
                    child_occ = occ.component.occurrences.item(i)
                    child_comp = child_occ.component
                    if child_comp:
                        futil.log(f'  子コンポーネント[{i}]: {child_comp.name}', force_console=True)
                        for j in range(child_comp.bRepBodies.count):
                            child_body = child_comp.bRepBodies.item(j)
                            futil.log(f'    ボディ: {child_body.name}', force_console=True)
        
        occ.transform = transform if transform else default_matrix
        try:
            if occ.component and do_name_cleanup:
                import re
                current_name = occ.component.name if hasattr(occ.component, 'name') else model_name
                base_name = current_name or model_name
                clean_name = re.sub(r'\s*\(\d+\)\s*$', '', base_name).rstrip() + ' '
                occ.component.name = clean_name
                try:
                    occ.name = clean_name
                except Exception:
                    pass
                try:
                    child_occs = occ.component.occurrences
                    for i in range(child_occs.count):
                        ch = child_occs.item(i)
                        if ch.component and hasattr(ch.component, 'name'):
                            ch_name = ch.component.name or ''
                            ch_clean = re.sub(r'\s*\(\d+\)\s*$', '', ch_name).rstrip() + ' '
                            if ch_clean != ch_name:
                                ch.component.name = ch_clean
                                futil.log(f'子コンポーネント名をクリーン: {ch_name} -> {ch_clean}', force_console=True)
                except Exception:
                    pass
                futil.log(f'コンポーネント名を設定: {clean_name}', force_console=True)
        except Exception as rename_err:
            futil.log(f'モデル名設定エラー: {rename_err}')
        return occ
    return None

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
