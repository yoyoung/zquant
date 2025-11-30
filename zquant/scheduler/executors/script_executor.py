# Copyright 2025 ZQuant Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Author: kevin
# Contact:
#     - Email: kevin@vip.qq.com
#     - Wechat: zquant2025
#     - Issues: https://github.com/zquant/zquant/issues
#     - Documentation: https://docs.zquant.com
#     - Repository: https://github.com/zquant/zquant

"""
脚本执行器
用于执行外部命令或脚本
"""

import os
from pathlib import Path
import shlex
import subprocess
import threading
import time
from typing import Any

from loguru import logger
from sqlalchemy.orm import Session

from zquant.models.scheduler import TaskExecution, TaskType
from zquant.scheduler.base import TaskExecutor


class ScriptExecutor(TaskExecutor):
    """脚本执行器

    用于执行外部命令或脚本，支持：
    - 执行任意命令和脚本
    - 可配置超时时间
    - 自动识别工作目录（使用脚本所在目录）
    - 捕获标准输出和标准错误
    """

    def get_task_type(self) -> TaskType:
        """获取任务类型（脚本执行器不通过任务类型调用，返回任意类型）"""
        return TaskType.COMMON_TASK  # 占位符，实际不通过类型调用

    def execute(self, db: Session, config: dict[str, Any], execution: TaskExecution | None = None) -> dict[str, Any]:
        """
        执行命令/脚本

        Args:
            db: 数据库会话
            config: 任务配置，必须包含以下参数：
                - command: 执行命令/脚本（必需，如：python instock/cron/example_scheduled_job.py）
                - timeout_seconds: 超时时间（可选，默认3600秒）

        Returns:
            执行结果字典，包含：
                - success: 是否成功
                - exit_code: 退出码
                - stdout: 标准输出
                - stderr: 标准错误
                - duration_seconds: 执行时长（秒）
        """
        # 获取配置参数
        command = config.get("command")
        if not command:
            raise ValueError("配置中缺少必需的 'command' 参数")

        timeout_seconds = config.get("timeout_seconds", 3600)

        logger.info(f"[脚本执行] 开始执行命令: {command}")
        logger.debug(f"[脚本执行] 超时时间: {timeout_seconds} 秒")

        # 解析命令（支持空格分隔的命令和参数）
        try:
            command_parts = shlex.split(command)
        except ValueError as e:
            raise ValueError(f"命令解析失败: {e}")

        if not command_parts:
            raise ValueError("命令不能为空")

        # 确定工作目录
        # 如果命令的第一个部分是文件路径，使用文件所在目录
        # 否则使用项目根目录
        work_dir = None
        first_part = command_parts[0]

        # 检查是否是文件路径（相对路径或绝对路径）
        if os.path.exists(first_part):
            script_path = Path(first_part).resolve()
            if script_path.is_file():
                work_dir = str(script_path.parent)
                logger.debug(f"[脚本执行] 使用脚本所在目录作为工作目录: {work_dir}")
        elif "/" in first_part or "\\" in first_part:
            # 可能是相对路径，尝试解析
            script_path = Path(first_part).resolve()
            if script_path.exists() and script_path.is_file():
                work_dir = str(script_path.parent)
                logger.debug(f"[脚本执行] 使用脚本所在目录作为工作目录: {work_dir}")

        # 如果没有找到工作目录，使用项目根目录
        if not work_dir:
            # 获取项目根目录（zquant包的父目录）
            current_file = Path(__file__).resolve()
            # 从 zquant/scheduler/executors/script_executor.py 向上找到项目根目录
            project_root = current_file.parent.parent.parent.parent
            work_dir = str(project_root)
            logger.debug(f"[脚本执行] 使用项目根目录作为工作目录: {work_dir}")

        # 记录开始时间
        start_time = time.time()

        # 设置环境变量，确保使用UTF-8编码（特别是Windows系统）
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"

        # 用于存储输出的列表
        stdout_lines = []
        stderr_lines = []

        def read_output(pipe, output_list, log_level="info"):
            """实时读取输出并记录到日志"""
            try:
                for line in iter(pipe.readline, ""):
                    if not line:
                        break
                    # 移除行尾的换行符
                    line = line.rstrip("\n\r")
                    if line:  # 只记录非空行
                        output_list.append(line)
                        # 识别日志级别：如果行中包含日志级别标识，使用相应的级别
                        # loguru 格式: "时间 | 级别 | 模块:函数:行号 - 消息"
                        if " | DEBUG | " in line:
                            logger.debug(f"[脚本输出] {line}")
                        elif " | INFO | " in line:
                            logger.info(f"[脚本输出] {line}")
                        elif " | WARNING | " in line or " | WARN | " in line:
                            logger.warning(f"[脚本输出] {line}")
                        elif " | ERROR | " in line:
                            logger.error(f"[脚本输出] {line}")
                        elif " | CRITICAL | " in line:
                            logger.critical(f"[脚本输出] {line}")
                        else:
                            # 没有识别到日志级别，根据 log_level 参数决定
                            if log_level == "info":
                                logger.info(f"[脚本输出] {line}")
                            else:
                                logger.warning(f"[脚本错误] {line}")
            except Exception as e:
                logger.error(f"[脚本执行] 读取输出时发生异常: {e}")
            finally:
                pipe.close()

        try:
            # 使用 Popen 创建进程，实现实时输出
            process = subprocess.Popen(
                command_parts,
                cwd=work_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
                bufsize=1,  # 行缓冲
            )

            # 创建线程实时读取 stdout 和 stderr
            stdout_thread = threading.Thread(
                target=read_output, args=(process.stdout, stdout_lines, "info"), daemon=True
            )
            stderr_thread = threading.Thread(
                target=read_output, args=(process.stderr, stderr_lines, "warning"), daemon=True
            )

            stdout_thread.start()
            stderr_thread.start()

            # 等待进程完成，带超时
            try:
                returncode = process.wait(timeout=timeout_seconds)
            except subprocess.TimeoutExpired:
                # 超时，终止进程
                process.kill()
                process.wait()
                duration_seconds = int(time.time() - start_time)
                error_msg = f"命令执行超时（超过 {timeout_seconds} 秒）"
                logger.error(f"[脚本执行] {error_msg}")
                raise Exception(error_msg)

            # 等待输出线程完成
            stdout_thread.join(timeout=1)
            stderr_thread.join(timeout=1)

            # 计算执行时长
            duration_seconds = int(time.time() - start_time)

            # 合并输出
            stdout_text = "\n".join(stdout_lines)
            stderr_text = "\n".join(stderr_lines)

            # 构建结果
            execution_result = {
                "success": returncode == 0,
                "exit_code": returncode,
                "stdout": stdout_text,
                "stderr": stderr_text,
                "duration_seconds": duration_seconds,
                "command": command,
                "work_dir": work_dir,
            }

            if returncode == 0:
                logger.info(f"[脚本执行] 执行成功，退出码: {returncode}，耗时: {duration_seconds} 秒")
            else:
                error_msg = f"命令执行失败，退出码: {returncode}"
                logger.warning(f"[脚本执行] {error_msg}")
                if stderr_text:
                    logger.warning(f"[脚本执行] 完整错误输出:\n{stderr_text}")
                raise Exception(f"{error_msg}\n标准错误: {stderr_text}")

            return execution_result

        except subprocess.TimeoutExpired:
            duration_seconds = int(time.time() - start_time)
            error_msg = f"命令执行超时（超过 {timeout_seconds} 秒）"
            logger.error(f"[脚本执行] {error_msg}")
            raise Exception(error_msg)

        except Exception as e:
            duration_seconds = int(time.time() - start_time)
            error_msg = f"命令执行异常: {e!s}"
            logger.error(f"[脚本执行] {error_msg}")
            raise Exception(error_msg)
