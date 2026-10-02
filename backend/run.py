"""
bai 后端开发启动脚本
--------------------------------------------------------------------------
用法：backend 目录下执行 `python run.py`（可选参数覆盖端口，如 `python run.py 10011`）。
等价于：python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 10001

前置条件：认证服务 auth 已就绪（开发环境 http://localhost:10000）。
"""
import os
import sys
from pathlib import Path

# 后端目录（run.py 位于 backend/ 下）
BACKEND_DIR = Path(__file__).resolve().parent
DEFAULT_PORT = 10001
PROJECT_NAME = "无足鸟古诗词学习助手（bai）"


def main() -> None:
    # 端口：可选第一个参数覆盖（默认 10001，与 backend/.env 及 项目规范.md 保持一致）
    port = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PORT

    if not (BACKEND_DIR / "app" / "main.py").exists():
        print(f"[错误] 未找到后端入口：{BACKEND_DIR / 'app' / 'main.py'}")
        sys.exit(1)
    try:
        import uvicorn  # noqa: F401
    except ImportError:
        print(f"[错误] 缺少依赖，请先执行：pip install -r {BACKEND_DIR / 'requirements.txt'}")
        sys.exit(1)

    # uvicorn 以 import string 加载应用：切到 backend/ 目录（重载监视与相对路径基准），
    # 并确保 backend/ 在 sys.path 中（从其他目录执行本脚本时保证 app 包可导入）
    os.chdir(BACKEND_DIR)
    if str(BACKEND_DIR) not in sys.path:
        sys.path.insert(0, str(BACKEND_DIR))
    print(f"[启动] {PROJECT_NAME} 后端")
    print(f"[地址] http://localhost:{port} （接口文档 http://localhost:{port}/docs）")
    print("[说明] 认证服务 auth 需先就绪（http://localhost:10000）")
    print("[停止] Ctrl+C")
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)


if __name__ == "__main__":
    main()
