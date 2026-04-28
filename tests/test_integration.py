"""tests/test_integration.py — 集成验收测试（v2）"""

import subprocess
from pathlib import Path

import pytest

# v2 Profile 路径
PROFILE_DIR = Path("~/.local/share/google_search/profile").expanduser()


@pytest.fixture
def skip_if_no_profile():
    """如果 Profile 不存在或为空，跳过测试"""
    if not PROFILE_DIR.exists():
        pytest.skip("Profile 目录不存在，需要先运行 google-search login")
    if not list(PROFILE_DIR.glob("**/*")):
        pytest.skip("Profile 为空，需要先运行 google-search login")


class TestSearchWithProfile:
    """验收标准：使用已登录 Profile 搜索时，不应返回致命错误"""

    def test_search_exits_zero_or_one(self, skip_if_no_profile, tmp_path):
        """
        验收标准 1: 搜索命令退出码为 0（成功）或 1（部分成功）
        """
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        result = subprocess.run(
            [
                "python", "-m", "google_search",
                "测试公司", "company",
                "--output-dir", str(output_dir),
            ],
            capture_output=True,
            text=True,
            timeout=180,
            cwd=str(Path(__file__).parent.parent),
        )

        assert result.returncode in (0, 1), (
            f"搜索失败 (exit={result.returncode}):\n"
            f"stdout: {result.stdout}\n"
            f"stderr: {result.stderr}"
        )

    def test_no_fatal_error(self, skip_if_no_profile, tmp_path):
        """
        验收标准 2: 不包含 FatalError 退出码 2
        """
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        result = subprocess.run(
            [
                "python", "-m", "google_search",
                "测试公司", "company",
                "--output-dir", str(output_dir),
            ],
            capture_output=True,
            text=True,
            timeout=180,
            cwd=str(Path(__file__).parent.parent),
        )

        assert result.returncode != 2, (
            f"Fatal error (exit=2):\n"
            f"stdout: {result.stdout}\n"
            f"stderr: {result.stderr}"
        )

    def test_json_files_generated(self, skip_if_no_profile, tmp_path):
        """
        验收标准 3: JSON 结果文件存在
        """
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        result = subprocess.run(
            [
                "python", "-m", "google_search",
                "测试公司", "company",
                "--output-dir", str(output_dir),
            ],
            capture_output=True,
            text=True,
            timeout=180,
            cwd=str(Path(__file__).parent.parent),
        )

        if result.returncode not in (0, 1):
            pytest.skip(f"搜索命令失败，跳过 JSON 验证: {result.stderr}")

        # 找到 JSON 文件（v2 格式: entity_templateid_timestamp.json）
        json_files = list(output_dir.glob("测试公司_*.json"))
        assert json_files, f"未找到 JSON 输出文件 (output_dir={output_dir})"

    def test_pdf_generated(self, skip_if_no_profile, tmp_path):
        """
        验收标准 4: PDF 文件存在
        """
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        result = subprocess.run(
            [
                "python", "-m", "google_search",
                "测试公司", "company",
                "--output-dir", str(output_dir),
            ],
            capture_output=True,
            text=True,
            timeout=180,
            cwd=str(Path(__file__).parent.parent),
        )

        if result.returncode not in (0, 1):
            pytest.skip(f"搜索命令失败，跳过 PDF 验证: {result.stderr}")

        pdf_files = list(output_dir.glob("测试公司_*.pdf"))
        assert pdf_files, f"未找到 PDF 输出文件 (output_dir={output_dir})"

        latest_pdf = max(pdf_files, key=lambda p: p.stat().st_mtime)
        assert latest_pdf.stat().st_size > 1000, (
            f"PDF 文件过小 ({latest_pdf.stat().st_size} bytes)，可能不完整"
        )
