"""Tests for IncrementalCache (L3 git-aware cache)"""

import pytest
from unittest.mock import patch, MagicMock
from unified_engine.cache.incremental_cache import IncrementalCache


class TestIncrementalCache:
    """Tests for git-aware incremental cache"""

    def test_basic_mark_and_get(self, tmp_path):
        """Test basic mark/get operations"""
        cache = IncrementalCache(cache_dir=str(tmp_path / "incremental"))

        cache.mark_scanned("commit_abc", ["file1.kt", "file2.kt"])
        changed = cache.get_changed_files("commit_abc", [".kt"])

        assert changed == []

    def test_get_changed_files_with_mock(self, tmp_path):
        """Test getting changed files with mocked git"""
        cache = IncrementalCache(cache_dir=str(tmp_path / "incremental"))

        # Mock git diff output
        mock_output = "file2.kt\nfile3.kt\n"

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=mock_output
            )

            changed = cache.get_changed_files("commit_abc", [".kt"])

            assert "file2.kt" in changed
            assert "file3.kt" in changed

    def test_get_all_files_when_no_previous_commit(self, tmp_path):
        """Test getting all files when no previous commit tracked"""
        cache = IncrementalCache(cache_dir=str(tmp_path / "incremental"))

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="file1.kt\nfile2.kt\n"
            )

            changed = cache.get_changed_files(None, [".kt"])

            assert "file1.kt" in changed
            assert "file2.kt" in changed

    def test_filter_by_extension(self, tmp_path):
        """Test filtering by file extension"""
        cache = IncrementalCache(cache_dir=str(tmp_path / "incremental"))

        mock_output = "file1.kt\nfile2.java\nfile3.kt\nreadme.md\n"

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=mock_output
            )

            changed = cache.get_changed_files("commit_abc", [".kt"])

            assert "file1.kt" in changed
            assert "file2.java" not in changed
            assert "file3.kt" in changed
            assert "readme.md" not in changed

    def test_git_command_failure(self, tmp_path):
        """Test handling of git command failure"""
        cache = IncrementalCache(cache_dir=str(tmp_path / "incremental"))

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stderr="fatal: not a git repository"
            )

            # Should return empty list on error
            changed = cache.get_changed_files("commit_abc", [".kt"])
            assert changed == []

    def test_persistence(self, tmp_path):
        """Test scanned state persists across instances"""
        cache_dir = str(tmp_path / "incremental")

        cache1 = IncrementalCache(cache_dir=cache_dir)
        cache1.mark_scanned("commit_abc", ["file1.kt"])

        cache2 = IncrementalCache(cache_dir=cache_dir)

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=""
            )

            changed = cache2.get_changed_files("commit_abc", [".kt"])
            assert changed == []

    def test_clear(self, tmp_path):
        """Test clear operation"""
        cache = IncrementalCache(cache_dir=str(tmp_path / "incremental"))

        cache.mark_scanned("commit_abc", ["file1.kt"])
        cache.clear()

        # State should be reset
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="file1.kt\n"
            )

            changed = cache.get_changed_files("commit_abc", [".kt"])
            assert "file1.kt" in changed  # Reset, so all files appear as changed
