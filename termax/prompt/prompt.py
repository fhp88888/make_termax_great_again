from .memory import Memory
from termax.utils.metadata import *
from termax.utils import CONFIG_SEC_OPENAI

import textwrap
from datetime import datetime


class Prompt:
    # 初始化 Prompt 类，加载系统和路径元数据，并设置 memory 实例
    def __init__(self, memory):
        """
        Prompt for Termax: the prompt for the LLMs.
        Args:
            memory: the memory instance.
        """
        # TODO：让系统相关元数据的同步只在初始化时发生
        self.system_metadata = get_system_metadata()
        self.path_metadata = get_path_metadata()
        # self.command_history = get_command_history()

        # 共享同一个 memory 实例。
        if memory is None:
            self.memory = Memory()
        else:
            self.memory = memory

    # 生成命令建议提示词，根据环境和历史信息生成 LLM 输入
    def gen_suggestions(self, primary: str, model: str = CONFIG_SEC_OPENAI):
        """
        [Prompt] Generate the suggestions based on the environment and the history.
        Args:
            primary: the primary data source, could be git or docker.
            model: the model to use, default is OpenAI.
        """
        if primary == 'git':
            primary_data = "\n".join(
                f"{index + 1}. {key}: {value}" for index, (key, value) in enumerate(get_git_metadata().items()))
        elif primary == 'docker':
            primary_data = "\n".join(
                f"{index + 1}. {key}: {value}" for index, (key, value) in enumerate(get_docker_metadata().items()))
        else:
            primary_data = 'No primary data source available'

        files = get_file_metadata()
        if model == CONFIG_SEC_OPENAI:
            return textwrap.dedent(
                f"""\
                You are an shell expert, you need to assist user to infer the next command based on
                 user's given intent description.
                
                [INFORMATION] The user's current system information:
                
                1. OS: {self.system_metadata['platform']}
                2. OS Version: {self.system_metadata['platform_version']}
                3. Architecture: {self.system_metadata['architecture']}
                
                [INFORMATION] The user's current PATH information:

                1. User: {self.path_metadata['user']}
                2. Current PATH: {self.path_metadata['current_directory']}
                3. Files under the current directory: {files['files']}
                4. Directories under the current directory: {files['directory']}
                5. Invisible files under the current directory: {files['invisible_files']}
                6. Invisible directories under the current directory: {files['invisible_directory']}
                
                [INFORMATION] The current time: {datetime.now().isoformat()}

                [INFORMATION] The primary command information:
                {primary_data}
                
                Here are some rules you need to follow:
                1. Please provide only shell commands as the format below for os without any description.
                2. Ensure the output is a valid shell command.
                
                The output shell commands is (please replace the `{{commands}}` with the actual commands):

                Commands: ${{commands}}
                """
            )
        else:
            # TODO：添加更多模型专用的 prompt
            return textwrap.dedent(
                f"""\
                You are an shell expert, you need to assist user to infer the next command based on
                 user's given intent description.
                
                [INFORMATION] The user's current system information:
                
                1. OS: {self.system_metadata['platform']}
                2. OS Version: {self.system_metadata['platform_version']}
                3. Architecture: {self.system_metadata['architecture']}
                
                [INFORMATION] The user's current PATH information:

                1. User: {self.path_metadata['user']}
                2. Current PATH: {self.path_metadata['current_directory']}
                3. Files under the current directory: {files['files']}
                4. Directories under the current directory: {files['directory']}
                5. Invisible files under the current directory: {files['invisible_files']}
                6. Invisible directories under the current directory: {files['invisible_directory']}
                
                [INFORMATION] The current time: {datetime.now().isoformat()}

                [INFORMATION] The primary command information:
                {primary_data}
                
                Here are some rules you need to follow:
                1. Please provide only shell commands as the format below for os without any description.
                2. Ensure the output is a valid shell command.
                
                The output shell commands is (please replace the `{{commands}}` with the actual commands):

                Commands: ${{commands}}
                """
            )

    # 生成命令解释提示词，用于让 LLM 解释 shell 命令
    def explain_commands(self, model: str = CONFIG_SEC_OPENAI):
        """
        [Prompt] Explain the shell commands.
        Args:
            model: the model to use, default is OpenAI.
        """
        if model == CONFIG_SEC_OPENAI:
            return f"Help me describe this command:"
        else:
            # TODO：添加更多模型专用的 prompt
            return f"Help me describe this command:"

    # 生成命令转换提示词，将自然语言转为 shell 命令，并结合历史相似样例
    def gen_commands(self, text: str, model: str = CONFIG_SEC_OPENAI):
        """
        [Prompt] Convert the natural language text to the commands.
        Args:
            text: the natural language text.
            model: the model to use, default is OpenAI.
        """
        # 查询历史数据库以获取相似样例
        samples = self.memory.query([text])
        metadatas = samples['metadatas'][0]
        documents = samples['documents'][0]
        distances = samples['distances'][0]

        # 构造一个包含样例的人类可读字符串
        sample_string = ""
        for i in range(len(documents)):
            sample_string += f"""
            User Input: {documents[i]}
            Generated Commands: {metadatas[i]['response']}
            Distance Score: {distances[i]}
            Date: {metadatas[i]['created_at']}\n
            """

        # 刷新元数据
        files = get_file_metadata()
        if model == CONFIG_SEC_OPENAI:
            return textwrap.dedent(
                f"""\
                You are an shell expert, you can convert natural language text from user to shell commands.
                
                1. Please provide only shell commands for os without any description.
                2. Ensure the output is a valid shell command.
                3. If multiple steps required try to combine them together.
                
                Here are some rules you need to follow:

                1. The commands should be able to run on the current system according to the system information.
                2. The files in the commands should be available in the path, according to the path information.
                3. The CLI application should be installed in the system (check the path information).

                Here are some information you may need to know:
                
                [INFORMATION] The user's current system information:
                1. OS: {self.system_metadata['platform']}
                2. OS Version: {self.system_metadata['platform_version']}
                3. Architecture: {self.system_metadata['architecture']}
                
                [INFORMATION] The user's current PATH information:
                1. User: {self.path_metadata['user']}
                2. Current PATH: {self.path_metadata['current_directory']}
                3. Files under the current directory: {files['files']}
                4. Directories under the current directory: {files['directory']}
                5. Invisible files under the current directory: {files['invisible_files']}
                6. Invisible directories under the current directory: {files['invisible_directory']}
    
                Here are some similar commands generated before:
                {sample_string}

                The output shell commands is (please replace the `{{commands}}` with the actual commands):

                Commands: ${{commands}}
                """
            )
        else:
            # TODO：添加更多模型专用的 prompt
            return textwrap.dedent(
                f"""\
                You are an shell expert, you can convert natural language text from user to shell commands.
                
                1. Please provide only shell commands for os without any extra description.
                2. Ensure the output is a valid shell command.
                3. If multiple steps required try to combine them together.
                
                Here are some rules you need to follow:

                1. The commands should be able to run on the current system according to the system information.
                2. The files in the commands should be available in the path, according to the path information.
                3. The CLI application should be installed in the system (check the path information).

                Here are some information you may need to know:
                
                [INFORMATION] The user's current system information:
                1. OS: {self.system_metadata['platform']}
                2. OS Version: {self.system_metadata['platform_version']}
                3. Architecture: {self.system_metadata['architecture']}
                
                [INFORMATION] The user's current PATH information:
                1. User: {self.path_metadata['user']}
                2. Current PATH: {self.path_metadata['current_directory']}
                3. Files under the current directory: {files['files']}
                4. Directories under the current directory: {files['directory']}
                5. Invisible files under the current directory: {files['invisible_files']}
                6. Invisible directories under the current directory: {files['invisible_directory']}
                
                Here are some similar commands generated before:
                {sample_string}
                
                The output shell commands is (please replace the `{{commands}}` with the actual commands):

                Commands: ${{commands}}
                """
            )
