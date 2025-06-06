import os
import platform
import subprocess
import pyperclip

from termax.prompt import Memory
from termax.agent import OpenAIModel, OllamaModel, GeminiModel, ClaudeModel, QianFanModel, MistralModel, QianWenModel
from termax.utils import Config, qa_general, qa_platform
from termax.utils.const import *


# 构建 Termax 的配置文件。
# 如果 general=True，则只配置通用参数，否则配置平台相关参数。
def build_config(general: bool = False):
    """
    build_config：为 Termax 构建配置文件。
    参数:
        general: 是否仅构建通用配置（布尔值）。
    返回值:
    """
    configuration = Config()
    if general:  # 配置通用参数
        general_config = qa_general()
        if general_config:
            configuration.write_general(general_config)
    else:  # 配置平台相关参数
        platform_config = qa_platform()
        if platform_config:
            configuration.write_platform(platform_config, platform=platform_config['platform'])


# 根据配置文件加载并返回对应的大模型实例和平台名。
def load_model():
    """
    load_model：根据配置文件加载并返回对应的大模型实例和平台名。
    """
    configuration = Config()
    config_dict = configuration.read()
    plat = config_dict['general']['platform']

    if plat == CONFIG_SEC_OPENAI:
        model = OpenAIModel(
            api_key=config_dict['openai'][CONFIG_SEC_API_KEY], version=config_dict['openai']['model'],
            temperature=float(config_dict['openai']['temperature']), base_url=config_dict['openai']['base_url']
        )
    elif plat == CONFIG_SEC_OLLAMA:
        model = OllamaModel(
            host_url=config_dict['ollama']['host_url'], version=config_dict['ollama']['model'],
        )
    elif plat == CONFIG_SEC_GEMINI:
        model = GeminiModel(
            api_key=config_dict['gemini'][CONFIG_SEC_API_KEY], version=config_dict['gemini']['model'],
            generation_config={
                'stop_sequences': config_dict['gemini']['stop_sequences']
                if config_dict['gemini']['stop_sequences'] != 'None' else None,
                'temperature': config_dict['gemini']['temperature'],
                'top_p': config_dict['gemini']['top_p'],
                'top_k': config_dict['gemini']['top_k'],
                'candidate_count': config_dict['gemini']['candidate_count'],
                'max_output_tokens': config_dict['gemini']['max_tokens']
            }
        )
    elif plat == CONFIG_SEC_CLAUDE:
        model = ClaudeModel(
            api_key=config_dict['claude'][CONFIG_SEC_API_KEY], version=config_dict['claude']['model'],
            generation_config={
                'stop_sequences': config_dict['claude']['stop_sequences']
                if config_dict['claude']['stop_sequences'] != 'None' else None,
                'temperature': config_dict['claude']['temperature'],
                'top_p': config_dict['claude']['top_p'],
                'top_k': config_dict['claude']['top_k'],
                'max_tokens': config_dict['claude']['max_tokens']
            }
        )
    elif plat == CONFIG_SEC_QIANFAN:
        model = QianFanModel(
            api_key=config_dict['qianfan'][CONFIG_SEC_API_KEY], secret_key=config_dict['qianfan']['secret_key'],
            version=config_dict['qianfan']['model'],
            generation_config={
                'temperature': config_dict['qianfan']['temperature'],
                'top_p': config_dict['qianfan']['top_p'],
                'max_output_tokens': config_dict['qianfan']['max_tokens']
            }
        )
    elif plat == CONFIG_SEC_MISTRAL:
        model = MistralModel(
            api_key=config_dict['mistral'][CONFIG_SEC_API_KEY], version=config_dict['mistral']['model'],
            generation_config={
                'temperature': config_dict['mistral']['temperature'],
                'top_p': config_dict['mistral']['top_p'],
                'max_tokens': config_dict['mistral']['max_tokens']
            }
        )
    elif plat == CONFIG_SEC_QIANWEN:
        model = QianWenModel(
            api_key=config_dict['qianwen'][CONFIG_SEC_API_KEY], version=config_dict['qianwen']['model'],
            generation_config={
                'temperature': config_dict['qianwen']['temperature'],
                'top_p': config_dict['qianwen']['top_p'],
                'top_k': config_dict['qianwen']['top_k'],
                'stop': config_dict['qianwen']['stop_sequences']
                if config_dict['qianwen']['stop_sequences'] != 'None' else None,
                'max_tokens': config_dict['qianwen']['max_tokens']
            }
        )
    else:
        raise ValueError(f"Platform {plat} not supported.")

    return model, plat


# 执行命令行命令，返回是否执行成功（True/False）。
def execute_command(command: str) -> bool:
    """
    执行命令并返回是否成功。

    参数:
        command: 要执行的命令。

    返回值:
        如果命令执行成功返回 True，否则返回 False。
    """
    try:
        if platform.system() == "Windows":
            is_powershell = len(os.getenv("PSModulePath", "").split(os.pathsep)) >= 3
            if is_powershell:
                # Powershell 执行
                completed = subprocess.run(['powershell.exe', '-Command', command], check=True)
            else:
                # CMD 执行
                completed = subprocess.run(['cmd.exe', '/c', command], check=True)
        else:
            # 类 Unix shell 执行
            shell = os.environ.get("SHELL", "/bin/sh")
            completed = subprocess.run([shell, '-c', command], check=True)

        return completed.returncode == 0
    except subprocess.CalledProcessError:
        # 命令执行失败
        return False


# 保存用户命令及其对应的用户输入到内存数据库（向量数据库），并根据配置自动淘汰超出最大存储数的历史记录。
def save_command(command: str, text: str, config_dict: dict, memory: Memory):
    """
    save_command：将命令保存到数据库中。
    参数:
        command: 要执行的命令。
        text: 用户输入的提示。
        config_dict: 配置字典。
        memory: 内存中的向量数据库。
    """
    # add the query to the memory, eviction with the default max size of 2000.
    if config_dict.get(CONFIG_SEC_GENERAL).get('storage_size') is None:
        storage_size = 2000
    else:
        storage_size = int(config_dict[CONFIG_SEC_GENERAL]['storage_size'])

    if memory.count() > storage_size:
        memory.delete()

    if command != '':
        memory.add_query(queries=[{"query": text, "response": command}])


# 根据过滤条件筛选命令历史，并格式化输出，最多返回 max_count 条。
def filter_and_format_history(command_history, filter_condition, max_count):
    """根据条件和最大数量过滤并格式化命令历史。"""
    filtered_history = [f"Command: {entry['command']}\nExecution Date: {entry['time']}\n" for entry in
                        command_history if filter_condition(entry)][:max_count]

    return "Command History: \n" + "\n".join(filtered_history)


# 将命令复制到剪贴板，成功返回 True，失败返回 False。
def copy_command(command: str):
    """
    copy_command：将命令复制到剪贴板。
    参数:
        command: 要复制的命令。
    """
    try:
        pyperclip.copy(command)
        return True
    except pyperclip.PyperclipException:
        return False
