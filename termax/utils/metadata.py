import re
import os
import sys
import psutil
import socket
import shutil
import getpass
import platform
import subprocess
from datetime import datetime


def get_git_metadata():
    """
    get_git_metadata：记录当前工作区的 git 信息。
    返回值：git 元数据字典。

    """

    def run_git_command(command):
        """
        运行 git 命令并返回输出。
        参数:
            command: 要运行的 git 命令。

        返回值: git 命令的输出。

        """
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True)
        if result.returncode != 0:
            raise Exception(f"Git command failed: {result.stderr}")
        return result.stdout.strip()

    # 检查当前目录是否已初始化为 git 仓库
    if run_git_command("[ -d .git ] && echo 1 || echo 0") == "0":
        return {
            "git_sha": "",
            "git_current_branch": "",
            "git_remotes": [],
            "git_latest_commit_author": "",
            "git_latest_commit_date": "",
            "git_latest_commit_message": ""
        }

    # 获取最新提交的哈希值
    latest_commit_hash = run_git_command("git rev-parse HEAD")
    latest_commit_author = run_git_command("git log -1 --pretty=%an")
    latest_commit_message = run_git_command("git log -1 --pretty=%B")
    latest_commit_timestamp = run_git_command("git log -1 --pretty=%ct")
    latest_commit_date = datetime.utcfromtimestamp(int(latest_commit_timestamp)).strftime('%Y-%m-%d %H:%M:%S UTC')

    # 获取当前分支名称
    current_branch = run_git_command("git rev-parse --abbrev-ref HEAD")

    # 获取远程仓库信息
    remotes_raw = run_git_command("git remote -v")
    remotes = {}
    for line in remotes_raw.split('\n'):
        if line:
            name, url, typ = line.split()
            if name not in remotes:
                remotes[name] = {'fetchUrl': '', 'pushUrl': ''}
            if typ == '(fetch)':
                remotes[name]['fetchUrl'] = url
            elif typ == '(push)':
                remotes[name]['pushUrl'] = url

    remote_list = []
    for name, urls in remotes.items():
        remote_list.append(
            {
                "remote_name": name,
                "fetch_url": urls['fetchUrl'],
                "push_url": urls['pushUrl']
            }
        )

    return {
        "git_sha": latest_commit_hash,
        "git_current_branch": current_branch,
        "git_remotes": remote_list,
        "git_latest_commit_author": latest_commit_author,
        "git_latest_commit_date": latest_commit_date,
        "git_latest_commit_message": latest_commit_message
    }


def get_docker_metadata():
    """
    记录当前工作区的 Docker 容器和镜像信息。
    
    返回值:
        包含 Docker 容器和镜像元数据的字典。
    """

    def parse_docker_output(output, headers):
        """
        解析 Docker 命令输出，根据提供的表头转为字典列表。
        
        参数:
            output: Docker 命令的字符串输出。
            headers: 与 Docker 输出列对应的表头列表。
            
        返回值:
            包含 Docker 数据的字典列表。
        """
        entries = []
        for line in output.strip().split('\n')[1:]:
            parts = re.split(r'\s{2,}', line)
            entry = {header: parts[i] if i < len(parts) else "" for i, header in enumerate(headers)}
            entries.append(entry)
        return entries

    def run_command(command):
        """
        执行 shell 命令并返回输出。
        
        参数:
            command: 命令参数列表。
        
        返回值:
            (成功标志, 输出或错误信息) 的元组。
        """
        try:
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
            return result.stdout
        except subprocess.CalledProcessError as e:
            raise Exception("Docker command failed: " + e.stderr)

    containers_info = run_command(
        [
            "docker", "ps", "-a", "--format",
            "table {{.ID}}\t{{.Image}}\t{{.Command}}\t{{.CreatedAt}}\t{{.Status}}\t{{.Names}}\t{{.Ports}}"
        ]
    )
    containers_headers = ['CONTAINER ID', 'IMAGE', 'COMMAND', 'CREATED', 'STATUS', 'NAMES', 'PORTS']
    containers = parse_docker_output(containers_info, containers_headers)

    images_info = run_command(["docker", "images"])
    images_headers = ['REPOSITORY', 'TAG', 'IMAGE ID', 'CREATED', 'SIZE']
    images = parse_docker_output(images_info, images_headers)

    # docker_info = run_command(["docker", "info"])
    # docker_headers = []
    # docker = parse_docker_output(docker_info, docker_headers)

    return {
        # "docker_info": docker_info,
        "docker_containers": containers,
        "docker_images": images,
    }


def get_system_metadata():
    """
    记录系统信息。

    返回值：包含系统元数据的字典。
    """
    return {
        'platform': platform.system(),
        'platform_release': platform.release(),
        'platform_version': platform.version(),
        'architecture': platform.machine(),
        'hostname': socket.gethostname(),
        'ip_address': socket.gethostbyname(socket.gethostname()),
        'physical_cores': psutil.cpu_count(logical=False),
        'total_cores': psutil.cpu_count(logical=True),
        'ram_total': round(psutil.virtual_memory().total / (1024.0 ** 3)),
        'ram_available': round(psutil.virtual_memory().available / (1024.0 ** 3)),
        'ram_used_percent': psutil.virtual_memory().percent
    }


def get_path_metadata():
    """
    记录 PATH 路径信息。

    返回值：包含路径元数据的字典。
    """
    # 扫描 PATH 目录，列出所有可执行命令
    paths = os.environ['PATH'].split(os.pathsep)
    commands = set()
    for path in paths:
        if os.path.exists(path):
            try:
                for item in os.listdir(path):
                    item_path = os.path.join(path, item)
                    if os.path.isfile(item_path) and os.access(item_path, os.X_OK):
                        commands.add(item)
            except PermissionError:
                # 如果没有权限列出目录内容，跳过该目录
                continue

    return {
        "user": os.getlogin(),
        "current_directory": os.getcwd(),
        "home_directory": os.path.expanduser("~"),
        "executable_commands": sorted(list(commands))
    }


def get_file_metadata():
    """
    get_file_metadata：记录当前目录下的文件信息。
    """
    result = {
        "directory": [],
        "files": [],
        "invisible_files": [],
        "invisible_directory": []
    }

    # 获取当前目录
    current_directory = os.getcwd()

    # 列出当前目录下的所有文件和文件夹
    for item in os.listdir(current_directory):
        # 构建条目的完整路径
        item_path = os.path.join(current_directory, item)
        # 检查该条目是否为隐藏文件（以点开头）
        if item.startswith('.'):
            if os.path.isdir(item_path):
                result["invisible_directory"].append(item)
            else:
                result["invisible_files"].append(item)
        else:
            if os.path.isdir(item_path):
                result["directory"].append(item)
            else:
                result["files"].append(item)

    return result


def get_python_metadata():
    """
    get_python_metadata：记录 Python 相关环境信息。

    返回值：包含 Python 相关元数据的字典。
    """
    process = subprocess.run(["pip", "list"], capture_output=True, text=True)
    pip_list_lines = process.stdout.strip().split("\n")[2:]  # Skip the header lines
    pip_list = []
    for line in pip_list_lines:
        match = re.match(r"(\S+)\s+(\S+)(?:\s+(.*))?", line)
        if match:
            pip_list.append({
                "package": match.group(1),
                "version": match.group(2),
                "location": match.group(3)
            })

    return {
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "python_compiler": platform.python_compiler(),
        "python_implementation": platform.python_implementation(),
        "python_build": platform.python_build(),
        "python_pip_packages": pip_list[2:],
    }


def get_gpu_metadata():
    """
    get_gpu_metadata：记录 GPU 相关环境信息。

    返回值：包含 GPU 相关元数据的字典。
    """
    gpu_model_name = ""
    gpu_driver_version = ""
    cuda_version = ""
    if shutil.which("nvidia-smi"):
        p = subprocess.run([
            "nvidia-smi",
            "--query-gpu=gpu_name,driver_version",
            "--format=csv,noheader"
        ], capture_output=True)
        smi_string = p.stdout.decode("utf-8").strip().split("\n")
        if len(smi_string) == 1:
            gpu_model_name, gpu_driver_version = smi_string[0].split(",")
        else:
            gpu_model_name, gpu_driver_version = smi_string[0].split(",")
            for smi_entry in smi_string[1:]:
                other_model_name, other_driver_version = smi_entry.split(",")
                if other_model_name != gpu_model_name or other_driver_version != gpu_driver_version:
                    raise EnvironmentError("System is configured with different GPU models or driver versions.")

    if shutil.which("nvcc"):
        p = subprocess.run(["nvcc", "--version"], capture_output=True)
        match = re.search("\n.*release ([0-9]+\.[0-9]+).*\n", p.stdout.decode("utf-8"))
        cuda_version = match.group(1)

    return {
        "gpu_model_name": gpu_model_name,
        "gpu_driver_version": gpu_driver_version,
        "cuda_version": cuda_version,
    }


def get_command_history():
    """
    get_command_history：获取当前用户的命令历史（包括 zsh 的命令时间）。

    返回值：包含 'command' 和可选 'time' 键的字典列表，'time' 为日期时间格式。
    """
    if sys.platform.startswith('linux') or sys.platform == 'darwin':
        # 尝试从 $SHELL 环境变量或 /etc/passwd 检测默认 shell
        import pwd
        shell = os.environ.get('SHELL', pwd.getpwnam(getpass.getuser()).pw_shell)

        if 'bash' in shell:
            shell_type = 'bash'
            history_file = os.path.join(os.environ['HOME'], '.bash_history')
            history_format = 'plain'
        elif 'zsh' in shell:
            shell_type = 'zsh'
            history_file = os.path.join(os.environ['HOME'], '.zsh_history')
            history_format = 'with_time'
        elif 'fish' in shell: # [TODO] Add a support for fish shell
            shell_type = 'fish'
            history_file = os.path.join(os.environ['HOME'], '.local/share/fish/fish_history')
            history_format = 'yaml'
        else:
            raise ValueError(f"Shell not supported or history file unknown for shell: {shell}")

    elif sys.platform == 'win32':
        shell_type = 'powershell'
        history_file = os.path.join(os.environ['APPDATA'], 'Microsoft', 'Windows', 'PowerShell', 'PSReadLine',
                                    'ConsoleHost_history.txt')
        history_format = 'plain'
    else:
        raise ValueError(f"Platform not supported: {sys.platform}")

    try:
        history_lines = []
        with open(history_file, 'rb') as file:  # Open as binary to handle potential non-UTF characters
            for line in file:
                try:
                    # 逐行解码，遇到错误则替换
                    decoded_line = line.decode('utf-8', 'replace').strip()
                    if history_format == 'with_time' and shell_type == 'zsh':
                        # 用正则解析带时间戳的 zsh 历史记录
                        match = re.match(r'^: (\d+):\d+;(.*)', decoded_line)
                        if match:
                            # 将 epoch 时间戳转换为 datetime 对象并格式化
                            epoch_time = int(match.group(1))
                            datetime_obj = datetime.fromtimestamp(epoch_time)
                            formatted_time = datetime_obj.strftime('%Y-%m-%d %H:%M:%S')
                            history_lines.append({
                                'command': match.group(2).strip(),
                                'time': formatted_time
                            })
                    elif history_format == 'yaml' and shell_type == 'fish':
                        if decoded_line.startswith('- cmd:'):
                            command_match = re.match(r'^- cmd: (.*)', decoded_line)
                            command = command_match.group(1).strip() if command_match else None
                        if decoded_line.startswith('when:'):
                            time_match = re.match(r'^when: (\d+)', decoded_line)
                            if time_match:
                                epoch_time = int(time_match.group(1))
                                datetime_obj = datetime.fromtimestamp(epoch_time)
                                formatted_time = datetime_obj.strftime('%Y-%m-%d %H:%M:%S')
                                history_lines.append({
                                    'command': command,
                                    'time': formatted_time
                                })
                    else:
                        history_lines.append({'command': decoded_line, 'time': None})
                except UnicodeDecodeError:
                    # 如果解码失败，跳过该行或做相应处理
                    continue
            # 返回所有命令
            return {"shell_command_history": history_lines[::-1]}
    except Exception as e:
        return f"Failed to read history file: {e}"
