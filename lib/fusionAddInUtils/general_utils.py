#  Copyright 2022 by Autodesk, Inc.
#  Permission to use, copy, modify, and distribute this software in object code form
#  for any purpose and without fee is hereby granted, provided that the above copyright
#  notice appears in all copies and that both that copyright notice and the limited
#  warranty and restricted rights notice below appear in all supporting documentation.
#
#  AUTODESK PROVIDES THIS PROGRAM "AS IS" AND WITH ALL FAULTS. AUTODESK SPECIFICALLY
#  DISCLAIMS ANY IMPLIED WARRANTY OF MERCHANTABILITY OR FITNESS FOR A PARTICULAR USE.
#  AUTODESK, INC. DOES NOT WARRANT THAT THE OPERATION OF THE PROGRAM WILL BE
#  UNINTERRUPTED OR ERROR FREE.

import os
import traceback
import adsk.core

app = adsk.core.Application.get()
ui = app.userInterface

# Attempt to read DEBUG flag from parent config.
try:
    from ... import config
    DEBUG = config.DEBUG
except:
    DEBUG = False


def log(message: str, level: adsk.core.LogLevels = adsk.core.LogLevels.InfoLogLevel, force_console: bool = False):
    """Utility function to easily handle logging in your app.

    Arguments:
    message -- The message to log.
    level -- The logging severity level.
    force_console -- Forces the message to be written to the Text Command window. 
    """    
    # Always print to console, only seen through IDE.
    print(message)  

    # Log all errors to Fusion log file.
    if level == adsk.core.LogLevels.ErrorLogLevel:
        log_type = adsk.core.LogTypes.FileLogType
        app.log(message, level, log_type)

    # If config.DEBUG is True write all log messages to the console.
    if DEBUG or force_console:
        log_type = adsk.core.LogTypes.ConsoleLogType
        app.log(message, level, log_type)


def handle_error(name: str, show_message_box: bool = False):
    """Utility function to simplify error handling.

    Arguments:
    name -- A name used to label the error.
    show_message_box -- Indicates if the error should be shown in the message box.
                        If False, it will only be shown in the Text Command window
                        and logged to the log file.                        
    """    

    log('===== Error =====', adsk.core.LogLevels.ErrorLogLevel)
    log(f'{name}\n{traceback.format_exc()}', adsk.core.LogLevels.ErrorLogLevel)

    # If desired you could show an error as a message box.
    if show_message_box:
        ui.messageBox(f'{name}\n{traceback.format_exc()}')


def set_command_resource_folder(cmd_def, module_file: str):
    """Try to set the `resourceFolder` attribute on a command definition.

    Some Fusion versions expose `resourceFolder` and some do not. This helper
    attempts to set it to the `resources` directory next to the provided
    module file. Failures are logged but not raised.
    """
    try:
        if not cmd_def:
            return
        base = os.path.dirname(os.path.abspath(module_file))
        res_dir = os.path.join(base, 'resources')
        if not os.path.isdir(res_dir):
            return
        # Fusion API may expect forward slashes
        res_dir = res_dir.replace('\\', '/')
        try:
            setattr(cmd_def, 'resourceFolder', res_dir)
        except Exception:
            try:
                cmd_def.resourceFolder = res_dir
            except Exception as e:
                log(f'set_command_resource_folder: failed to set resourceFolder: {e}', force_console=True)
    except Exception as e:
        log(f'set_command_resource_folder: unexpected error: {e}', force_console=True)


def get_target_component(design):
    """アクティブなコンポーネント内にモデルを挿入するためのターゲットコンポーネントを取得します。
    
    Fusion 360でコンポーネント編集モード中（ダブルクリックでコンポーネント内に入った状態）のターゲットコンポーネントを返します。
    コンポーネント編集モードでない場合はrootComponentを返します。
    
    Arguments:
    design -- 対象のDesignオブジェクト
    
    Returns:
    ターゲットコンポーネント
    """
    try:
        if not design:
            return None
        
        import adsk.fusion
        import adsk.core
        
        # 方法1: activeComponentを確認
        if hasattr(design, 'activeComponent'):
            active_comp = design.activeComponent
            if active_comp:
                log(f'get_target_component: activeComponent={active_comp.name}', force_console=True)
                return active_comp
        
        # 方法2: rootComponentを返す
        if hasattr(design, 'rootComponent'):
            root = design.rootComponent
            log(f'get_target_component: rootComponentを使用', force_console=True)
            return root
            
    except Exception as e:
        log(f'get_target_component エラー: {e}', force_console=True)
    
    return None


def format_component_name(name: str) -> str:
    """コンポーネント名を整形します。
    
    括弧付き数字（例：(1), (2)）を削除し、最後の文字の後に半角スペースを挿入します。
    例: 'SPL H200用A1(1)' → 'SPL H200用A1 '
    
    Arguments:
    name -- 元のコンポーネント名
    
    Returns:
    整形されたコンポーネント名
    """
    import re
    
    if not name:
        return name
    
    # 括弧付き数字（例：(1), (2)）を削除
    formatted = re.sub(r'\(\d+\)$', '', name)
    
    # 最後に半角スペースを追加
    formatted = formatted + ' '
    
    return formatted
