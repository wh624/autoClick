# 自动点击器使用说明 - 高性能版

## 功能特性
- 🎯 可视化界面选择点击坐标
- ⚡ **支持极速点击：1ms - 1000ms 间隔**
- 🚀 **使用 Windows API 直接调用，性能提升 10-100 倍**
- ⏱️ 自定义点击频率（毫秒为单位）
- ⌨️ 按 S 键快速停止点击
- 📊 实时显示点击次数
- 🛡️ 多重安全保护机制

## 性能对比

| 方案 | 最低间隔 | 实际点击速度 |
|------|---------|-------------|
| 旧版 (PyAutoGUI) | 100ms | 受限于内置延迟 |
| **新版 (Windows API)** | **1ms** | **极速，无延迟** |

## 为什么这么快？

1. **直接使用 Windows API**：`user32.dll` 的 `mouse_event` 函数
2. **移除了 PyAutoGUI 的 0.1 秒内置延迟**
3. **优化了线程性能**：减少不必要的 GUI 更新
4. **高精度计时**：支持毫秒级精确控制

## 安装依赖

```bash
pip install -r requirements.txt
```

## 运行程序

```bash
python auto_clicker.py
```

## 使用步骤

1. 点击"选择坐标"按钮
2. 移动鼠标到目标位置，按 S 键确认
3. 在"点击间隔"输入框中设置频率（单位：毫秒）
   - 极速点击：1-10ms
   - 快速点击：10-50ms
   - 正常点击：50-200ms
   - 慢速点击：200-1000ms
4. 点击"开始点击"按钮或按 S 键
5. 需要停止时，按 S 键即可停止

## 推荐间隔设置

| 场景 | 推荐间隔 |
|------|---------|
| 游戏连点 | 10-20ms |
| 自动化测试 | 50-100ms |
| 普通点击 | 100-500ms |
| 慢速操作 | 500-1000ms |

⚠️ **注意**：
- 间隔设置为 1-5ms 时，点击速度极快，请谨慎使用
- 某些应用程序可能会检测异常点击速度
- 建议先从较大间隔开始测试

## 编译成 EXE 文件

### 方法一：使用 PyInstaller（推荐）

```bash
# 安装 PyInstaller
pip install pyinstaller

# 编译成单个 exe 文件（推荐）
pyinstaller --onefile --windowed --name=autoClicker --icon=app_icon.ico auto_clicker.py

# 编译后的 exe 文件在 dist 目录下
```

### 方法二：使用批处理脚本（最简单）

直接双击运行 `build_exe.bat`，自动完成编译

### 方法三：使用 auto-py-to-exe（图形化界面）

```bash
# 安装 auto-py-to-exe
pip install auto-py-to-exe

# 启动图形化界面
auto-py-to-exe

# 然后在界面中：
# 1. 选择 auto_clicker.py 文件
# 2. 选择 "One File" 模式
# 3. 选择 "Window Based" (隐藏控制台)
# 4. 点击 "CONVERT .PY TO .EXE"
```

## PyInstaller 参数说明

- `--onefile`: 打包成单个exe文件
- `--windowed`: 不显示控制台窗口
- `--name`: 指定exe文件名称
- `--icon`: 指定图标文件（可选）
- `--add-data`: 添加额外的数据文件（如果需要）

## 技术原理

### Windows API 调用

程序使用以下 Windows API 函数：

```python
# 获取鼠标位置
user32.GetCursorPos()

# 设置鼠标位置
user32.SetCursorPos(x, y)

# 模拟鼠标点击
user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
```

这些 API 函数直接与操作系统交互，无需经过 Python 库的封装，因此速度极快。

## 常见问题

### Q: 为什么点击间隔设置为 1ms 还是感觉没那么快？
A: 1ms 已经是极限速度（每秒 1000 次点击）。某些应用程序可能无法响应如此高频的点击。

### Q: 程序在某些应用中不工作？
A: 尝试以管理员权限运行程序。某些应用程序有安全保护。

### Q: 如何紧急停止？
A: 按 S 键即可立即停止点击。

### Q: 点击次数显示不准确？
A: 为了性能，显示每 100 次更新一次。实际点击次数是准确的。

## 注意事项

⚠️ **重要提示**：
- 本程序仅用于学习和合法用途
- 不要在禁止使用自动化工具的游戏或应用中使用
- 使用时请确保目标坐标正确
- 极高频率点击可能对硬件造成压力
- 建议先用较长的间隔测试

## 系统要求

- Windows 7/10/11
- Python 3.7+
- 依赖库：keyboard（无需 pyautogui）

## 更新日志

### v2.0 - 高性能版
- ✨ 使用 Windows API 替代 PyAutoGUI
- ⚡ 支持 1ms 极速点击
- 📊 添加点击次数实时统计
- 🎨 优化界面显示

### v1.0 - 初始版本
- 基础点击功能
- 使用 PyAutoGUI 库
