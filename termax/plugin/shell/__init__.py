# termax.plugin.shell 包初始化文件
# 导出各 shell（zsh、bash、fish）插件脚本内容，供插件安装/卸载模块调用

from .zsh import zsh_plugin
from .bash import bash_plugin
from .fish import fish_function, fish_plugin
