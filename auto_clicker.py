"""
自动连点器程序 - 高性能版
功能：选择坐标、配置点击频率、按S键开始/停止
支持极高频率点击（可低至1ms）
支持定时开始和结束
"""

import tkinter as tk
from tkinter import messagebox
import threading
import keyboard
import time
import ctypes
from datetime import datetime, timedelta

# Windows API 函数用于高性能点击
user32 = ctypes.windll.user32

# 鼠标事件常量
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004


class AutoClicker:
    def __init__(self, root):
        self.root = root
        self.root.title("自动连点器")
        self.root.geometry("420x550")
        self.root.resizable(False, False)

        # 设置高DPI支持，让字体更清晰
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except:
            pass

        self.is_clicking = False
        self.is_selecting = False
        self.is_waiting = False  # 是否正在等待定时开始
        self.click_count = 0
        self.last_update_time = 0

        self.setup_ui()
        self.setup_hotkey()

    def validate_number_input(self, new_value):
        """验证输入是否为数字"""
        if new_value == "":
            return True
        try:
            int(new_value)
            return True
        except ValueError:
            return False

    def setup_ui(self):
        """设置用户界面"""
        # 注册验证函数
        vcmd = (self.root.register(self.validate_number_input), '%P')

        # 标题
        title_label = tk.Label(
            self.root,
            text="自动连点器",
            font=("Microsoft YaHei UI", 16, "bold")
        )
        title_label.pack(pady=12)

        # 坐标输入区域
        coord_frame = tk.Frame(self.root)
        coord_frame.pack(pady=12)

        tk.Label(coord_frame, text="X坐标：", font=("Microsoft YaHei UI", 11, "bold")).grid(row=0, column=0, padx=5, sticky="e")
        self.x_var = tk.IntVar(value=0)
        x_entry = tk.Entry(coord_frame, textvariable=self.x_var, width=10, font=("Consolas", 11), validate='key', validatecommand=vcmd)
        x_entry.grid(row=0, column=1, padx=5)

        tk.Label(coord_frame, text="Y坐标：", font=("Microsoft YaHei UI", 11, "bold")).grid(row=0, column=2, padx=5, sticky="e")
        self.y_var = tk.IntVar(value=0)
        y_entry = tk.Entry(coord_frame, textvariable=self.y_var, width=10, font=("Consolas", 11), validate='key', validatecommand=vcmd)
        y_entry.grid(row=0, column=3, padx=5)

        # 坐标操作按钮
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=8)

        select_btn = tk.Button(
            btn_frame,
            text="手动选择坐标",
            command=self.select_coordinates,
            bg="#2196F3",
            fg="white",
            font=("Microsoft YaHei UI", 11, "bold"),
            width=14,
            cursor="hand2"
        )
        select_btn.grid(row=0, column=0, padx=5)

        clear_btn = tk.Button(
            btn_frame,
            text="清空坐标",
            command=self.clear_coordinates,
            bg="#9E9E9E",
            fg="white",
            font=("Microsoft YaHei UI", 11, "bold"),
            width=14,
            cursor="hand2"
        )
        clear_btn.grid(row=0, column=1, padx=5)

        # 点击间隔设置
        freq_frame = tk.Frame(self.root)
        freq_frame.pack(pady=12)

        tk.Label(freq_frame, text="点击间隔（毫秒）：", font=("Microsoft YaHei UI", 11, "bold")).grid(row=0, column=0, padx=5)

        self.interval_var = tk.IntVar(value=10000)
        interval_entry = tk.Entry(
            freq_frame,
            textvariable=self.interval_var,
            width=10,
            font=("Consolas", 11),
            validate='key',
            validatecommand=vcmd
        )
        interval_entry.grid(row=0, column=1, padx=5)

        # 定时设置区域
        timer_frame = tk.LabelFrame(self.root, text="定时设置（可选）", font=("Microsoft YaHei UI", 10, "bold"))
        timer_frame.pack(pady=12, padx=20, fill="x")

        # 开始时间
        start_time_frame = tk.Frame(timer_frame)
        start_time_frame.pack(pady=8)

        tk.Label(start_time_frame, text="开始时间：", font=("Microsoft YaHei UI", 10)).grid(row=0, column=0, padx=5)
        self.start_time_var = tk.StringVar(value="203000")
        start_time_entry = tk.Entry(
            start_time_frame,
            textvariable=self.start_time_var,
            width=20,
            font=("Consolas", 10),
            validate='key',
            validatecommand=vcmd
        )
        start_time_entry.grid(row=0, column=1, padx=5)
        tk.Label(start_time_frame, text="格式: HHMMSS", font=("Microsoft YaHei UI", 9), fg="gray").grid(row=0, column=2, padx=5)

        # 结束时间
        end_time_frame = tk.Frame(timer_frame)
        end_time_frame.pack(pady=8)

        tk.Label(end_time_frame, text="结束时间：", font=("Microsoft YaHei UI", 10)).grid(row=0, column=0, padx=5)
        self.end_time_var = tk.StringVar(value="210000")
        end_time_entry = tk.Entry(
            end_time_frame,
            textvariable=self.end_time_var,
            width=20,
            font=("Consolas", 10),
            validate='key',
            validatecommand=vcmd
        )
        end_time_entry.grid(row=0, column=1, padx=5)
        tk.Label(end_time_frame, text="格式: HHMMSS", font=("Microsoft YaHei UI", 9), fg="gray").grid(row=0, column=2, padx=5)

        # 提示信息
        tk.Label(
            timer_frame,
            text="留空则不启用定时功能",
            font=("Microsoft YaHei UI", 9),
            fg="gray"
        ).pack(pady=5)

        # 控制按钮
        control_frame = tk.Frame(self.root)
        control_frame.pack(pady=18)

        self.start_btn = tk.Button(
            control_frame,
            text="开始(S键)",
            command=self.start_clicking,
            bg="#4CAF50",
            fg="white",
            font=("Microsoft YaHei UI", 12, "bold"),
            width=12,
            height=2,
            relief="raised",
            cursor="hand2"
        )
        self.start_btn.grid(row=0, column=0, padx=10)

        self.stop_btn = tk.Button(
            control_frame,
            text="停止 (S键)",
            command=self.stop_clicking,
            bg="#FF5722",
            fg="white",
            font=("Microsoft YaHei UI", 12, "bold"),
            width=12,
            height=2,
            relief="raised",
            cursor="hand2",
            state="disabled"
        )
        self.stop_btn.grid(row=0, column=1, padx=10)

        # 状态显示
        self.status_label = tk.Label(
            self.root,
            text="状态：待机中",
            font=("Microsoft YaHei UI", 11, "bold"),
            fg="gray"
        )
        self.status_label.pack(pady=12)

        # 点击计数显示
        self.count_label = tk.Label(
            self.root,
            text="点击次数: 0",
            font=("Consolas", 12, "bold"),
            fg="blue"
        )
        self.count_label.pack(pady=5)

        # 取消所有输入框的焦点
        self.root.focus_set()

    def setup_hotkey(self):
        """设置热键监听"""
        keyboard.on_press_key('s', lambda _: self.handle_s_key())

    def handle_s_key(self):
        """S键处理：确认坐标 -> 开始点击 -> 停止点击"""
        if self.is_selecting:
            # 如果正在选择坐标，S键确认坐标
            self.confirm_coordinates()
        elif self.is_clicking or self.is_waiting:
            # 如果正在点击或等待定时，S键停止
            self.stop_clicking()
        else:
            # 否则S键开始点击
            self.start_clicking()

    def select_coordinates(self):
        """选择点击坐标"""
        if self.is_clicking:
            messagebox.showwarning("警告", "请先停止点击再选择坐标！")
            return

        if self.is_selecting:
            return

        self.is_selecting = True
        self.status_label.config(text="状态：请移动鼠标到目标位置，按 S 键确认", fg="red")

    def confirm_coordinates(self):
        """确认坐标位置"""
        if not self.is_selecting:
            return

        # 使用 Windows API 获取鼠标位置（更快）
        class POINT(ctypes.Structure):
            _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

        point = POINT()
        user32.GetCursorPos(ctypes.byref(point))
        x, y = point.x, point.y

        self.x_var.set(x)
        self.y_var.set(y)
        self.is_selecting = False
        self.status_label.config(text=f"状态：坐标已选择 ({x}, {y})", fg="blue")

    def clear_coordinates(self):
        """清空坐标"""
        if self.is_clicking:
            messagebox.showwarning("警告", "请先停止点击再清空坐标！")
            return

        self.x_var.set(0)
        self.y_var.set(0)
        self.status_label.config(text="状态：坐标已清空", fg="gray")

    def parse_time(self, time_str):
        """解析时间字符串，只支持纯数字格式（HHMMSS 或 HHMM）"""
        time_str = time_str.strip()
        if not time_str:
            return None

        try:
            # 只支持纯数字格式
            if not time_str.isdigit():
                return None
            
            if len(time_str) == 6:  # HHMMSS
                hour = int(time_str[0:2])
                minute = int(time_str[2:4])
                second = int(time_str[4:6])
            elif len(time_str) == 4:  # HHMM
                hour = int(time_str[0:2])
                minute = int(time_str[2:4])
                second = 0
            else:
                return None

            # 验证时间有效性
            if not (0 <= hour <= 23 and 0 <= minute <= 59 and 0 <= second <= 59):
                return None

            now = datetime.now()
            target_time = now.replace(hour=hour, minute=minute, second=second, microsecond=0)

            # 如果目标时间已过，设为明天
            if target_time < now:
                target_time += timedelta(days=1)

            return target_time
        except:
            return None

    def start_clicking(self):
        """开始自动点击 - 使用高性能 Windows API"""
        try:
            x = self.x_var.get()
            y = self.y_var.get()

            if x == 0 and y == 0:
                messagebox.showwarning("警告", "请先选择或输入点击坐标！")
                return

            interval = self.interval_var.get()
            if interval <= 0:
                messagebox.showwarning("警告", "点击间隔必须大于0毫秒！")
                return
        except:
            messagebox.showwarning("警告", "请输入有效的坐标和间隔！")
            return

        # 解析定时设置
        start_time_str = self.start_time_var.get()
        end_time_str = self.end_time_var.get()

        start_time = self.parse_time(start_time_str)
        end_time = self.parse_time(end_time_str)

        # 验证时间格式
        if start_time_str and not start_time:
            messagebox.showwarning("警告", "开始时间格式错误！请使用纯数字格式 HHMMSS 或 HHMM")
            return

        if end_time_str and not end_time:
            messagebox.showwarning("警告", "结束时间格式错误！请使用纯数字格式 HHMMSS 或 HHMM")
            return

        # 如果设置了开始时间，验证必须在当前时间之后
        if start_time:
            now = datetime.now()
            # 允许1秒的误差，避免在输入时正好到达该时间
            if start_time <= now + timedelta(seconds=1):
                messagebox.showwarning("警告", "开始时间必须在当前时间之后！")
                return

        # 如果同时设置了开始和结束时间，确保结束时间在开始时间之后
        if start_time and end_time:
            if end_time <= start_time:
                messagebox.showwarning("警告", "结束时间必须在开始时间之后！")
                return
        
        # 如果只设置了结束时间（没有开始时间），验证结束时间必须在当前时间之后
        if end_time and not start_time:
            now = datetime.now()
            if end_time <= now + timedelta(seconds=1):
                messagebox.showwarning("警告", "结束时间必须在当前时间之后！")
                return

        self.click_count = 0
        self.last_update_time = time.time()
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")

        def update_count_display(count):
            """更新点击次数显示"""
            self.count_label.config(text=f"点击次数: {count}")

        def update_status(text, color):
            """更新状态显示"""
            self.status_label.config(text=text, fg=color)

        def high_performance_click():
            """高性能点击循环 - 直接使用 Windows API"""
            interval_sec = self.interval_var.get() / 1000.0
            target_x = self.x_var.get()
            target_y = self.y_var.get()

            # 等待开始时间
            if start_time:
                self.is_waiting = True
                self.root.after(0, update_status, f"状态：等待开始 ({start_time.strftime('%H:%M:%S')})", "orange")

                while self.is_waiting and datetime.now() < start_time:
                    remaining = (start_time - datetime.now()).total_seconds()
                    if remaining > 0:
                        mins, secs = divmod(int(remaining), 60)
                        hours, mins = divmod(mins, 60)
                        self.root.after(0, update_status, f"状态：等待开始 (剩余 {hours:02d}:{mins:02d}:{secs:02d})", "orange")
                    time.sleep(0.5)

                if not self.is_waiting:
                    return

                self.is_waiting = False

            # 开始点击
            self.is_clicking = True
            self.root.after(0, update_status, "状态：点击中...", "green")

            while self.is_clicking:
                # 检查是否到达结束时间
                if end_time and datetime.now() >= end_time:
                    self.root.after(0, self.stop_clicking)
                    break

                try:
                    # 移动鼠标到目标位置
                    user32.SetCursorPos(target_x, target_y)

                    # 执行鼠标左键按下和释放（点击）
                    user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                    user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)

                    self.click_count += 1

                    # 实时更新显示：每隔 50ms 或每 10 次点击更新一次
                    current_time = time.time()
                    if (current_time - self.last_update_time) >= 0.05 or self.click_count % 10 == 0:
                        self.root.after(0, update_count_display, self.click_count)
                        self.last_update_time = current_time

                    # 高精度延迟
                    if interval_sec > 0:
                        time.sleep(interval_sec)

                except Exception as e:
                    print(f"点击错误: {e}")
                    break

            # 点击停止后更新最终计数
            self.root.after(0, update_count_display, self.click_count)

        threading.Thread(target=high_performance_click, daemon=True).start()

    def stop_clicking(self):
        """停止自动点击"""
        if not self.is_clicking and not self.is_waiting:
            return

        self.is_clicking = False
        self.is_waiting = False
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.status_label.config(text="状态：已停止", fg="red")

    def on_closing(self):
        """关闭程序时的处理"""
        self.stop_clicking()
        self.is_selecting = False
        self.is_waiting = False
        keyboard.unhook_all()
        self.root.destroy()


def main():
    root = tk.Tk()
    app = AutoClicker(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()
