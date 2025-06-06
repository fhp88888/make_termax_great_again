import re
from urllib.parse import urlparse


# 从 markdown 文本中提取所有代码块，并用分隔符拼接
def extract_code_from_markdown(markdown_text, separator="\n\n"):
    """
    从 markdown 文本中提取代码块。
    :param markdown_text:  markdown 文本内容。
    :param separator: 用于拼接代码块的分隔符。
    :return: 代码块组成的字符串。
    """
    code_block_regex = re.compile(r"```(?:[a-zA-Z0-9]+)?\n(.*?)```", re.DOTALL)
    code_blocks = code_block_regex.findall(markdown_text)

    return separator.join(code_blocks)


# 从输出文本中提取 shell 命令，支持多种格式
def extract_shell_commands(output):
    commands_start = "Commands: "
    commands_index = output.find(commands_start)

    command_start = "Command: "
    command_index = output.find(command_start)

    if command_index >= 0:
        commands = output[command_index + len(command_start):].strip()
    elif commands_index >= 0:
        commands = output[commands_index + len(commands_start):].strip()
    else:
        commands = extract_code_from_markdown(output)

    return commands


# 处理 macOS 脚本字符串，去除 osascript -e 和多余引号，并包裹为单引号
def process_mac_script(text):
    """
    处理脚本字符串，移除 "osascript -e" 和多余的引号，并确保最终用一对单引号包裹。

    参数:
    - text (str): 可能包含 "osascript -e" 和多重引号的输入文本。

    返回:
    - str: 处理后用单引号包裹的文本。
    """
    processed_text = re.sub(r'^\s*osascript -e\s*', '', text)
    if (processed_text.startswith('"') and processed_text.endswith('"')) or (processed_text.startswith("'") and processed_text.endswith("'")):
        processed_text = remove_quotes(processed_text)
    return f"'{processed_text}'"


# 处理 PowerShell 脚本字符串，去除多余引号并包裹为双引号
def process_powershell_script(text):
    """
    处理 PowerShell 脚本字符串，移除多余引号，并确保最终用一对双引号包裹。

    参数:
    - text (str): 可能包含多重引号的输入文本。

    返回:
    - str: 处理后用双引号包裹的文本。
    """
    processed_text = re.sub(r'^\s*powershell -Command\s*', '', text)
    if (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'")):
        processed_text = remove_quotes(text)
    else:
        processed_text = text
    return f'"{processed_text}"'


# 移除字符串首尾的单引号和双引号
def remove_quotes(input_string):
    """
    移除输入字符串首尾的所有单引号和双引号。

    参数:
    - input_string (str): 需要移除首尾引号的字符串。

    返回:
    - str: 移除首尾引号后的字符串。
    """
    # 使用正则表达式移除字符串首尾的引号
    # 此模式用于匹配字符串开头（^["']+）和结尾（["']+$）的引号并将其移除
    modified_string = re.sub(r'^["\']+|["\']+$', '', input_string)
    return modified_string


# 判断字符串是否为合法 URL
def is_url(string):
    """
    检查字符串是否为合法的 URL。

    参数:
    - string (str): 需要检查的字符串。

    返回:
    - bool: 如果字符串是合法 URL 返回 True，否则返回 False。
    """
    try:
        result = urlparse(string)
        # 检查解析是否成功且 scheme 和 netloc 是否存在
        return all([result.scheme, result.netloc])
    except ValueError:
        return False
