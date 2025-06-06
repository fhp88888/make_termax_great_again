from .openai import MacFunction, ShellFunction, WinFunction

import sys


def get_all_function_schemas():
    """
    获取所有函数 schema。
    返回值：函数 schema 列表。
    """
    if sys.platform.startswith('linux') or sys.platform == 'darwin':
        return [MacFunction.openai_schema, ShellFunction.openai_schema]
    return [WinFunction.openai_schema, ShellFunction.openai_schema]


def get_all_functions():
    """
    获取所有函数。
    返回值：函数列表。
    """
    if sys.platform.startswith('linux') or sys.platform == 'darwin':
        return [MacFunction, ShellFunction]  # TODO: load all modules dynamically
    return [WinFunction, ShellFunction]
