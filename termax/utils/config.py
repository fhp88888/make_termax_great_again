import os
import configparser
from pathlib import Path

from termax.utils.const import *

CONFIG_HOME = os.path.join(str(Path.home()), ".termax")
CONFIG_PATH = os.path.join(CONFIG_HOME, "config")


class Config:
    """
    Config：Termax 的整体系统配置类。
    """

    def __init__(self):
        self.home = CONFIG_HOME
        Path(self.home).mkdir(parents=True, exist_ok=True)

        self.config_path = CONFIG_PATH
        self.config = configparser.ConfigParser()
        self.config.read(self.config_path)
        self.snowflake_auth = None
        self.docker_auth = None

    def read(self):
        """
        read：读取配置文件。

        返回值：配置字典。
        """
        self.reload_config(CONFIG_PATH)
        config_dict = {}

        for section in self.config.sections():
            options_dict = {option: self.config.get(section, option) for option in self.config.options(section)}
            config_dict[section] = options_dict

        return config_dict

    def reload_config(self, config_path):
        """
        reload_config：默认会加载 ~/.termax/config，如需自定义配置文件路径需调用此方法。

        参数:
            config_path: 新配置文件的路径。
        """
        self.config.read(config_path)

    def load_openai_config(self):
        """
        load_openai_config：按需加载 OpenAI 配置。
        """
        if self.config.has_section(CONFIG_SEC_OPENAI):
            return self.config[CONFIG_SEC_OPENAI]
        else:
            raise ValueError("there is no '[openai]' section found in the configuration file.")

    def write_general(self, config_dict: dict):
        """
        write_general：写入通用配置。

        参数:
            config_dict: 配置字典。

        """
        if not self.config.has_section(CONFIG_SEC_GENERAL):
            self.config.add_section(CONFIG_SEC_GENERAL)

        self.config[CONFIG_SEC_GENERAL] = config_dict

        # 保存新配置并重新加载。
        with open(self.config_path, 'w') as configfile:
            self.config.write(configfile)
            self.reload_config(self.config_path)

    def write_platform(
            self,
            config_dict: dict,
            platform: str = CONFIG_SEC_OPENAI
    ):
        """
        write_platform：生成并写入平台相关配置。

        参数:
            config_dict: 配置字典。
            platform: 要配置的平台。

        """
        del config_dict['platform']
        # 创建用于连接 OpenAI 的配置。
        if not self.config.has_section(platform):
            self.config.add_section(platform)

        self.config[platform] = config_dict

        # 保存新配置并重新加载。
        with open(self.config_path, 'w') as configfile:
            self.config.write(configfile)
            self.reload_config(self.config_path)
