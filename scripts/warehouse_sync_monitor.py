#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZBC 生产仓库同步监控模块

功能：
    监控本地 Git 仓库与远端（origin/main）的同步状态。
    检测是否存在未推送的本地提交或未拉取的远端更新。
    提供命令行接口用于 CI/CD 流水线或人工巡检。

依赖：
    仅依赖 Python 标准库 (subprocess, sys)。

作者：OSAI Agent
"""

import subprocess
import sys
from typing import Tuple, List


def run_git_command(args: List[str]) -> Tuple[int, str, str]:
    """
    执行 git 命令并返回状态码、标准输出和标准错误。

    Args:
        args: git 命令参数列表，例如 ['rev-parse', '--abbrev-ref', 'HEAD']

    Returns:
        Tuple[return_code, stdout, stderr]
    """
    try:
        process = subprocess.Popen(
            ['git'] + args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate()
        return process.returncode, stdout.strip(), stderr.strip()
    except FileNotFoundError:
        return -1, "", "Error: git command not found. Is git installed and in PATH?"
    except Exception as e:
        return -1, "", f"Unexpected error running git: {str(e)}"


def check_sync_status() -> dict:
    """
    检查仓库同步状态。

    Returns:
        dict: 包含状态信息的字典。
            - 'is_git_repo': bool, 是否在 git 仓库中
            - 'current_branch': str, 当前分支名
            - 'local_ahead': int, 本地领先远端的提交数
            - 'local_behind': int, 本地落后远端的提交数
            - 'status_message': str, 人类可读的状态描述
            - 'needs_push': bool, 是否需要 push
            - 'needs_pull': bool, 是否需要 pull
    """
    result = {
        'is_git_repo': False,
        'current_branch': '',
        'local_ahead': 0,
        'local_behind': 0,
        'status_message': '',
        'needs_push': False,
        'needs_pull': False
    }

    # 1. 检查是否在 git 仓库中
    code, _, _ = run_git_command(['rev-parse', '--is-inside-work-tree'])
    if code != 0:
        result['status_message'] = 'Not a git repository.'
        return result
    result['is_git_repo'] = True

    # 2. 获取当前分支
    code, branch, _ = run_git_command(['rev-parse', '--abbrev-ref', 'HEAD'])
    if code != 0 or branch == 'HEAD':
        result['status_message'] = 'Not on any branch (detached HEAD state).'
        return result
    result['current_branch'] = branch

    # 3. 获取远端跟踪分支 (例如 origin/main)
    code, remote_ref, _ = run_git_command(['rev-parse', '--abbrev-ref', f'{branch}@{{u}}'])
    if code != 0:
        result['status_message'] = f'Branch "{branch}" has no upstream tracking branch.'
        return result

    # 4. 获取提交差异统计
    # git rev-list --left-right --count HEAD...@{u}
    # 输出格式: "<local_ahead>\t<local_behind>"
    code, count_output, _ = run_git_command(['rev-list', '--left-right', '--count', f'HEAD...{remote_ref}'])
    if code == 0 and count_output:
        try:
            ahead_str, behind_str = count_output.split('\t')
            result['local_ahead'] = int(ahead_str)
            result['local_behind'] = int(behind_str)
        except ValueError:
            result['status_message'] = f'Failed to parse commit count: {count_output}'
            return result
    else:
        result['status_message'] = 'Failed to get commit difference.'
        return result

    # 5. 生成状态消息
    result['needs_push'] = result['local_ahead'] > 0
    result['needs_pull'] = result['local_behind'] > 0

    if result['needs_push'] and result['needs_pull']:
        result['status_message'] = (f"Diverged: Local is {result['local_ahead']} commit(s) ahead and "
                                    f"{result['local_behind']} commit(s) behind '{remote_ref}'.")
    elif result['needs_push']:
        result['status_message'] = (f"Ahead: Local is {result['local_ahead']} commit(s) ahead of "
                                    f"'{remote_ref}'. Needs push.")
    elif result['needs_pull']:
        result['status_message'] = (f"Behind: Local is {result['local_behind']} commit(s) behind "
                                    f"'{remote_ref}'. Needs pull.")
    else:
        result['status_message'] = f"Synced: Local branch '{branch}' is up to date with '{remote_ref}'."

    return result


def main():
    """
    命令行入口。
    打印同步状态并返回相应的退出码。
    Exit 0: 同步一致
    Exit 1: 需要操作 (push/pull) 或出错
    """
    status = check_sync_status()
    print(f"[Sync Monitor] {status['status_message']}")

    if not status['is_git_repo']:
        sys.exit(1)

    if status['needs_push'] or status['needs_pull']:
        print("Action Required: Please synchronize your repository.")
        sys.exit(1)
    else:
        print("Status OK: No sync action needed.")
        sys.exit(0)


if __name__ == '__main__':
    main()
