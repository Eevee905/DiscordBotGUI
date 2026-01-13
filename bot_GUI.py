# --- START OF FILE bot_open_GUI_v3.1_Fixed.py ---

import discord
from discord.ext import commands
import tkinter as tk
from tkinter import messagebox, font, filedialog, simpledialog
import ttkbootstrap as ttk
from ttkbootstrap.constants import *

import asyncio
import threading
import json
import os
import datetime
import pytz
from PIL import Image, ImageTk

# 全域變數
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)
app = None

with open("version.info", mode="r", encoding="ANSI") as ver:
    version = ver.read()

# --- 私訊視窗類別 (DMChatWindow) ---
# 此類別的功能在上次修改後是正常的，保持不變
class DMChatWindow(tk.Toplevel):
    def __init__(self, master, bot_instance, user, app_instance):
        super().__init__(master)
        self.bot = bot_instance
        self.user = user
        self.app = app_instance

        self.title(f"與 {user.name} 的私訊")
        self.geometry("600x700")
        self.minsize(400, 500)

        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        style = ttk.Style.get_instance()
        self.BG_COLOR = style.colors.bg
        self.FG_COLOR = style.colors.fg
        self.LIST_BG_COLOR = style.colors.dark
        
        self.configure(bg=self.BG_COLOR)
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        message_frame = ttk.Frame(self, padding=10)
        message_frame.grid(row=0, column=0, sticky="nsew")
        message_frame.grid_columnconfigure(0, weight=1)
        message_frame.grid_rowconfigure(0, weight=1)

        self.messages_text = tk.Text(message_frame, font=self.app.default_font, wrap=tk.WORD, 
                                   bg=self.LIST_BG_COLOR, fg=self.FG_COLOR, 
                                   state=tk.DISABLED, padx=10, pady=10, relief="flat", borderwidth=0)
        self.messages_text.grid(row=0, column=0, sticky="nsew")

        message_scrollbar = ttk.Scrollbar(message_frame, orient=tk.VERTICAL, command=self.messages_text.yview, bootstyle="round")
        message_scrollbar.grid(row=0, column=1, sticky="ns")
        self.messages_text.config(yscrollcommand=message_scrollbar.set)
        
        self.messages_text.tag_configure("author", font=self.app.messages_text.tag_cget("author", "font"), 
                                        foreground=style.colors.primary)
        self.messages_text.tag_configure("timestamp", font=self.app.messages_text.tag_cget("timestamp", "font"), 
                                        foreground=style.colors.secondary)
        self.messages_text.tag_configure("system", font=self.app.messages_text.tag_cget("system", "font"), 
                                        foreground=style.colors.warning)
        self.messages_text.tag_configure("bot_author", font=self.app.messages_text.tag_cget("author", "font"),
                                        foreground=style.colors.info)

        send_frame = ttk.Frame(self, padding=10)
        send_frame.grid(row=1, column=0, sticky="ew")
        send_frame.grid_columnconfigure(0, weight=1)

        self.send_message_entry = ttk.Entry(send_frame, font=self.app.default_font)
        self.send_message_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10), ipady=5)
        self.send_message_entry.bind("<Return>", self.send_message)

        ttk.Button(send_frame, text="發送", command=self.send_message, bootstyle="success").grid(row=0, column=1)
        
        self.load_history()

    def load_history(self):
        async def do_load():
            try:
                dm_channel = await self.user.create_dm()
                messages = [msg async for msg in dm_channel.history(limit=50)]
                self.master.after(0, lambda: self.update_messages_display(messages))
            except Exception as e:
                self.app.log_message(f"無法載入與 {self.user.name} 的歷史訊息: {e}", "ERROR")

        asyncio.run_coroutine_threadsafe(do_load(), self.bot.loop)

    def update_messages_display(self, messages):
        self.messages_text.config(state=tk.NORMAL)
        self.messages_text.delete(1.0, tk.END)
        for message in reversed(messages):
            self.append_message(message, scroll=False)
        self.messages_text.config(state=tk.DISABLED)
        self.messages_text.see(tk.END)

    def append_message(self, message, scroll=True):
        self.messages_text.config(state=tk.NORMAL)
        naive_utc_time = message.created_at
        aware_utc_time = pytz.utc.localize(naive_utc_time)
        local_time = aware_utc_time.astimezone(pytz.timezone("Asia/Taipei"))
        timestamp = local_time.strftime("%Y-%m-%d %H:%M:%S")

        self.messages_text.insert(tk.END, f"[{timestamp}] ", "timestamp")
        author_name = getattr(message.author, 'display_name', message.author.name)
        tag = "bot_author" if message.author.id == self.bot.user.id else "author"
        self.messages_text.insert(tk.END, f"{author_name}", tag)
        self.messages_text.insert(tk.END, f": {message.content}\n")
        
        if message.attachments:
            for attachment in message.attachments:
                self.messages_text.insert(tk.END, f"  📎 {attachment.filename}\n", "system")
        
        self.messages_text.config(state=tk.DISABLED)
        if scroll:
            self.messages_text.see(tk.END)

    def send_message(self, event=None):
        content = self.send_message_entry.get().strip()
        if not content:
            return

        async def do_send():
            try:
                await self.user.send(content)
                self.master.after(0, self.send_message_entry.delete, 0, tk.END)
            except discord.Forbidden:
                self.master.after(0, lambda: messagebox.showerror("錯誤", "無法發送訊息。", parent=self))
            except Exception as e:
                self.master.after(0, lambda: messagebox.showerror("錯誤", f"發送失敗: {e}", parent=self))
        
        asyncio.run_coroutine_threadsafe(do_send(), self.bot.loop)

    def on_closing(self):
        self.app.log_message(f"關閉與 {self.user.name} 的私訊視窗。")
        self.app.active_dm_windows.pop(self.user.id, None)
        self.destroy()

# --- 主應用程式類別 (ChannelViewer) ---
class ChannelViewer:
    def __init__(self, master):
        self.master = master
        self.master.title(f"Discord機器人專用 GUI 管理工具 v{version}")
        self.master.geometry("1400x950")
        self.master.minsize(1200, 800)

        self.config_file = "discord_gui_config.json"
        self.load_config()

        self.icon_cache = {}
        self.avatar_cache = {}
        self.downloading_avatar = set()
        self.placeholder_image = self.create_placeholder_image()
        self.last_messages = []
        self.current_selected_guild = None
        self.current_channel = None
        self.message_history = {}
        self.typing_users = set()
        self.active_dm_windows = {}
        
        self.load_all_icons()
        self.setup_ui()
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)

    # --- UI 設定與佈局 (Modernized) ---
    
    def setup_ui(self):
        try:
            self.default_font = font.Font(family="Microsoft JhengHei UI", size=10)
            self.title_font = font.Font(family="Microsoft JhengHei UI", size=12, weight="bold")
        except tk.TclError:
            self.default_font = font.Font(family="Arial", size=10)
            self.title_font = font.Font(family="Arial", size=12, weight="bold")
            
        style = ttk.Style.get_instance()
        style.configure('Treeview', rowheight=30, font=self.default_font)
        style.configure('Title.TLabel', font=self.title_font)
        style.configure('TNotebook.Tab', font=self.default_font)
        
        self.create_menu_bar()
        self.create_main_frames()
        self.create_top_controls()
        self.create_notebook()
        self.create_status_bar()

    def create_main_frames(self):
        self.master.grid_columnconfigure(0, weight=1)
        self.master.grid_rowconfigure(1, weight=1)

        self.top_frame = ttk.Frame(self.master)
        self.top_frame.grid(row=0, column=0, sticky="ew")

        self.main_frame = ttk.Frame(self.master)
        self.main_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=1)

        self.status_frame = ttk.Frame(self.master, bootstyle="secondary")
        self.status_frame.grid(row=2, column=0, sticky="ew")

    def create_top_controls(self):
        self.top_frame.config(padding=(10, 5), bootstyle="secondary")
        self.top_frame.grid_columnconfigure(1, weight=1)

        self.connection_frame = ttk.Frame(self.top_frame, bootstyle="secondary")
        self.connection_frame.grid(row=0, column=0, padx=(0, 10), sticky="w")
        
        self.status_indicator = ttk.Label(self.connection_frame, text="●", font=("Arial", 16), bootstyle="danger")
        self.status_indicator.pack(side=tk.LEFT)
        
        self.status_label = ttk.Label(self.connection_frame, text="未連接", font=self.default_font, bootstyle="secondary")
        self.status_label.pack(side=tk.LEFT, padx=(5, 0))

        self.quick_actions_frame = ttk.Frame(self.top_frame, bootstyle="secondary")
        self.quick_actions_frame.grid(row=0, column=2, sticky="e")

        ttk.Button(self.quick_actions_frame, text=" 刷新", image=self.icons["refresh"], compound=tk.LEFT, command=self.refresh_all, bootstyle="outline-primary").pack(side=tk.LEFT, padx=(0,5))
        ttk.Button(self.quick_actions_frame, text=" 設置", image=self.icons["settings"], compound=tk.LEFT, command=self.open_preferences, bootstyle="outline-primary").pack(side=tk.LEFT, padx=(0,5))
        ttk.Button(self.quick_actions_frame, text=" 重連", image=self.icons["reconnect"], compound=tk.LEFT, command=self.reconnect_bot, bootstyle="outline-danger").pack(side=tk.LEFT)

    def create_notebook(self):
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.grid(row=0, column=0, sticky="nsew")

        self.main_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.main_tab, text=" 頻道瀏覽")
        self.setup_main_tab()

        self.batch_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.batch_tab, text=" 批量操作")
        self.setup_batch_tab()

        self.stats_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.stats_tab, text=" 服務器統計")
        self.setup_stats_tab()

        self.logs_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.logs_tab, text=" 操作日誌")
        self.setup_logs_tab()

    def setup_main_tab(self):
        self.main_tab.grid_columnconfigure(0, weight=1)
        self.main_tab.grid_columnconfigure(1, weight=3)
        self.main_tab.grid_rowconfigure(0, weight=1)
        
        self.left_panel = ttk.Frame(self.main_tab, padding=5)
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        self.setup_left_panel()

        self.right_panel = ttk.Frame(self.main_tab, padding=5)
        self.right_panel.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        self.setup_right_panel()

    def setup_left_panel(self):
        self.left_panel.grid_columnconfigure(0, weight=1)
        self.left_panel.grid_rowconfigure(1, weight=2)
        self.left_panel.grid_rowconfigure(4, weight=3)

        ttk.Label(self.left_panel, text="伺服器列表", style='Title.TLabel').grid(row=0, column=0, sticky="w", pady=(0, 5))
        guild_frame = ttk.Frame(self.left_panel)
        guild_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 10))
        guild_frame.grid_columnconfigure(0, weight=1)
        guild_frame.grid_rowconfigure(0, weight=1)

        self.guild_listbox = tk.Listbox(guild_frame, font=self.default_font, relief="flat",
                                       bg=ttk.Style.get_instance().colors.dark,
                                       fg=ttk.Style.get_instance().colors.fg,
                                       selectbackground=ttk.Style.get_instance().colors.primary,
                                       selectforeground=ttk.Style.get_instance().colors.light,
                                       highlightthickness=0, borderwidth=1)
        self.guild_listbox.grid(row=0, column=0, sticky="nsew")
        self.guild_listbox.bind("<<ListboxSelect>>", self.on_guild_select)
        guild_scrollbar = ttk.Scrollbar(guild_frame, orient=tk.VERTICAL, command=self.guild_listbox.yview, bootstyle="round")
        guild_scrollbar.grid(row=0, column=1, sticky="ns")
        self.guild_listbox.config(yscrollcommand=guild_scrollbar.set)

        search_frame = ttk.Frame(self.left_panel)
        search_frame.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        search_frame.grid_columnconfigure(1, weight=1)
        ttk.Label(search_frame, text="搜索:").grid(row=0, column=0, padx=(0, 5))
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self.filter_channels)
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        self.search_entry.grid(row=0, column=1, sticky="ew")

        ttk.Label(self.left_panel, text="頻道列表", style='Title.TLabel').grid(row=3, column=0, sticky="w", pady=(0, 5))
        channel_frame = ttk.Frame(self.left_panel)
        channel_frame.grid(row=4, column=0, sticky="nsew")
        channel_frame.grid_columnconfigure(0, weight=1)
        channel_frame.grid_rowconfigure(0, weight=1)
        self.channel_tree = ttk.Treeview(channel_frame, show="tree headings", bootstyle="primary")
        self.channel_tree.grid(row=0, column=0, sticky="nsew")
        self.channel_tree.heading("#0", text="頻道", anchor="w")
        self.channel_tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        self.channel_tree.bind("<Double-1>", self.on_channel_double_click)
        channel_scrollbar = ttk.Scrollbar(channel_frame, orient="vertical", command=self.channel_tree.yview, bootstyle="round")
        channel_scrollbar.grid(row=0, column=1, sticky="ns")
        self.channel_tree.configure(yscrollcommand=channel_scrollbar.set)
        self.channel_id_mapping = {}

    def setup_right_panel(self):
        self.right_panel.grid_columnconfigure(0, weight=1)
        self.right_panel.grid_rowconfigure(1, weight=1) 

        top_utility_frame = ttk.Frame(self.right_panel, padding=(0, 0, 0, 10))
        top_utility_frame.grid(row=0, column=0, sticky="ew")
        top_utility_frame.grid_columnconfigure(0, weight=1)

        info_frame = ttk.Frame(top_utility_frame)
        info_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        info_frame.grid_columnconfigure(1, weight=1)
        ttk.Label(info_frame, text="伺服器:", font=self.default_font, width=8).grid(row=0, column=0, sticky="w")
        self.guild_name_label = ttk.Label(info_frame, text="未選擇", bootstyle="info", font=self.default_font)
        self.guild_name_label.grid(row=0, column=1, sticky="w", padx=5)
        ttk.Label(info_frame, text="頻道:", font=self.default_font, width=8).grid(row=1, column=0, sticky="w")
        self.channel_name_label = ttk.Label(info_frame, text="未選擇", bootstyle="info", font=self.default_font)
        self.channel_name_label.grid(row=1, column=1, sticky="w", padx=5)
        
        ttk.Separator(top_utility_frame, orient=HORIZONTAL).grid(row=1, column=0, sticky="ew", pady=10)

        control_frame = ttk.Frame(top_utility_frame)
        control_frame.grid(row=2, column=0, sticky="ew")
        self.setup_control_frame(control_frame)

        self.details_notebook = ttk.Notebook(self.right_panel, bootstyle="primary")
        self.details_notebook.grid(row=1, column=0, sticky="nsew")
        self.message_tab = ttk.Frame(self.details_notebook)
        self.details_notebook.add(self.message_tab, text=" 訊息")
        self.member_tab = ttk.Frame(self.details_notebook)
        self.details_notebook.add(self.member_tab, text=" 成員列表")
        self.message_tab.grid_columnconfigure(0, weight=1)
        self.message_tab.grid_rowconfigure(0, weight=1)
        message_frame = ttk.Frame(self.message_tab)
        message_frame.grid(row=0, column=0, sticky="nsew")
        self.setup_message_frame(message_frame)
        send_frame = ttk.Frame(self.message_tab, padding=(10, 5))
        send_frame.grid(row=1, column=0, sticky="ew")
        self.setup_send_frame(send_frame)
        self.setup_member_tab()

    def setup_control_frame(self, parent):
        parent.grid_columnconfigure(1, weight=1)

        # 頻道ID
        ttk.Label(parent, text="頻道ID:").grid(row=0, column=0, padx=(0, 5), sticky="w")
        self.channel_id_entry = ttk.Entry(parent, width=22)
        self.channel_id_entry.grid(row=0, column=1, padx=5, sticky="ew")
        self.channel_id_entry.bind("<Return>", lambda e: self.view_channel())
        ttk.Button(parent, text="查看", command=self.view_channel, image=self.icons["view"], compound=tk.LEFT, bootstyle="outline-info").grid(row=0, column=2)

        # 消息數量與自動更新
        msg_limit_frame = ttk.Frame(parent)
        msg_limit_frame.grid(row=0, column=3, sticky="e", padx=(20,0))
        ttk.Label(msg_limit_frame, text="數量:").pack(side=tk.LEFT, padx=(0,5))
        self.message_limit_var = tk.StringVar(value=str(self.config.get("message_limit", 50)))
        message_limit_spinbox = ttk.Spinbox(msg_limit_frame, from_=10, to=200, textvariable=self.message_limit_var, width=5)
        message_limit_spinbox.pack(side=tk.LEFT)
        self.auto_update_var = tk.BooleanVar(value=self.config.get("auto_update", False))
        auto_update_check = ttk.Checkbutton(msg_limit_frame, text="自動更新", variable=self.auto_update_var, command=self.toggle_auto_update, bootstyle="round-toggle")
        auto_update_check.pack(side=tk.LEFT, padx=(10,0))
        
        ttk.Separator(parent, orient=HORIZONTAL).grid(row=1, column=0, columnspan=4, sticky="ew", pady=10)
        
        # --- <<< RESTORED FUNCTIONALITY >>> ---
        # 邀請連結區塊
        invite_frame = ttk.Frame(parent)
        invite_frame.grid(row=2, column=0, columnspan=4, sticky="ew")
        invite_frame.grid_columnconfigure(3, weight=1)

        # 邀請參數設定
        self.create_invite_button = ttk.Button(invite_frame, text=" 創建邀請", command=self.create_invite_link, state=tk.DISABLED, image=self.icons["invite"], compound=tk.LEFT)
        self.create_invite_button.grid(row=0, column=0, padx=(0, 10))

        ttk.Label(invite_frame, text="有效期:").grid(row=0, column=1, sticky="w")
        self.invite_max_age_var = tk.StringVar()
        age_options = ["30 分鐘", "1 小時", "6 小時", "12 小時", "1 天", "7 天", "永久"]
        self.invite_max_age_combo = ttk.Combobox(invite_frame, textvariable=self.invite_max_age_var, values=age_options, state="readonly", width=8)
        self.invite_max_age_combo.grid(row=0, column=2, padx=5, sticky="w")
        self.invite_max_age_combo.set("7 天")
        
        ttk.Label(invite_frame, text="次數:").grid(row=0, column=3, sticky="e")
        self.invite_max_uses_var = tk.StringVar(value="0")
        ttk.Entry(invite_frame, textvariable=self.invite_max_uses_var, width=5).grid(row=0, column=4, padx=(5,10))

        # 邀請連結顯示與複製
        self.invite_url_var = tk.StringVar()
        self.invite_url_entry = ttk.Entry(invite_frame, textvariable=self.invite_url_var, state="readonly")
        self.invite_url_entry.grid(row=1, column=0, columnspan=4, sticky="ew", pady=(5, 0), ipady=2)
        self.copy_invite_button = ttk.Button(invite_frame, text="複製", command=self.copy_invite_to_clipboard, state=tk.DISABLED, image=self.icons["copy"], compound=tk.LEFT, bootstyle="outline-secondary")
        self.copy_invite_button.grid(row=1, column=4, padx=(10, 0), pady=(5, 0))

    def setup_message_frame(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=1)
        self.messages_text = tk.Text(parent, font=self.default_font, wrap=tk.WORD, 
                                   bg=ttk.Style.get_instance().colors.dark, 
                                   fg=ttk.Style.get_instance().colors.fg, 
                                   state=tk.DISABLED, padx=10, pady=10, relief="flat", borderwidth=0)
        self.messages_text.grid(row=0, column=0, sticky="nsew")
        message_scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=self.messages_text.yview, bootstyle="round")
        message_scrollbar.grid(row=0, column=1, sticky="ns")
        self.messages_text.config(yscrollcommand=message_scrollbar.set)
        style = ttk.Style.get_instance()
        self.messages_text.tag_configure("author", font=(self.default_font.cget("family"), self.default_font.cget("size"), "bold"), foreground=style.colors.primary)
        self.messages_text.tag_configure("timestamp", foreground=style.colors.secondary, font=(self.default_font.cget("family"), self.default_font.cget("size")-1))
        self.messages_text.tag_configure("system", foreground=style.colors.warning, font=(self.default_font.cget("family"), self.default_font.cget("size"), "italic"))

    def setup_send_frame(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        self.send_message_entry = ttk.Entry(parent, font=self.default_font)
        self.send_message_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10), ipady=5)
        self.send_message_entry.bind("<Return>", lambda e: self.send_message())
        self.send_message_entry.bind("<Control-Return>", lambda e: self.send_message_with_file())
        button_frame = ttk.Frame(parent)
        button_frame.grid(row=0, column=1)
        ttk.Button(button_frame, image=self.icons["file"], command=self.send_message_with_file, bootstyle="outline-secondary").pack(side=tk.LEFT)
        ttk.Button(button_frame, text=" 發送", image=self.icons["send"], compound=tk.LEFT, command=self.send_message, bootstyle="success").pack(side=tk.LEFT, padx=(5, 0))
    
    def setup_member_tab(self):
        self.member_tab.grid_columnconfigure(0, weight=1)
        self.member_tab.grid_rowconfigure(0, weight=1)
        member_frame = ttk.Frame(self.member_tab, padding=5)
        member_frame.grid(row=0, column=0, sticky="nsew")
        member_frame.grid_columnconfigure(0, weight=1)
        member_frame.grid_rowconfigure(0, weight=1)
        columns = ("name", "id", "status")
        self.member_tree = ttk.Treeview(member_frame, columns=columns, show="headings", bootstyle="primary")
        self.member_tree.grid(row=0, column=0, sticky="nsew")
        self.member_tree.heading("name", text="成員名稱")
        self.member_tree.heading("id", text="用戶ID")
        self.member_tree.heading("status", text="狀態")
        self.member_tree.column("name", width=200)
        self.member_tree.column("id", width=180)
        self.member_tree.column("status", width=100, anchor="center")
        member_scrollbar = ttk.Scrollbar(member_frame, orient=tk.VERTICAL, command=self.member_tree.yview, bootstyle="round")
        member_scrollbar.grid(row=0, column=1, sticky="ns")
        self.member_tree.config(yscrollcommand=member_scrollbar.set)
        self.member_context_menu = tk.Menu(self.master, tearoff=0)
        self.member_context_menu.add_command(label="查看成員資訊", command=self.show_selected_member_info)
        self.member_context_menu.add_command(label="開啟聊天室", command=self.open_dm_chat_window)
        self.member_tree.bind("<<TreeviewSelect>>", self.on_member_select)
        self.member_tree.bind("<Double-1>", self.on_member_double_click)
        self.member_tree.bind("<Button-3>", self.show_member_context_menu)
        action_frame = ttk.Frame(self.member_tab, padding=(5, 10))
        action_frame.grid(row=1, column=0, sticky="ew")
        self.dm_button = ttk.Button(action_frame, text=" 開啟聊天", image=self.icons["dm"], compound=tk.LEFT, command=self.open_dm_chat_window, state=tk.DISABLED, bootstyle="info")
        self.dm_button.pack(side=tk.LEFT)
        self.info_button = ttk.Button(action_frame, text=" 查看資訊", image=self.icons["info"], compound=tk.LEFT, command=self.show_selected_member_info, state=tk.DISABLED, bootstyle="outline-secondary")
        self.info_button.pack(side=tk.LEFT, padx=5)

    # --- 其他頁籤 (Batch, Stats, Logs) ---
    # 這部分功能相對獨立，保持原樣，但美化了部分元件
    def setup_batch_tab(self):
        self.batch_tab.grid_columnconfigure(0, weight=1)
        self.batch_tab.grid_rowconfigure(1, weight=1)
        
        control_frame = ttk.LabelFrame(self.batch_tab, text="批量操作控制", padding=10, bootstyle="primary")
        control_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        ttk.Label(control_frame, text="操作類型:").grid(row=0, column=0, sticky="w")
        self.batch_operation_var = tk.StringVar()
        operations = ["批量發送消息", "批量創建邀請", "批量修改頻道權限", "批量清理消息"]
        ttk.Combobox(control_frame, textvariable=self.batch_operation_var, values=operations, state="readonly").grid(row=0, column=1, padx=(5, 0), sticky="w")
        ttk.Button(control_frame, text="執行", command=self.execute_batch_operation, bootstyle="danger").grid(row=0, column=2, padx=(10, 0))
        
        result_frame = ttk.LabelFrame(self.batch_tab, text="操作結果", padding=10, bootstyle="primary")
        result_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        result_frame.grid_columnconfigure(0, weight=1)
        result_frame.grid_rowconfigure(0, weight=1)
        self.batch_result_text = tk.Text(result_frame, font=self.default_font, bg=ttk.Style.get_instance().colors.dark, fg=ttk.Style.get_instance().colors.fg, state=tk.DISABLED, relief="flat", borderwidth=0)
        self.batch_result_text.grid(row=0, column=0, sticky="nsew")
        batch_scrollbar = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=self.batch_result_text.yview, bootstyle="round")
        batch_scrollbar.grid(row=0, column=1, sticky="ns")
        self.batch_result_text.config(yscrollcommand=batch_scrollbar.set)

    def setup_stats_tab(self):
        self.stats_tab.grid_columnconfigure(0, weight=1)
        self.stats_tab.grid_columnconfigure(1, weight=1)
        self.stats_tab.grid_rowconfigure(1, weight=1)
        
        stats_control_frame = ttk.Frame(self.stats_tab, padding=10)
        stats_control_frame.grid(row=0, column=0, columnspan=2, sticky="ew")
        ttk.Button(stats_control_frame, text="刷新統計", command=self.refresh_stats, bootstyle="info").pack(side=tk.LEFT)
        ttk.Button(stats_control_frame, text="導出報告", command=self.export_stats, bootstyle="outline-secondary").pack(side=tk.LEFT, padx=(10, 0))
        
        server_stats_frame = ttk.LabelFrame(self.stats_tab, text="服務器統計", padding=10, bootstyle="primary")
        server_stats_frame.grid(row=1, column=0, sticky="nsew", padx=(10, 5), pady=(0, 10))
        self.server_stats_text = tk.Text(server_stats_frame, font=self.default_font, bg=ttk.Style.get_instance().colors.dark, fg=ttk.Style.get_instance().colors.fg, state=tk.DISABLED, height=15, relief="flat", borderwidth=0)
        self.server_stats_text.pack(fill=tk.BOTH, expand=True)
        
        user_stats_frame = ttk.LabelFrame(self.stats_tab, text="用戶統計", padding=10, bootstyle="primary")
        user_stats_frame.grid(row=1, column=1, sticky="nsew", padx=(5, 10), pady=(0, 10))
        self.user_stats_text = tk.Text(user_stats_frame, font=self.default_font, bg=ttk.Style.get_instance().colors.dark, fg=ttk.Style.get_instance().colors.fg, state=tk.DISABLED, height=15, relief="flat", borderwidth=0)
        self.user_stats_text.pack(fill=tk.BOTH, expand=True)

    def setup_logs_tab(self):
        self.logs_tab.grid_columnconfigure(0, weight=1)
        self.logs_tab.grid_rowconfigure(1, weight=1)
        
        log_control_frame = ttk.Frame(self.logs_tab, padding=10)
        log_control_frame.grid(row=0, column=0, sticky="ew")
        ttk.Button(log_control_frame, text="清空日誌", command=self.clear_logs, bootstyle="warning").pack(side=tk.LEFT)
        ttk.Button(log_control_frame, text="保存日誌", command=self.save_logs, bootstyle="outline-secondary").pack(side=tk.LEFT, padx=(10, 0))
        self.log_level_var = tk.StringVar(value="INFO")
        ttk.Label(log_control_frame, text="日誌級別:").pack(side=tk.LEFT, padx=(20, 5))
        ttk.Combobox(log_control_frame, textvariable=self.log_level_var, values=["DEBUG", "INFO", "WARNING", "ERROR"], state="readonly", width=10).pack(side=tk.LEFT)
        
        log_frame = ttk.LabelFrame(self.logs_tab, text="操作日誌", padding=10, bootstyle="primary")
        log_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        log_frame.grid_columnconfigure(0, weight=1)
        log_frame.grid_rowconfigure(0, weight=1)
        self.logs_text = tk.Text(log_frame, font=self.default_font, bg=ttk.Style.get_instance().colors.dark, fg=ttk.Style.get_instance().colors.fg, state=tk.DISABLED, relief="flat", borderwidth=0)
        self.logs_text.grid(row=0, column=0, sticky="nsew")
        log_scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.logs_text.yview, bootstyle="round")
        log_scrollbar.grid(row=0, column=1, sticky="ns")
        self.logs_text.config(yscrollcommand=log_scrollbar.set)

    def create_status_bar(self):
        self.status_frame.grid_columnconfigure(1, weight=1)
        self.status_text = tk.StringVar(value="就緒")
        ttk.Label(self.status_frame, textvariable=self.status_text, bootstyle="inverse-secondary").grid(row=0, column=0, padx=10, sticky="w")
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self.status_frame, variable=self.progress_var, mode='determinate')
        self.progress_bar.grid(row=0, column=1, sticky="ew", padx=(0, 5))
        self.time_label = ttk.Label(self.status_frame, text="", bootstyle="inverse-secondary")
        self.time_label.grid(row=0, column=2, padx=10, sticky="e")
        self.update_time()

    # --- 輔助與核心功能 ---
    # 從這裡開始是所有功能的實作，已恢復為易讀格式

    def load_config(self):
        default_config = {
            "bot_token": "", "theme": "superhero", "auto_update": False, 
            "update_interval": 5, "message_limit": 50, "save_logs": False, 
            "logs_directory": "./logs", "font_size": 10, "window_geometry": "1400x950"
        }
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config = {**default_config, **json.load(f)}
            else:
                self.config = default_config
        except Exception as e:
            print(f"載入配置失敗: {e}")
            self.config = default_config

    def save_config(self):
        try:
            self.config["window_geometry"] = self.master.geometry()
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存配置失敗: {e}")

    def create_placeholder_image(self):
        placeholder = Image.new('RGB', (24, 24), color='lightgray')
        return ImageTk.PhotoImage(placeholder)

    def load_all_icons(self):
        self.icons = {name: self.load_icon(f"{name}.png") for name in [
            "refresh-cw", "settings", "log-in", "send", "paperclip", 
            "copy", "plus-square", "eye", "message-square", "info"
        ]}
        # 別名
        self.icons["refresh"] = self.icons["refresh-cw"]
        self.icons["reconnect"] = self.icons["log-in"]
        self.icons["file"] = self.icons["paperclip"]
        self.icons["invite"] = self.icons["plus-square"]
        self.icons["view"] = self.icons["eye"]
        self.icons["dm"] = self.icons["message-square"]

    def load_icon(self, filename, size=(16, 16)):
        path = os.path.join("icons", filename)
        if path in self.icon_cache:
            return self.icon_cache[path]
        try:
            image = Image.open(path).resize(size, Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(image)
            self.icon_cache[path] = photo
            return photo
        except Exception as e:
            print(f"無法載入圖示 {path}: {e}")
            return ImageTk.PhotoImage(Image.new('RGBA', size, (0, 0, 0, 0)))

    def create_menu_bar(self):
        menubar = tk.Menu(self.master)
        self.master.config(menu=menubar)
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="導出消息歷史", command=self.export_messages)
        file_menu.add_command(label="導入設置", command=self.import_settings)
        file_menu.add_command(label="導出設置", command=self.export_settings)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.on_closing)
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="工具", menu=tools_menu)
        tools_menu.add_command(label="批量管理頻道", command=self.open_batch_manager)
        tools_menu.add_command(label="用戶信息查詢", command=self.open_user_info)
        tools_menu.add_command(label="服務器統計", command=self.open_server_stats)
        tools_menu.add_command(label="清理緩存", command=self.clear_cache)
        settings_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="設置", menu=settings_menu)
        settings_menu.add_command(label="首選項", command=self.open_preferences)
        settings_menu.add_command(label="切換主題 (需重啟)", command=self.toggle_theme)
        settings_menu.add_command(label="字體設置 (需重啟)", command=self.font_settings)
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="幫助", menu=help_menu)
        help_menu.add_command(label="使用說明", command=self.show_help)
        help_menu.add_command(label="快捷鍵", command=self.show_shortcuts)
        help_menu.add_command(label="關於", command=self.show_about)

    def on_guild_select(self, event):
        if not hasattr(self, 'guild_listbox') or not self.guild_listbox.curselection():
            return
        index = self.guild_listbox.curselection()[0]
        guild_name = self.guild_listbox.get(index)
        guild = discord.utils.get(bot.guilds, name=guild_name)
        if guild:
            self.current_selected_guild = guild
            self.guild_name_label.config(text=guild.name)
            self.create_invite_button.config(state=tk.NORMAL)
            self.show_channels_for_guild(guild)
            self.show_members_for_guild(guild)
            self.log_message(f"選擇服務器: {guild.name}")
    
    def on_tree_select(self, event):
        if not self.channel_tree.selection(): return
        item_id = self.channel_tree.selection()[0]
        if item_id in self.channel_id_mapping:
            channel_id = self.channel_id_mapping[item_id]
            self.channel_id_entry.delete(0, tk.END)
            self.channel_id_entry.insert(0, str(channel_id))
            channel = bot.get_channel(channel_id)
            if channel:
                self.current_channel = channel
                self.channel_name_label.config(text=channel.name)
                self.view_channel()
    
    def on_channel_double_click(self, event):
        self.view_channel()

    def on_member_select(self, event):
        state = tk.NORMAL if self.member_tree.selection() else tk.DISABLED
        self.dm_button.config(state=state)
        self.info_button.config(state=state)

    def on_member_double_click(self, event):
        if self.member_tree.identify_row(event.y):
            self.open_dm_chat_window()
            
    def show_member_context_menu(self, event):
        item_id = self.member_tree.identify_row(event.y)
        if item_id:
            self.member_tree.selection_set(item_id)
            self.member_context_menu.post(event.x_root, event.y_root)

    def show_members_for_guild(self, guild):
        for item in self.member_tree.get_children():
            self.member_tree.delete(item)
        status_map = {
            discord.Status.online: "線上", discord.Status.idle: "閒置",
            discord.Status.dnd: "請勿打擾", discord.Status.offline: "離線",
            discord.Status.invisible: "離線"
        }
        sorted_members = sorted(guild.members, key=lambda m: (m.bot, m.status == discord.Status.offline))
        for member in sorted_members:
            display_name = member.display_name + (" [BOT]" if member.bot else "")
            self.member_tree.insert("", tk.END, values=(display_name, member.id, status_map.get(member.status, "未知")))

    def show_channels_for_guild(self, guild):
        for item in self.channel_tree.get_children():
            self.channel_tree.delete(item)
        self.channel_id_mapping.clear()
        categories = {}
        uncategorized = []
        for channel in guild.text_channels:
            if channel.category:
                cat_name = channel.category.name
                if cat_name not in categories:
                    categories[cat_name] = []
                categories[cat_name].append(channel)
            else:
                uncategorized.append(channel)
        for cat_name, channels in sorted(categories.items()):
            parent_id = self.channel_tree.insert("", tk.END, text=f"📁 {cat_name}", open=True)
            for channel in sorted(channels, key=lambda c: c.position):
                item_id = self.channel_tree.insert(parent_id, tk.END, text=f" # {channel.name}")
                self.channel_id_mapping[item_id] = channel.id
        if uncategorized:
            parent_id = self.channel_tree.insert("", tk.END, text="📁 未分類", open=True)
            for channel in sorted(uncategorized, key=lambda c: c.position):
                item_id = self.channel_tree.insert(parent_id, tk.END, text=f" # {channel.name}")
                self.channel_id_mapping[item_id] = channel.id

    async def fetch_messages(self, channel_id):
        try:
            channel = bot.get_channel(channel_id)
            if not channel:
                messagebox.showerror("錯誤", "無法找到該頻道")
                return
            self.status_text.set("正在載入消息...")
            messages = [msg async for msg in channel.history(limit=int(self.message_limit_var.get()))]
            self.last_messages = messages
            self.message_history[channel_id] = messages
            self.update_messages_display(messages)
            self.status_text.set(f"已載入 {len(messages)} 條消息")
        except discord.Forbidden:
            messagebox.showerror("錯誤", "沒有權限訪問該頻道")
        except Exception as e:
            messagebox.showerror("錯誤", f"獲取消息失敗: {e}")
            self.log_message(f"ERROR: 獲取消息失敗: {e}", "ERROR")

    def update_messages_display(self, messages):
        self.messages_text.config(state=tk.NORMAL)
        self.messages_text.delete(1.0, tk.END)
        for message in reversed(messages):
            self.append_message_to_display(message, scroll=False)
        self.messages_text.config(state=tk.DISABLED)
        self.messages_text.see(tk.END)

    def append_message_to_display(self, message, scroll=True):
        self.messages_text.config(state=tk.NORMAL)
        local_time = message.created_at.astimezone(pytz.timezone("Asia/Taipei"))
        timestamp = local_time.strftime("%Y-%m-%d %H:%M:%S")
        self.messages_text.insert(tk.END, f"[{timestamp}] ", "timestamp")
        author_name = getattr(message.author, 'display_name', message.author.name)
        self.messages_text.insert(tk.END, f"{author_name}", "author")
        self.messages_text.insert(tk.END, f": {message.content}\n")
        if message.attachments:
            for attachment in message.attachments:
                self.messages_text.insert(tk.END, f"  📎 {attachment.filename}\n", "system")
        if message.embeds:
            self.messages_text.insert(tk.END, f"  📋 嵌入內容 ({len(message.embeds)})\n", "system")
        self.messages_text.config(state=tk.DISABLED)
        if scroll:
            self.messages_text.see(tk.END)

    def view_channel(self):
        channel_id_str = self.channel_id_entry.get().strip()
        if not channel_id_str.isdigit():
            messagebox.showerror("錯誤", "請輸入有效的頻道ID")
            return
        asyncio.run_coroutine_threadsafe(self.fetch_messages(int(channel_id_str)), bot.loop)

    def send_message(self):
        if not self.current_channel:
            messagebox.showwarning("警告", "請先選擇一個頻道")
            return
        content = self.send_message_entry.get().strip()
        if not content:
            return
        async def do_send():
            try:
                await self.current_channel.send(content)
                self.send_message_entry.delete(0, tk.END)
                self.log_message(f"發送消息到 {self.current_channel.name}: {content}")
            except Exception as e:
                messagebox.showerror("錯誤", f"發送消息失敗: {e}")
        asyncio.run_coroutine_threadsafe(do_send(), bot.loop)

    def send_message_with_file(self):
        if not self.current_channel:
            messagebox.showwarning("警告", "請先選擇一個頻道")
            return
        file_path = filedialog.askopenfilename(title="選擇要發送的文件")
        if not file_path:
            return
        content = self.send_message_entry.get().strip()
        async def do_send_file():
            try:
                with open(file_path, 'rb') as f:
                    d_file = discord.File(f, filename=os.path.basename(file_path))
                    await self.current_channel.send(content=content or None, file=d_file)
                self.send_message_entry.delete(0, tk.END)
                self.log_message(f"發送文件到 {self.current_channel.name}")
            except Exception as e:
                messagebox.showerror("錯誤", f"發送文件失敗: {e}")
        asyncio.run_coroutine_threadsafe(do_send_file(), bot.loop)
    
    def open_dm_chat_window(self):
        if not self.member_tree.selection(): return
        item = self.member_tree.item(self.member_tree.selection()[0])
        member_id = int(item['values'][1])

        if member_id in self.active_dm_windows:
            dm_window = self.active_dm_windows[member_id]
            if dm_window.winfo_exists():
                dm_window.lift()
                return
            else:
                self.active_dm_windows.pop(member_id, None)

        async def get_user_and_open_window(uid):
            try:
                user = await bot.fetch_user(uid)
                if user.bot:
                    messagebox.showwarning("警告", "無法與機器人進行私訊。")
                    return
                self.master.after(0, lambda: self._create_dm_window(user))
            except Exception as e:
                messagebox.showerror("錯誤", f"無法開啟聊天室: {e}")
        
        asyncio.run_coroutine_threadsafe(get_user_and_open_window(member_id), bot.loop)

    def _create_dm_window(self, user):
        dm_window = DMChatWindow(self.master, bot, user, self)
        self.active_dm_windows[user.id] = dm_window
        self.log_message(f"開啟與 {user.name} 的私訊視窗。")

    def show_selected_member_info(self):
        if not self.member_tree.selection(): return
        item = self.member_tree.item(self.member_tree.selection()[0])
        member_id = int(item['values'][1])
        if not self.current_selected_guild: return
        member = self.current_selected_guild.get_member(member_id)
        if not member:
            messagebox.showerror("錯誤", "無法找到該成員。")
            return
        
        taipei_tz = pytz.timezone("Asia/Taipei")
        created_at_local = member.created_at.astimezone(taipei_tz).strftime('%Y-%m-%d %H:%M:%S')
        joined_at_local = member.joined_at.astimezone(taipei_tz).strftime('%Y-%m-%d %H:%M:%S')
        status_map = {
            discord.Status.online: "線上", discord.Status.idle: "閒置",
            discord.Status.dnd: "請勿打擾", discord.Status.offline: "離線",
            discord.Status.invisible: "離線"
        }
        
        info_text = (
            f"用戶名: {member.name}#{member.discriminator}\n"
            f"伺服器暱稱: {member.nick or '無'}\n"
            f"用戶 ID: {member.id}\n"
            f"狀態: {status_map.get(member.status, '未知')}\n"
            f"帳號創建時間: {created_at_local}\n"
            f"加入伺服器時間: {joined_at_local}\n"
            f"是否為機器人: {'是' if member.bot else '否'}\n"
            f"最高身分組: {member.top_role.name if member.top_role else '無'}"
        )
        messagebox.showinfo(f"{member.display_name} 的資訊", info_text, parent=self.master)

    def filter_channels(self, *args):
        search_term = self.search_var.get().lower()
        if not self.current_selected_guild: return
        
        # Detach all items first to avoid visual glitches
        all_items = list(self.channel_tree.get_children(''))
        for item in all_items:
            self.channel_tree.detach(item)

        # Re-attach items that match
        for item in all_items:
            # If the item is a category (has children)
            if self.channel_tree.get_children(item):
                category_text = self.channel_tree.item(item, "text").lower()
                child_visible = False
                for child_item in self.channel_tree.get_children(item):
                    child_text = self.channel_tree.item(child_item, "text").lower()
                    if search_term in child_text:
                        child_visible = True
                        break # Found one visible child, so category is visible
                if search_term in category_text or child_visible:
                    self.channel_tree.move(item, '', 'end')
            # If the item is a channel (no children) and not in a category
            else:
                channel_text = self.channel_tree.item(item, "text").lower()
                if search_term in channel_text:
                    self.channel_tree.move(item, '', 'end')

    # def toggle_auto_update(self):
    #     state = "啟用" if self.auto_update_var.get() else "停用"
    #     self.log_message(f"{state}自動更新")
    #     if self.auto_update_var.get():
    #         self.auto_update_scheduler()
    def toggle_auto_update(self):
        """
        切換是否在 on_message 事件中更新 UI。
        這不再啟動一個定時器，而是作為一個開關給 on_message 事件使用。
        """
        state = "啟用" if self.auto_update_var.get() else "停用"
        self.log_message(f"{state}新訊息自動附加功能")

    # def auto_update_scheduler(self):
    #     if self.auto_update_var.get():
    #         if self.current_channel:
    #             self.view_channel()
    #         interval = self.config.get("update_interval", 5) * 1000
    #         self.master.after(interval, self.auto_update_scheduler)

    def create_invite_link(self):
        if not self.current_selected_guild:
            messagebox.showerror("錯誤", "請先選擇一個服務器")
            return

        max_age = self.get_seconds_from_duration_string(self.invite_max_age_var.get())
        try:
            max_uses = int(self.invite_max_uses_var.get())
        except ValueError:
            max_uses = 0

        target_channel = self.current_channel or self.current_selected_guild.system_channel
        if not target_channel:
            target_channel = next((c for c in self.current_selected_guild.text_channels if c.permissions_for(self.current_selected_guild.me).create_instant_invite), None)

        if not target_channel:
            messagebox.showerror("錯誤", "沒有可用的頻道來創建邀請")
            return

        async def do_create_invite():
            try:
                invite = await target_channel.create_invite(max_age=max_age, max_uses=max_uses, temporary=False, unique=True)
                self.invite_url_var.set(invite.url)
                self.copy_invite_button.config(state=tk.NORMAL)
                self.log_message(f"創建邀請鏈接: {invite.url}")
            except Exception as e:
                messagebox.showerror("錯誤", f"創建邀請失敗: {e}")

        asyncio.run_coroutine_threadsafe(do_create_invite(), bot.loop)

    def get_seconds_from_duration_string(self, duration_str):
        return {
            "30 分鐘": 1800, "1 小時": 3600, "6 小時": 21600, "12 小時": 43200,
            "1 天": 86400, "7 天": 604800, "永久": 0
        }.get(duration_str, 0)

    def copy_invite_to_clipboard(self):
        url = self.invite_url_var.get()
        if url:
            self.master.clipboard_clear()
            self.master.clipboard_append(url)
            messagebox.showinfo("成功", "邀請鏈接已複製到剪貼板")

    # ... and so on for all other methods. The logic inside them is mostly sound.
    # The key was fixing the UI layout code. The following methods are restored to readable format.

    def open_batch_manager(self):
        self.notebook.select(self.batch_tab)

    def open_user_info(self):
        user_id = simpledialog.askstring("用戶查詢", "請輸入用戶ID:")
        if user_id and user_id.isdigit():
            asyncio.run_coroutine_threadsafe(self.get_user_info(int(user_id)), bot.loop)

    async def get_user_info(self, user_id):
        try:
            user = await bot.fetch_user(user_id)
            info = f"用戶名: {user.name}\nID: {user.id}\n創建時間: {user.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n頭像URL: {user.display_avatar.url}"
            messagebox.showinfo("用戶信息", info)
        except Exception as e:
            messagebox.showerror("錯誤", f"獲取用戶信息失敗: {e}")

    def open_server_stats(self):
        self.notebook.select(self.stats_tab)
        self.refresh_stats()

    def refresh_stats(self):
        if not bot.guilds: return
        server_stats = ""
        for guild in bot.guilds:
            server_stats += f"服務器: {guild.name}\n"
            server_stats += f"  成員數: {guild.member_count}\n"
            server_stats += f"  頻道數: {len(guild.channels)}\n"
            server_stats += f"  身分組: {len(guild.roles)}\n"
            server_stats += f"  創建時間: {guild.created_at.strftime('%Y-%m-%d')}\n\n"
        self.server_stats_text.config(state=tk.NORMAL)
        self.server_stats_text.delete(1.0, tk.END)
        self.server_stats_text.insert(tk.END, server_stats)
        self.server_stats_text.config(state=tk.DISABLED)

    def export_stats(self):
        content = self.server_stats_text.get(1.0, tk.END) + "\n\n" + self.user_stats_text.get(1.0, tk.END)
        if not content.strip():
            messagebox.showwarning("警告", "沒有可導出的統計數據")
            return
        file_path = filedialog.asksaveasfilename(defaultextension=".txt", title="保存統計報告")
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                messagebox.showinfo("成功", f"統計報告已保存到: {file_path}")
            except Exception as e:
                messagebox.showerror("錯誤", f"導出失敗: {e}")

    def clear_cache(self):
        self.avatar_cache.clear()
        self.message_history.clear()
        messagebox.showinfo("成功", "緩存已清理")

    def open_preferences(self):
        pref_window = tk.Toplevel(self.master)
        pref_window.title("首選項設置")
        pref_window.geometry("450x300")
        pref_window.transient(self.master)
        pref_window.grab_set()
        
        frame = ttk.Frame(pref_window, padding=20)
        frame.pack(fill=BOTH, expand=YES)
        
        ttk.Label(frame, text="機器人Token:").pack(pady=5, anchor=W)
        token_var = tk.StringVar(value=self.config.get("bot_token", ""))
        token_entry = ttk.Entry(frame, textvariable=token_var, width=50, show="*")
        token_entry.pack(pady=5, fill=X)

        ttk.Label(frame, text="自動更新間隔(秒):").pack(pady=5, anchor=W)
        interval_var = tk.StringVar(value=str(self.config.get("update_interval", 5)))
        ttk.Entry(frame, textvariable=interval_var, width=10).pack(pady=5, anchor=W)

        ttk.Label(frame, text="消息數量限制:").pack(pady=5, anchor=W)
        limit_var = tk.StringVar(value=str(self.config.get("message_limit", 50)))
        ttk.Entry(frame, textvariable=limit_var, width=10).pack(pady=5, anchor=W)

        def save_preferences():
            self.config["bot_token"] = token_var.get()
            self.config["update_interval"] = int(interval_var.get())
            self.config["message_limit"] = int(limit_var.get())
            self.save_config()
            messagebox.showinfo("成功", "設置已保存，部分設置需重啟生效。")
            pref_window.destroy()

        ttk.Button(frame, text="保存", command=save_preferences, bootstyle="success").pack(pady=20)

    def toggle_theme(self):
        # This is a placeholder, as changing theme requires app restart with ttkbootstrap
        messagebox.showinfo("主題切換", "請在 discord_gui_config.json 文件中修改 'theme' 欄位並重啟程式以切換主題。")

    def font_settings(self):
        size = simpledialog.askinteger("字體設置", "請輸入字體大小:", initialvalue=self.config.get("font_size", 10))
        if size:
            self.config["font_size"] = size
            self.save_config()
            messagebox.showinfo("字體設置", "字體大小已設置，重啟程序後生效。")
    
    def export_messages(self):
        if not self.current_channel or not self.last_messages:
            messagebox.showwarning("警告", "沒有可導出的消息")
            return
        file_path = filedialog.asksaveasfilename(defaultextension=".txt", title="保存消息歷史")
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    for msg in reversed(self.last_messages):
                        f.write(f"[{msg.created_at.strftime('%Y-%m-%d %H:%M:%S')}] {msg.author.name}: {msg.content}\n")
                messagebox.showinfo("成功", f"消息已導出到: {file_path}")
            except Exception as e:
                messagebox.showerror("錯誤", f"導出失敗: {e}")

    def import_settings(self):
        file_path = filedialog.askopenfilename(title="選擇設置文件")
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    imported_config = json.load(f)
                self.config.update(imported_config)
                self.save_config()
                messagebox.showinfo("成功", "設置已導入，重啟程序後生效。")
            except Exception as e:
                messagebox.showerror("錯誤", f"導入失敗: {e}")

    def export_settings(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".json", title="保存設置文件")
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(self.config, f, indent=2, ensure_ascii=False)
                messagebox.showinfo("成功", f"設置已導出到: {file_path}")
            except Exception as e:
                messagebox.showerror("錯誤", f"導出失敗: {e}")

    def execute_batch_operation(self):
        # Placeholder for batch operations
        messagebox.showinfo("提示", "此功能待實現。")

    def log_message(self, message, level="INFO"):
        log_entry = f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {level}: {message}\n"
        if hasattr(self, 'logs_text'):
            self.logs_text.config(state=tk.NORMAL)
            self.logs_text.insert(tk.END, log_entry)
            self.logs_text.config(state=tk.DISABLED)
            self.logs_text.see(tk.END)

    def clear_logs(self):
        self.logs_text.config(state=tk.NORMAL)
        self.logs_text.delete(1.0, tk.END)
        self.logs_text.config(state=tk.DISABLED)

    def save_logs(self):
        content = self.logs_text.get(1.0, tk.END)
        if not content.strip(): return
        file_path = filedialog.asksaveasfilename(defaultextension=".log", title="保存日誌")
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                messagebox.showinfo("成功", "日誌已保存")
            except Exception as e:
                messagebox.showerror("錯誤", f"保存失敗: {e}")

    def refresh_all(self):
        if bot.is_ready():
            self.guild_listbox.delete(0, tk.END)
            for guild in sorted(bot.guilds, key=lambda g: g.name):
                self.guild_listbox.insert(tk.END, guild.name)
            if self.current_channel:
                self.view_channel()
            self.log_message("已刷新所有內容")

    def reconnect_bot(self):
        self.status_text.set("正在重新連接...")
        self.log_message("請求重新連接機器人...")
        asyncio.run_coroutine_threadsafe(bot.close(), bot.loop)
        asyncio.run_coroutine_threadsafe(bot.start(self.config.get("bot_token")), bot.loop)
        # self.status_text.set("重新連接成功!")

    def update_time(self):
        self.time_label.config(text=datetime.datetime.now().strftime("%H:%M:%S"))
        self.master.after(1000, self.update_time)

    def show_help(self): messagebox.showinfo("幫助", "功能正在逐步完善中。")
    def show_shortcuts(self): messagebox.showinfo("快捷鍵", "...")
    def show_about(self): messagebox.showinfo("關於", "Discord GUI v3.1")

    def on_closing(self):
        if messagebox.askokcancel("確認", "確定要關閉程式嗎?"):
            for window in list(self.active_dm_windows.values()):
                if window.winfo_exists():
                    window.destroy()
            self.save_config()
            self.master.destroy()

# --- Bot 事件處理 ---
@bot.event
async def on_ready():
    print(f"機器人已登錄: {bot.user.name}")
    if app:
        app.master.after(0, lambda: app.status_indicator.config(bootstyle="success"))
        app.master.after(0, lambda: app.status_label.config(text="已連接"))
        app.master.after(0, lambda: app.status_text.set(f"已連接到 {len(bot.guilds)} 個服務器"))
        app.master.after(0, app.refresh_all)
        app.master.after(0, lambda: app.log_message(f"機器人已登錄: {bot.user.name}"))

@bot.event
async def on_message(message):
    if not app: return

    # 處理私訊
    if isinstance(message.channel, discord.DMChannel):
        user_id = message.channel.recipient.id if message.author.id == bot.user.id else message.author.id
        if user_id in app.active_dm_windows:
            dm_window = app.active_dm_windows[user_id]
            if dm_window.winfo_exists():
                app.master.after(0, dm_window.append_message, message)
        return

    # 處理公開頻道訊息
    if app.current_channel and message.channel.id == app.current_channel.id:
        # 只在啟用自動更新時增量添加，避免手動刷新時重複
        if app.auto_update_var.get():
            app.master.after(0, app.append_message_to_display, message)

# --- 程式啟動 ---
def start_bot(token):
    if not token:
        if app:
            app.master.after(0, lambda: messagebox.showerror("錯誤", "請在 '首選項' 中配置機器人Token"))
        return
    
    async def runner():
        try:
            await bot.start(token)
        except discord.LoginFailure:
            if app: app.master.after(0, lambda: messagebox.showerror("錯誤", "機器人Token無效"))
        except Exception as e:
            if app: app.master.after(0, lambda: messagebox.showerror("錯誤", f"啟動失敗: {e}"))

    bot.loop.create_task(runner())

def run_bot_in_thread():
    token = app.config.get("bot_token")
    threading.Thread(target=start_bot, args=(token,), daemon=True).start()
    
if __name__ == "__main__":
    # 從設定檔讀取主題
    config = {}
    try:
        with open("discord_gui_config.json", 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        pass # 使用預設主題

    theme_to_use = config.get("theme", "superhero")
    
    root = ttk.Window(themename=theme_to_use)
    app = ChannelViewer(root)

    root.bind('<F5>', lambda e: app.refresh_all())
    root.bind('<Control-q>', lambda e: app.on_closing())
    
    if app.config.get("bot_token"):
        # 在新的事件循環中啟動機器人執行緒
        threading.Thread(target=bot.run, args=(app.config.get("bot_token"),), daemon=True).start()
    
    if app.config.get("window_geometry"):
        try:
            root.geometry(app.config["window_geometry"])
        except:
            pass
    
    root.mainloop()