# run_once.py
import sys
from pathlib import Path
import importlib

project_root = Path(__file__).resolve().parent

# 1) Ensure project root is on sys.path so "import src.main" works.
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# 2) Also add src/ to sys.path so modules that do "from utils..." can import src/utils as top-level 'utils'
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# Debugging prints (optional)
# print("sys.path (head):", sys.path[:3])

try:
    module = importlib.import_module("src.main")
except Exception as e:
    print("❌ Failed to import 'src.main':", e)
    print("Make sure 'src/main.py' exists and both project root and src/ are on sys.path.")
    raise SystemExit(1)

# Ensure run_cycle is present
if not hasattr(module, "run_cycle"):
    print("❌ 'src.main' imported but 'run_cycle' not found. Inspect src/main.py to ensure run_cycle is defined at module level.")
    raise SystemExit(1)

run_cycle = getattr(module, "run_cycle")

if __name__ == "__main__":
    print("▶️ Running one cycle of the autonomous trading agent (run_once)...")
    try:
        run_cycle()
        print("✅ Single cycle complete.")
    except Exception as e:
        print("❌ Exception during run_cycle():", e)
        raise
