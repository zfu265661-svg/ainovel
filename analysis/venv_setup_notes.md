# venv setup notes

## 在 VS Code 里选择解释器

创建好 `.venv` 后，打开命令面板，运行 `Python: Select Interpreter`，然后选择项目里的 `.venv\Scripts\python.exe`。
如果工作区已经应用了 `.vscode/settings.json`，通常会优先显示这个解释器，但仍建议手动确认一次。

## 如果 Pylance 仍报“无法解析导入 dotenv”

先检查三件事：

1. 当前选中的 VS Code Python 解释器是不是项目里的 `.venv\Scripts\python.exe`
2. 依赖是否已经安装到这个环境里：`python -m pip install -r requirements.txt`
3. 当前终端里的 `python -c "import sys; print(sys.executable)"` 输出是否和 VS Code 选中的解释器一致

## 终端和 VS Code 解释器不一致时如何确认

在 VS Code 终端里运行：

```bash
python -c "import sys; print(sys.executable)"
```

然后对照 VS Code 状态栏或 `Python: Select Interpreter` 里显示的解释器路径。
如果两边不是同一个 `.venv\Scripts\python.exe`，就说明终端和编辑器没有对齐，需要重新选择解释器或重新打开终端。
