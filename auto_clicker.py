"""
自动连点器程序 - 高性能版
功能：左键选取坐标、配置点击频率、按 S 键开始/停止
支持极高频率点击（可低至 1ms）
支持定时开始和结束
"""

import os
import sys
import queue
import tkinter as tk
from tkinter import messagebox
import threading
import keyboard
import time
import ctypes
from datetime import datetime, timedelta

# Windows API 函数用于高性能点击
user32 = ctypes.windll.user32
# 单独加载一份 user32，避免给全局 windll 设置 argtypes 后影响 keyboard 的钩子
user32_hook = ctypes.WinDLL("user32", use_last_error=True)

# 鼠标事件常量
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
WH_MOUSE_LL = 14
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
WM_QUIT = 0x0012
HC_ACTION = 0

# TDesign 默认字体：PingFang SC, Microsoft YaHei, Arial
FONT = "Microsoft YaHei"
# 12px / 14px / 20px 换成 pt，对应 caption、body-medium、title-large
FONT_CAPTION = 9
FONT_BODY = 11
FONT_TITLE = 15

# TDesign Light 默认主题，token 来自 tdesign-common style/web/theme/_light.less
PALETTE = {
    "bg": "#eeeeee",
    "card": "#ffffff",
    "line": "#e8e8e8",
    "border": "#dddddd",
    "text": "#1a1a1a",
    "muted": "#666666",
    "placeholder": "#999999",
    "disabled_fg": "#bdbdbd",
    "entry": "#ffffff",
    "white": "#ffffff",
    "brand": "#0052d9",
    "brand_hover": "#366ef4",
    "brand_disabled": "#b5c7ff",
    "success": "#2ba471",
    "success_hover": "#56c08d",
    "success_disabled": "#92dab2",
    "warning": "#e37318",
    "warning_hover": "#fa9550",
    "warning_disabled": "#ffb98c",
    "error": "#d54941",
    "error_hover": "#f6685d",
    "error_disabled": "#ffb9b0",
    "component_disabled": "#eeeeee",
    "ok": "#2ba471",
    "warn": "#e37318",
    "info": "#0052d9",
    "danger": "#d54941",
}

# 对应 Button 的 theme：primary / default / success / danger / warning，variant=base（default 为白底描边）
BUTTON_SPECS = {
    "primary": {
        "bg": "#0052d9", "hover": "#366ef4", "fg": "#ffffff", "hover_fg": "#ffffff",
        "disabled_bg": "#b5c7ff", "disabled_fg": "#ffffff",
        "border": "#0052d9", "hover_border": "#366ef4",
    },
    "default": {
        "bg": "#ffffff", "hover": "#ffffff", "fg": "#1a1a1a", "hover_fg": "#366ef4",
        "disabled_bg": "#eeeeee", "disabled_fg": "#bdbdbd",
        "border": "#dddddd", "hover_border": "#366ef4",
    },
    "success": {
        "bg": "#2ba471", "hover": "#56c08d", "fg": "#ffffff", "hover_fg": "#ffffff",
        "disabled_bg": "#92dab2", "disabled_fg": "#ffffff",
        "border": "#2ba471", "hover_border": "#56c08d",
    },
    "danger": {
        "bg": "#d54941", "hover": "#f6685d", "fg": "#ffffff", "hover_fg": "#ffffff",
        "disabled_bg": "#ffb9b0", "disabled_fg": "#ffffff",
        "border": "#d54941", "hover_border": "#f6685d",
    },
    "warning": {
        "bg": "#e37318", "hover": "#fa9550", "fg": "#ffffff", "hover_fg": "#ffffff",
        "disabled_bg": "#ffb98c", "disabled_fg": "#ffffff",
        "border": "#e37318", "hover_border": "#fa9550",
    },
}


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


class MSLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("pt", POINT),
        ("mouseData", ctypes.c_ulong),
        ("flags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.c_void_p),
    ]


LRESULT = ctypes.c_ssize_t
LowLevelMouseProc = ctypes.WINFUNCTYPE(
    LRESULT,
    ctypes.c_int,
    ctypes.c_size_t,
    ctypes.c_void_p,
)

user32_hook.SetWindowsHookExW.argtypes = [
    ctypes.c_int,
    LowLevelMouseProc,
    ctypes.c_void_p,
    ctypes.c_ulong,
]
user32_hook.SetWindowsHookExW.restype = ctypes.c_void_p
user32_hook.CallNextHookEx.argtypes = [
    ctypes.c_void_p,
    ctypes.c_int,
    ctypes.c_size_t,
    ctypes.c_void_p,
]
user32_hook.CallNextHookEx.restype = LRESULT
user32_hook.UnhookWindowsHookEx.argtypes = [ctypes.c_void_p]
user32_hook.UnhookWindowsHookEx.restype = ctypes.wintypes.BOOL


class MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", ctypes.c_void_p),
        ("message", ctypes.c_uint),
        ("wParam", ctypes.c_size_t),
        ("lParam", ctypes.c_ssize_t),
        ("time", ctypes.c_ulong),
        ("pt", POINT),
    ]


user32_hook.GetMessageW.argtypes = [ctypes.POINTER(MSG), ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint]
user32_hook.GetMessageW.restype = ctypes.c_int
user32_hook.TranslateMessage.argtypes = [ctypes.POINTER(MSG)]
user32_hook.TranslateMessage.restype = ctypes.wintypes.BOOL
user32_hook.DispatchMessageW.argtypes = [ctypes.POINTER(MSG)]
user32_hook.DispatchMessageW.restype = ctypes.c_ssize_t
user32_hook.PostThreadMessageW.argtypes = [ctypes.c_ulong, ctypes.c_uint, ctypes.c_size_t, ctypes.c_ssize_t]
user32_hook.PostThreadMessageW.restype = ctypes.wintypes.BOOL

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
kernel32.GetCurrentThreadId.restype = ctypes.c_ulong


def enable_dpi_awareness():
    """在创建窗口前打开 DPI 感知，避免高分屏上字体发虚。"""
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            user32.SetProcessDPIAware()
        except Exception:
            pass


def resource_path(relative_path):
    """获取资源文件路径，兼容源码运行和 PyInstaller 打包。"""
    if getattr(sys, "frozen", False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


def set_window_icon(root):
    """设置窗口标题栏和任务栏图标。"""
    ico_path = resource_path("app_icon.ico")
    png_path = resource_path("zjzp.png")
    try:
        if os.path.exists(ico_path):
            root.iconbitmap(default=ico_path)
    except Exception:
        pass
    try:
        if os.path.exists(png_path):
            root._icon_photo = tk.PhotoImage(file=png_path)
            root.iconphoto(True, root._icon_photo)
    except Exception:
        pass


class AutoClicker:
    def __init__(self, root):
        self.root = root
        self.colors = PALETTE
        self.root.title("自动连点器")
        self.root.configure(bg=self.colors["bg"])
        set_window_icon(self.root)

        self.is_clicking = False
        self.is_selecting = False
        self.is_waiting = False  # 是否正在等待定时开始
        self.click_count = 0
        self.last_update_time = 0
        self._alive = True
        self._mouse_hook = None
        self._mouse_proc = None
        self._hook_thread = None
        self._hook_thread_id = None
        self._pick_queue = queue.Queue()
        self._pick_hwnd = None
        self._picked_point = None
        self._ignore_click = False

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

    def _card(self, parent, title, hint=None):
        """TDesign Card：白底容器、1px 分割线、16px 内边距。"""
        wrap = tk.Frame(parent, bg=self.colors["bg"])
        wrap.pack(fill="x", pady=(0, 16))
        body = tk.Frame(
            wrap,
            bg=self.colors["card"],
            highlightthickness=1,
            highlightbackground=self.colors["line"],
            highlightcolor=self.colors["line"],
        )
        body.pack(fill="x")
        head = tk.Frame(body, bg=self.colors["card"], padx=16, pady=12)
        head.pack(fill="x")
        tk.Label(
            head,
            text=title,
            bg=self.colors["card"],
            fg=self.colors["text"],
            font=(FONT, FONT_BODY),
        ).pack(side="left")
        if hint:
            tk.Label(
                head,
                text=hint,
                bg=self.colors["card"],
                fg=self.colors["placeholder"],
                font=(FONT, FONT_CAPTION),
            ).pack(side="right")
        divider = tk.Frame(body, bg=self.colors["line"], height=1)
        divider.pack(fill="x")
        divider.pack_propagate(False)
        content = tk.Frame(body, bg=self.colors["card"], padx=16, pady=16)
        content.pack(fill="x")
        return content

    def _entry(self, parent, variable, width):
        return tk.Entry(
            parent,
            textvariable=variable,
            width=width,
            font=(FONT, FONT_BODY),
            bg=self.colors["entry"],
            fg=self.colors["text"],
            insertbackground=self.colors["text"],
            disabledbackground=self.colors["component_disabled"],
            relief="flat",
            highlightthickness=1,
            highlightbackground=self.colors["border"],
            highlightcolor=self.colors["brand"],
            validate="key",
            validatecommand=self._vcmd,
        )

    def _button(self, parent, text, command, kind):
        shell = tk.Frame(parent, padx=1, pady=1)
        btn = tk.Button(
            shell,
            text=text,
            command=command,
            font=(FONT, FONT_BODY),
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            cursor="hand2",
            padx=16,
            pady=4,
        )
        btn.pack(fill="both", expand=True)
        btn._shell = shell
        btn.grid = shell.grid
        btn.bind("<Enter>", lambda _e, b=btn: self._on_btn_enter(b))
        btn.bind("<Leave>", lambda _e, b=btn: self._on_btn_leave(b))
        self._apply_button_theme(btn, kind)
        return btn

    def _apply_button_theme(self, btn, kind):
        spec = BUTTON_SPECS[kind]
        btn._kind = kind
        btn._normal_bg = spec["bg"]
        btn._hover_bg = spec["hover"]
        btn._normal_fg = spec["fg"]
        btn._hover_fg = spec["hover_fg"]
        btn._disabled_bg = spec["disabled_bg"]
        btn._disabled_fg = spec["disabled_fg"]
        btn._border = spec["border"]
        btn._hover_border = spec["hover_border"]
        btn.configure(
            activebackground=spec["hover"],
            activeforeground=spec["hover_fg"],
            disabledforeground=spec["disabled_fg"],
        )
        if str(btn.cget("state")) == "disabled":
            self._paint_button(btn, spec["disabled_bg"], spec["disabled_fg"], spec["border"])
        else:
            self._paint_button(btn, spec["bg"], spec["fg"], spec["border"])

    def _paint_button(self, btn, bg, fg, border):
        btn.configure(bg=bg, fg=fg)
        btn._shell.configure(bg=border)

    def _on_btn_enter(self, btn):
        if str(btn.cget("state")) != "disabled":
            self._paint_button(btn, btn._hover_bg, btn._hover_fg, btn._hover_border)

    def _on_btn_leave(self, btn):
        if str(btn.cget("state")) != "disabled":
            self._paint_button(btn, btn._normal_bg, btn._normal_fg, btn._border)

    def _set_enabled(self, btn, enabled):
        if enabled:
            btn.configure(state="normal")
            self._paint_button(btn, btn._normal_bg, btn._normal_fg, btn._border)
        else:
            btn.configure(state="disabled")
            self._paint_button(btn, btn._disabled_bg, btn._disabled_fg, btn._border)

    def _field_label(self, parent, text):
        return tk.Label(
            parent,
            text=text,
            bg=self.colors["card"],
            fg=self.colors["text"],
            font=(FONT, FONT_BODY),
        )

    def setup_ui(self):
        """设置用户界面"""
        self._vcmd = (self.root.register(self.validate_number_input), "%P")
        c = self.colors

        outer = tk.Frame(self.root, bg=c["bg"], padx=24, pady=24)
        outer.pack(fill="both", expand=True)

        tk.Label(
            outer,
            text="自动连点器",
            bg=c["bg"],
            fg=c["text"],
            font=(FONT, FONT_TITLE, "bold"),
        ).pack(anchor="w")
        tk.Label(
            outer,
            text="左键选点   ·   S 键开始或停止",
            bg=c["bg"],
            fg=c["placeholder"],
            font=(FONT, FONT_CAPTION),
        ).pack(anchor="w", pady=(4, 16))

        center_x, center_y = self.get_screen_center()
        coord = self._card(outer, "点击位置", "下一记左键即坐标")

        coord_row = tk.Frame(coord, bg=c["card"])
        coord_row.pack(fill="x")
        self._field_label(coord_row, "X").pack(side="left")
        self.x_var = tk.IntVar(value=center_x)
        self._entry(coord_row, self.x_var, 8).pack(side="left", padx=(8, 16))
        self._field_label(coord_row, "Y").pack(side="left")
        self.y_var = tk.IntVar(value=center_y)
        self._entry(coord_row, self.y_var, 8).pack(side="left", padx=(8, 0))

        pick_row = tk.Frame(coord, bg=c["card"])
        pick_row.pack(fill="x", pady=(16, 0))
        pick_row.columnconfigure(0, weight=1)
        pick_row.columnconfigure(1, weight=1)
        self.select_btn = self._button(pick_row, "选取坐标", self.select_coordinates, "primary")
        self.select_btn.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.clear_btn = self._button(pick_row, "清空", self.clear_coordinates, "default")
        self.clear_btn.grid(row=0, column=1, sticky="ew", padx=(8, 0))

        freq = self._card(outer, "点击间隔", "越小越快")
        freq_row = tk.Frame(freq, bg=c["card"])
        freq_row.pack(fill="x")
        self.interval_var = tk.IntVar(value=10000)
        self._entry(freq_row, self.interval_var, 10).pack(side="left")
        self._field_label(freq_row, "毫秒").pack(side="left", padx=(8, 0))

        timer = self._card(outer, "定时", "留空则不启用")
        self.start_time_var = tk.StringVar(value=(datetime.now() + timedelta(minutes=1)).strftime("%H%M%S"))
        self.end_time_var = tk.StringVar(value="210000")
        self._time_row(timer, "开始", self.start_time_var)
        self._time_row(timer, "结束", self.end_time_var, top=12)
        tk.Label(
            timer,
            text="纯数字 HHMMSS，例如 093000",
            bg=c["card"],
            fg=c["placeholder"],
            font=(FONT, FONT_CAPTION),
        ).pack(anchor="w", pady=(12, 0))

        actions = tk.Frame(outer, bg=c["bg"])
        actions.pack(fill="x", pady=(0, 16))
        actions.columnconfigure(0, weight=1)
        actions.columnconfigure(1, weight=1)
        self.start_btn = self._button(actions, "开始", self.start_clicking, "success")
        self.start_btn.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.stop_btn = self._button(actions, "停止", self.stop_clicking, "danger")
        self.stop_btn.grid(row=0, column=1, sticky="ew", padx=(8, 0))
        self._set_enabled(self.stop_btn, False)

        status_card = tk.Frame(
            outer,
            bg=c["card"],
            highlightthickness=1,
            highlightbackground=c["line"],
            highlightcolor=c["line"],
            padx=16,
            pady=16,
        )
        status_card.pack(fill="x")
        self.status_label = tk.Label(
            status_card,
            text="准备就绪",
            bg=c["card"],
            fg=c["muted"],
            font=(FONT, FONT_BODY),
        )
        self.status_label.pack(anchor="w")
        count_row = tk.Frame(status_card, bg=c["card"])
        count_row.pack(fill="x", pady=(8, 0))
        tk.Label(
            count_row,
            text="点击次数",
            bg=c["card"],
            fg=c["placeholder"],
            font=(FONT, FONT_CAPTION),
        ).pack(side="left")
        self.count_label = tk.Label(
            count_row,
            text="0",
            bg=c["card"],
            fg=c["brand"],
            font=(FONT, FONT_TITLE, "bold"),
        )
        self.count_label.pack(side="right")

        self.root.update_idletasks()
        width = max(self.root.winfo_reqwidth(), 460)
        height = self.root.winfo_reqheight()
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        x = max((screen_w - width) // 2, 0)
        y = max((screen_h - height) // 2, 0)
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        self.root.minsize(width, height)
        self.root.maxsize(width, height)
        self.root.resizable(False, False)
        self.root.focus_set()

    def _time_row(self, parent, label, variable, top=0):
        row = tk.Frame(parent, bg=self.colors["card"])
        row.pack(fill="x", pady=(top, 0))
        self._field_label(row, label).pack(side="left")
        self._entry(row, variable, 12).pack(side="left", padx=(12, 8))
        tk.Label(
            row,
            text="HHMMSS",
            bg=self.colors["card"],
            fg=self.colors["placeholder"],
            font=(FONT, FONT_CAPTION),
        ).pack(side="left")

    def get_screen_center(self):
        """获取当前桌面屏幕中心坐标"""
        screen_w = user32.GetSystemMetrics(0)  # SM_CXSCREEN
        screen_h = user32.GetSystemMetrics(1)  # SM_CYSCREEN
        return screen_w // 2, screen_h // 2

    def setup_hotkey(self):
        """设置热键监听"""
        keyboard.on_press_key('s', lambda _: self.handle_s_key())

    def handle_s_key(self):
        """S 键只负责开始或停止，不再确认坐标。"""
        if self.is_selecting:
            return
        if self.is_clicking or self.is_waiting:
            self.stop_clicking()
        else:
            self.start_clicking()

    def select_coordinates(self):
        """进入选点：下一次鼠标左键按下的位置就是坐标。"""
        if self.is_clicking or self.is_waiting:
            messagebox.showwarning("警告", "请先停止点击再选择坐标！", parent=self.root)
            return

        if self.is_selecting:
            return

        self._picked_point = None
        self.is_selecting = True
        if not self._install_mouse_hook():
            self.is_selecting = False
            messagebox.showerror("错误", "无法监听鼠标，请重试。", parent=self.root)
            return

        self._apply_button_theme(self.select_btn, "warning")
        self.select_btn.configure(text="请单击目标…")
        self.status_label.config(text="请在目标位置单击鼠标左键", fg=self.colors["warn"])
        self._poll_pick()

    def _install_mouse_hook(self):
        self._remove_mouse_hook()
        self._pick_hwnd = self._window_hwnd()
        ready = threading.Event()
        self._hook_thread = threading.Thread(target=self._hook_loop, args=(ready,), daemon=True)
        self._hook_thread.start()
        if not ready.wait(1.0):
            self._remove_mouse_hook()
            return False
        return bool(self._mouse_hook)

    def _hook_loop(self, ready):
        """钩子必须挂在有消息循环的线程上，且不能直接碰 Tk。"""
        self._hook_thread_id = kernel32.GetCurrentThreadId()
        self._mouse_proc = LowLevelMouseProc(self._low_level_mouse)
        self._mouse_hook = user32_hook.SetWindowsHookExW(WH_MOUSE_LL, self._mouse_proc, None, 0)
        ready.set()
        if not self._mouse_hook:
            return
        msg = MSG()
        while user32_hook.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            user32_hook.TranslateMessage(ctypes.byref(msg))
            user32_hook.DispatchMessageW(ctypes.byref(msg))

    def _remove_mouse_hook(self):
        hook = self._mouse_hook
        self._mouse_hook = None
        if hook:
            user32_hook.UnhookWindowsHookEx(hook)
        thread_id = self._hook_thread_id
        thread = self._hook_thread
        if thread_id and thread is not None and thread is not threading.current_thread():
            user32_hook.PostThreadMessageW(thread_id, WM_QUIT, 0, 0)
            thread.join(timeout=1.0)
        self._hook_thread = None
        self._hook_thread_id = None

    def _window_hwnd(self):
        hwnd = self.root.winfo_id()
        parent = user32.GetParent(hwnd)
        return parent or hwnd

    def _is_window_chrome(self, x, y):
        """标题栏和边框上的点击要放行，否则选点时关不了窗口。"""
        hwnd = self._pick_hwnd or self._window_hwnd()
        window_rect = RECT()
        if not user32.GetWindowRect(hwnd, ctypes.byref(window_rect)):
            return False
        if not (window_rect.left <= x < window_rect.right and window_rect.top <= y < window_rect.bottom):
            return False
        pt = POINT(x, y)
        if not user32.ScreenToClient(hwnd, ctypes.byref(pt)):
            return False
        client_rect = RECT()
        if not user32.GetClientRect(hwnd, ctypes.byref(client_rect)):
            return False
        return not (0 <= pt.x < client_rect.right and 0 <= pt.y < client_rect.bottom)

    def _low_level_mouse(self, nCode, wParam, lParam):
        """选点期间吃掉第一次左键，只用它的坐标，不把它点到目标上。"""
        if nCode == HC_ACTION and self.is_selecting and wParam in (WM_LBUTTONDOWN, WM_LBUTTONUP):
            info = ctypes.cast(lParam, ctypes.POINTER(MSLLHOOKSTRUCT)).contents
            x, y = int(info.pt.x), int(info.pt.y)
            if wParam == WM_LBUTTONDOWN:
                if self._is_window_chrome(x, y):
                    self._ignore_click = True
                else:
                    self._ignore_click = False
                    self._picked_point = (x, y)
                    return 1
            elif self._ignore_click:
                self._ignore_click = False
            elif self._picked_point is not None:
                px, py = self._picked_point
                self._picked_point = None
                self.is_selecting = False
                self._pick_queue.put((px, py))
                return 1
            else:
                return 1
        return user32_hook.CallNextHookEx(self._mouse_hook, nCode, wParam, lParam)

    def _poll_pick(self):
        if not self._alive:
            return
        try:
            x, y = self._pick_queue.get_nowait()
        except queue.Empty:
            if self.is_selecting or self._mouse_hook:
                self.root.after(30, self._poll_pick)
            return
        self.is_selecting = False
        self._finish_pick(x, y)

    def _finish_pick(self, x, y):
        self._remove_mouse_hook()
        if not self._alive:
            return
        self.x_var.set(x)
        self.y_var.set(y)
        self._apply_button_theme(self.select_btn, "primary")
        self.select_btn.configure(text="选取坐标")
        self.status_label.config(text=f"已选中  {x}, {y}", fg=self.colors["info"])

    def clear_coordinates(self):
        """清空坐标"""
        if self.is_clicking or self.is_waiting:
            messagebox.showwarning("警告", "请先停止点击再清空坐标！", parent=self.root)
            return

        if self.is_selecting:
            self.is_selecting = False
            self._picked_point = None
            self._remove_mouse_hook()
            self._apply_button_theme(self.select_btn, "primary")
            self.select_btn.configure(text="选取坐标")

        self.x_var.set(0)
        self.y_var.set(0)
        self.status_label.config(text="坐标已清空", fg=self.colors["muted"])

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
                messagebox.showwarning("警告", "请先选择或输入点击坐标！", parent=self.root)
                return

            interval = self.interval_var.get()
            if interval <= 0:
                messagebox.showwarning("警告", "点击间隔必须大于0毫秒！", parent=self.root)
                return
        except Exception:
            messagebox.showwarning("警告", "请输入有效的坐标和间隔！", parent=self.root)
            return

        # 解析定时设置
        start_time_str = self.start_time_var.get()
        end_time_str = self.end_time_var.get()

        start_time = self.parse_time(start_time_str)
        end_time = self.parse_time(end_time_str)

        # 验证时间格式
        if start_time_str and not start_time:
            messagebox.showwarning("警告", "开始时间格式错误！请使用纯数字格式 HHMMSS 或 HHMM", parent=self.root)
            return

        if end_time_str and not end_time:
            messagebox.showwarning("警告", "结束时间格式错误！请使用纯数字格式 HHMMSS 或 HHMM", parent=self.root)
            return

        # 如果设置了开始时间，验证必须在当前时间之后
        if start_time:
            now = datetime.now()
            # 允许1秒的误差，避免在输入时正好到达该时间
            if start_time <= now + timedelta(seconds=1):
                messagebox.showwarning("警告", "开始时间必须在当前时间之后！", parent=self.root)
                return

        # 如果同时设置了开始和结束时间，确保结束时间在开始时间之后
        if start_time and end_time:
            if end_time <= start_time:
                messagebox.showwarning("警告", "结束时间必须在开始时间之后！", parent=self.root)
                return

        # 如果只设置了结束时间（没有开始时间），验证结束时间必须在当前时间之后
        if end_time and not start_time:
            now = datetime.now()
            if end_time <= now + timedelta(seconds=1):
                messagebox.showwarning("警告", "结束时间必须在当前时间之后！", parent=self.root)
                return

        if self.is_selecting:
            messagebox.showwarning("警告", "请先完成坐标选择。", parent=self.root)
            return

        self.click_count = 0
        self.last_update_time = time.time()
        self._set_enabled(self.start_btn, False)
        self._set_enabled(self.stop_btn, True)

        def update_count_display(count):
            """更新点击次数显示"""
            self.count_label.config(text=str(count))

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
                self.root.after(0, update_status, f"等待开始  {start_time.strftime('%H:%M:%S')}", self.colors["warn"])

                while self.is_waiting and datetime.now() < start_time:
                    remaining = (start_time - datetime.now()).total_seconds()
                    if remaining > 0:
                        mins, secs = divmod(int(remaining), 60)
                        hours, mins = divmod(mins, 60)
                        self.root.after(0, update_status, f"等待开始  剩余 {hours:02d}:{mins:02d}:{secs:02d}", self.colors["warn"])
                    time.sleep(0.5)

                if not self.is_waiting:
                    return

                self.is_waiting = False

            # 开始点击
            self.is_clicking = True
            self.root.after(0, update_status, "正在点击", self.colors["ok"])

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
        self._set_enabled(self.start_btn, True)
        self._set_enabled(self.stop_btn, False)
        self.status_label.config(text="已停止", fg=self.colors["danger"])

    def on_closing(self):
        """关闭程序时的处理"""
        self._alive = False
        self.is_selecting = False
        self._picked_point = None
        self._remove_mouse_hook()
        self.stop_clicking()
        self.is_waiting = False
        keyboard.unhook_all()
        self.root.destroy()


def main():
    enable_dpi_awareness()
    root = tk.Tk()
    app = AutoClicker(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()
