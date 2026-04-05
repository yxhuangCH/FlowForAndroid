"""
Incremental Cache - L3 增量缓存

Git 感知的增量扫描缓存，只扫描变更的文件。

特性:
- 基于 Git commit hash
- 检测文件变更
- 跨分支缓存共享
- 自动失效旧缓存
"""

import hashlib
import json
import subprocess
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


@dataclass
class FileState:
    """文件状态"""

    file_path: str
    content_hash: str
    mtime: float
    size: int


@dataclass
class CommitState:
    """提交状态"""

    commit_hash: str
    scanned_at: str
    files: Dict[str, FileState]  # file_path -> FileState
    parent_commit: Optional[str] = None


class IncrementalCache:
    """
    L3 增量缓存 - Git 感知

    通过 Git 检测变更文件，只扫描变更的部分，大幅提升扫描速度。

    Example:
        ```python
        cache = IncrementalCache()

        # 获取自上次扫描以来的变更文件
        changed_files = cache.get_changed_files(since_commit="HEAD~1")

        # 只扫描变更文件
        for file_path in changed_files:
            scan(file_path)

        # 标记当前提交已扫描
        cache.mark_scanned(current_commit, scanned_files)

        # 获取缓存的文件状态（用于对比）
        file_state = cache.get_file_state(file_path, commit_hash)
        ```
    """

    def __init__(
        self,
        cache_dir: str = ".unified_cache/incremental",
        max_commits: int = 10,
    ):
        """
        初始化增量缓存

        Args:
            cache_dir: 缓存目录
            max_commits: 保留的最大提交记录数
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_commits = max_commits

        self._state_file = self.cache_dir / "state.json"
        self._commits: Dict[str, CommitState] = {}
        self._current_commit: Optional[str] = None

        self._load_state()

    def _load_state(self) -> None:
        """加载状态文件"""
        if self._state_file.exists():
            try:
                with open(self._state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                self._commits = {
                    k: CommitState(
                        commit_hash=v["commit_hash"],
                        scanned_at=v["scanned_at"],
                        files={
                            fp: FileState(**fs)
                            for fp, fs in v.get("files", {}).items()
                        },
                        parent_commit=v.get("parent_commit"),
                    )
                    for k, v in data.get("commits", {}).items()
                }
                self._current_commit = data.get("current_commit")
            except Exception:
                self._commits = {}
                self._current_commit = None
        else:
            self._commits = {}
            self._current_commit = None

    def _save_state(self) -> None:
        """保存状态文件"""
        try:
            data = {
                "version": "1.0",
                "updated_at": datetime.now().isoformat(),
                "current_commit": self._current_commit,
                "commits": {
                    k: {
                        "commit_hash": v.commit_hash,
                        "scanned_at": v.scanned_at,
                        "files": {
                            fp: asdict(fs) for fp, fs in v.files.items()
                        },
                        "parent_commit": v.parent_commit,
                    }
                    for k, v in self._commits.items()
                },
            }

            with open(self._state_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Warning: Failed to save incremental cache state: {e}")

    def _run_git_command(self, args: List[str]) -> Optional[str]:
        """
        运行 Git 命令

        Args:
            args: Git 命令参数

        Returns:
            命令输出或 None
        """
        try:
            result = subprocess.run(
                ["git"] + args,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return result.stdout.strip()
            return None
        except Exception:
            return None

    def get_current_commit(self) -> Optional[str]:
        """
        获取当前 Git commit hash

        Returns:
            commit hash 或 None（如果不是 git 仓库）
        """
        return self._run_git_command(["rev-parse", "HEAD"])

    def get_changed_files(
        self,
        since_commit: Optional[str] = None,
        file_extensions: Optional[List[str]] = None,
    ) -> List[str]:
        """
        获取自指定提交以来的变更文件

        Args:
            since_commit: 起始提交，None 表示使用上次扫描的提交
            file_extensions: 文件扩展名过滤，如 [".kt", ".java"]

        Returns:
            变更文件路径列表
        """
        # 确定起始提交
        if since_commit is None:
            since_commit = self._current_commit

        current_commit = self.get_current_commit()
        if current_commit is None:
            # 不是 git 仓库，返回空列表（表示全部扫描）
            return []

        if since_commit is None:
            # 没有上次扫描记录，返回空列表（表示全部扫描）
            return []

        if since_commit == current_commit:
            # 同一提交，检查文件内容是否有变化
            return self._get_changed_files_in_commit(current_commit, file_extensions)

        # 获取 git diff 的变更文件
        output = self._run_git_command(
            ["diff", "--name-only", f"{since_commit}...{current_commit}"]
        )

        if output is None:
            return []

        changed_files = output.split("\n") if output else []

        # 过滤扩展名
        if file_extensions:
            changed_files = [
                f
                for f in changed_files
                if any(f.endswith(ext) for ext in file_extensions)
            ]

        return [f for f in changed_files if f]

    def _get_changed_files_in_commit(
        self,
        commit_hash: str,
        file_extensions: Optional[List[str]] = None,
    ) -> List[str]:
        """
        获取在当前提交中内容有变化的文件

        通过比较文件内容哈希来判断。
        """
        commit_state = self._commits.get(commit_hash)
        if commit_state is None:
            return []

        changed = []

        for file_path, old_state in commit_state.files.items():
            # 过滤扩展名
            if file_extensions:
                if not any(file_path.endswith(ext) for ext in file_extensions):
                    continue

            # 检查文件是否存在
            if not Path(file_path).exists():
                changed.append(file_path)
                continue

            # 计算当前内容哈希
            current_hash = self._compute_file_hash(file_path)
            if current_hash != old_state.content_hash:
                changed.append(file_path)

        return changed

    def _compute_file_hash(self, file_path: str) -> str:
        """计算文件内容哈希"""
        try:
            with open(file_path, "rb") as f:
                return hashlib.sha256(f.read()).hexdigest()[:16]
        except Exception:
            return ""

    def _get_file_state(self, file_path: str) -> Optional[FileState]:
        """获取文件当前状态"""
        path = Path(file_path)
        if not path.exists():
            return None

        try:
            stat = path.stat()
            return FileState(
                file_path=file_path,
                content_hash=self._compute_file_hash(file_path),
                mtime=stat.st_mtime,
                size=stat.st_size,
            )
        except Exception:
            return None

    def mark_scanned(
        self,
        commit_hash: str,
        files: List[str],
        parent_commit: Optional[str] = None,
    ) -> None:
        """
        标记指定提交已扫描

        Args:
            commit_hash: 提交哈希
            files: 扫描的文件列表
            parent_commit: 父提交哈希
        """
        # 收集文件状态
        file_states = {}
        for file_path in files:
            state = self._get_file_state(file_path)
            if state:
                file_states[file_path] = state

        # 创建提交状态
        commit_state = CommitState(
            commit_hash=commit_hash,
            scanned_at=datetime.now().isoformat(),
            files=file_states,
            parent_commit=parent_commit or self._current_commit,
        )

        # 保存
        self._commits[commit_hash] = commit_state
        self._current_commit = commit_hash

        # 清理旧记录
        self._cleanup_old_commits()

        # 保存状态
        self._save_state()

    def _cleanup_old_commits(self) -> None:
        """清理旧的提交记录"""
        if len(self._commits) <= self.max_commits:
            return

        # 按扫描时间排序
        sorted_commits = sorted(
            self._commits.items(),
            key=lambda x: x[1].scanned_at,
            reverse=True,
        )

        # 保留最近的
        to_keep = set(k for k, _ in sorted_commits[: self.max_commits])

        # 删除旧的
        self._commits = {k: v for k, v in self._commits.items() if k in to_keep}

    def is_fully_cached(self, commit_hash: str) -> bool:
        """
        检查指定提交是否已完全缓存

        Args:
            commit_hash: 提交哈希

        Returns:
            True 如果该提交已完全扫描
        """
        return commit_hash in self._commits

    def get_last_scanned_commit(self) -> Optional[str]:
        """
        获取上次扫描的提交

        Returns:
            commit hash 或 None
        """
        return self._current_commit

    def get_scan_time(self, commit_hash: str) -> Optional[str]:
        """
        获取指定提交的扫描时间

        Args:
            commit_hash: 提交哈希

        Returns:
            ISO 格式时间字符串或 None
        """
        state = self._commits.get(commit_hash)
        return state.scanned_at if state else None

    def clear(self) -> None:
        """清空所有缓存"""
        self._commits.clear()
        self._current_commit = None
        self._save_state()

    def get_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计

        Returns:
            统计信息字典
        """
        total_files = sum(len(c.files) for c in self._commits.values())

        return {
            "commits_tracked": len(self._commits),
            "current_commit": self._current_commit,
            "total_files_tracked": total_files,
            "max_commits": self.max_commits,
            "cache_dir": str(self.cache_dir),
        }
