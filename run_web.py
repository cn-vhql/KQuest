#!/usr/bin/env python3
"""启动Web UI的便捷脚本"""

import sys
import subprocess
from pathlib import Path

def main():
    """启动Streamlit应用"""
    # 确保项目根目录在Python路径中
    project_root = Path(__file__).parent
    web_ui_path = project_root / "src" / "kquest" / "web_ui.py"

    if not web_ui_path.exists():
        print(f"错误: 找不到Web UI文件 {web_ui_path}")
        sys.exit(1)

    # 启动Streamlit
    cmd = [
        sys.executable, "-m", "streamlit", "run",
        str(web_ui_path),
        "--server.port=8501",
        "--server.address=0.0.0.0",
        "--browser.gatherUsageStats=false",
        "--theme.base=light"
    ]

    print("🚀 启动KQuest Web UI...")
    print(f"📍 访问地址: http://localhost:8501")
    print("🔄 正在启动服务器...")

    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\n👋 服务器已停止")
    except subprocess.CalledProcessError as e:
        print(f"❌ 启动失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()