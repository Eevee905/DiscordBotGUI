# --- START OF FILE updater.py ---

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import requests
import json
import os
import shutil
import threading
from datetime import datetime

# --- 設定 ---
# 替換成你自己的 GitHub 用戶名和儲存庫名稱
GITHUB_USER = "Eevee905"
GITHUB_REPO = "DiscordBotGUI"
# 分支名稱
BRANCH_NAME = "main"

# GitHub Raw 內容的基礎 URL
GITHUB_REPO_URL = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/{BRANCH_NAME}/"

VERSION_FILE = "version.info"
MANIFEST_FILE = "manifest.json"
CONFIG_FILE = "updater_config.json"

class AppUpdater(ttk.Window):
    def __init__(self):
        super().__init__(themename="superhero")
        self.title("應用程式更新工具 (支援私人倉庫)")
        self.geometry("600x500")
        self.resizable(False, False)

        self.current_version = self.get_local_version()
        self.latest_version = "N/A"
        self.update_manifest = None
        self.github_token = ""
        
        self.load_config()
        self.setup_ui()
        
        # 啟動時自動檢查，延遲一下讓 UI 先顯示
        self.after(500, self.check_for_updates)

    def get_local_version(self):
        """讀取本地版本號"""
        try:
            with open(VERSION_FILE, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except FileNotFoundError:
            return "0.0.0"

    def load_config(self):
        """載入設定檔 (讀取 Token)"""
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.github_token = config.get("github_token", "")
        except Exception as e:
            print(f"載入設定失敗: {e}")

    def save_config(self):
        """儲存設定檔"""
        try:
            config = {"github_token": self.github_token}
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4)
        except Exception as e:
            self.log(f"儲存設定失敗: {e}")

    def get_headers(self):
        """產生 HTTP Header，如果有的話帶上 Token"""
        headers = {}
        if self.github_token:
            headers["Authorization"] = f"token {self.github_token}"
            # 某些情況下 GitHub API 需要 User-Agent
            headers["User-Agent"] = "DiscordBotGUI-Updater"
        return headers

    def setup_ui(self):
        """設定使用者介面"""
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill=BOTH, expand=YES)

        ttk.Label(main_frame, text="程式更新", font=("Microsoft JhengHei UI", 18, "bold")).pack(pady=(0, 20))
        
        # 版本資訊
        version_frame = ttk.Frame(main_frame)
        version_frame.pack(fill=X, pady=10)
        ttk.Label(version_frame, text="目前版本:", font=("Microsoft JhengHei UI", 12)).pack(side=LEFT)
        self.current_version_label = ttk.Label(version_frame, text=self.current_version, font=("Microsoft JhengHei UI", 12, "bold"), bootstyle=INFO)
        self.current_version_label.pack(side=LEFT, padx=5)
        
        ttk.Label(version_frame, text="最新版本:", font=("Microsoft JhengHei UI", 12)).pack(side=LEFT, padx=(20, 0))
        self.latest_version_label = ttk.Label(version_frame, text="等待檢查...", font=("Microsoft JhengHei UI", 12, "bold"), bootstyle=SECONDARY)
        self.latest_version_label.pack(side=LEFT, padx=5)

        # 狀態標籤
        self.status_label = ttk.Label(main_frame, text="準備就緒", font=("Microsoft JhengHei UI", 11))
        self.status_label.pack(pady=10)
        
        # 進度條
        self.progress = ttk.Progressbar(main_frame, mode='determinate', bootstyle=STRIPED)
        self.progress.pack(fill=X, pady=10)

        # 按鈕區域
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=10)
        
        self.check_button = ttk.Button(button_frame, text="重新檢查", command=self.check_for_updates, bootstyle=PRIMARY)
        self.check_button.pack(side=LEFT, padx=5)
        
        self.update_button = ttk.Button(button_frame, text="立即更新", command=self.start_update_thread, state=DISABLED, bootstyle=SUCCESS)
        self.update_button.pack(side=LEFT, padx=5)

        # Token 設定按鈕
        ttk.Button(button_frame, text="設定 Token", command=self.set_token, bootstyle="outline-secondary").pack(side=LEFT, padx=5)
        
        # 日誌
        log_frame = ttk.LabelFrame(main_frame, text="更新日誌", bootstyle=PRIMARY)
        log_frame.pack(fill=BOTH, expand=YES, pady=(10,0))
        self.log_text = tk.Text(log_frame, height=8, font=("Consolas", 10), relief="flat", state=DISABLED)
        self.log_text.pack(fill=BOTH, expand=YES, padx=5, pady=5)

    def set_token(self):
        """設定 GitHub Token"""
        token = simpledialog.askstring("GitHub Token", "請輸入 GitHub Personal Access Token (PAT):\n(私人倉庫必須設定)", initialvalue=self.github_token, parent=self)
        if token is not None:
            self.github_token = token.strip()
            self.save_config()
            self.log("Token 已更新，請點擊「重新檢查」。")
            messagebox.showinfo("設定", "Token 已儲存。")

    def log(self, message):
        """在日誌區域顯示訊息"""
        now = datetime.now().strftime("%H:%M:%S")
        self.log_text.config(state=NORMAL)
        self.log_text.insert(END, f"[{now}] {message}\n")
        self.log_text.see(END)
        self.log_text.config(state=DISABLED)
        self.update_idletasks()

    def check_for_updates(self):
        """檢查是否有新版本"""
        self.log("正在從 GitHub 檢查更新...")
        self.check_button.config(state=DISABLED)
        self.update_button.config(state=DISABLED)
        self.latest_version_label.config(text="檢查中...", bootstyle=WARNING)
        
        # 使用線程避免 UI 卡死
        threading.Thread(target=self._do_check_update, daemon=True).start()

    def _do_check_update(self):
        try:
            import time
            timestamp = int(time.time())
            url = f"{GITHUB_REPO_URL}{VERSION_FILE}?t={timestamp}"

            # # 這裡加入了 headers
            # response = requests.get(GITHUB_REPO_URL + VERSION_FILE, headers=self.get_headers(), timeout=10)
            
            # 這裡加入了 headers (和上面的 url)
            response = requests.get(url, headers=self.get_headers(), timeout=10)
            
            if response.status_code == 200:
                self.latest_version = response.text.strip()
                self.after(0, lambda: self.latest_version_label.config(text=self.latest_version, bootstyle=SUCCESS))
                self.after(0, lambda: self.log(f"取得最新版本號: {self.latest_version}"))

                if self.latest_version > self.current_version:
                    self.after(0, lambda: self.status_label.config(text="發現新版本！請點擊「立即更新」。", bootstyle=WARNING))
                    self.after(0, lambda: self.update_button.config(state=NORMAL))
                    self.after(0, lambda: self.log("版本過舊，建議更新。"))
                else:
                    self.after(0, lambda: self.status_label.config(text="您的程式已是最新版本。", bootstyle=SUCCESS))
                    self.after(0, lambda: self.log("無需更新。"))
            
            # --- 處理私人倉庫或無效 Token 的情況 ---
            elif response.status_code == 404:
                 # 404 對於私人倉庫來說，通常代表「沒登入」或「網址錯了」
                 # 這裡我們把它視為可能需要 Token
                 self.after(0, lambda: self.status_label.config(text="⚠️ 找不到倉庫 (若為私人倉庫請設定 Token)", bootstyle=DANGER))
                 self.after(0, lambda: self.latest_version_label.config(text="未知", bootstyle=SECONDARY))
                 self.after(0, lambda: self.log("錯誤: 404 Not Found。如果是私人倉庫，請點擊下方按鈕設定 Token。"))
            
            elif response.status_code == 401 or response.status_code == 403:
                 self.after(0, lambda: self.status_label.config(text="⚠️ 權限不足 (Token 無效或過期)", bootstyle=DANGER))
                 self.after(0, lambda: self.latest_version_label.config(text="Auth Error", bootstyle=DANGER))
                 self.after(0, lambda: self.log("錯誤: 權限不足。請檢查 Token 是否正確或過期。"))
            
            else:
                self.after(0, lambda: self.handle_error(f"HTTP 錯誤: {response.status_code}"))
                
        except requests.exceptions.RequestException as e:
            self.after(0, lambda: self.handle_error(f"網路連線錯誤: {e}"))
        finally:
            self.after(0, lambda: self.check_button.config(state=NORMAL))

    def handle_error(self, message):
        """統一處理一般錯誤 (僅顯示文字，不彈窗)"""
        self.status_label.config(text="發生錯誤 (請查看日誌)", bootstyle=DANGER)
        self.latest_version_label.config(text="失敗", bootstyle=DANGER)
        self.log(f"錯誤: {message}")

    def start_update_thread(self):
        """使用執行緒來執行更新，避免 GUI 凍結"""
        self.update_button.config(state=DISABLED)
        self.check_button.config(state=DISABLED)
        update_thread = threading.Thread(target=self.run_update, daemon=True)
        update_thread.start()

    def run_update(self):
        """執行更新流程"""
        # 1. 備份舊檔案
        self.after(0, lambda: self.log("正在備份目前版本..."))
        backup_dir = f"backup_{self.current_version}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        try:
            # 加入 headers
            manifest_response = requests.get(GITHUB_REPO_URL + MANIFEST_FILE, headers=self.get_headers(), timeout=10)
            if manifest_response.status_code != 200:
                self.after(0, lambda: self.handle_error(f"無法下載 manifest (Code: {manifest_response.status_code})，中止更新。"))
                return

            self.update_manifest = manifest_response.json()
            os.makedirs(backup_dir, exist_ok=True)
            for file_path in self.update_manifest['files']:
                if os.path.exists(file_path):
                    backup_file_path = os.path.join(backup_dir, file_path)
                    os.makedirs(os.path.dirname(backup_file_path), exist_ok=True)
                    shutil.copy(file_path, backup_file_path)
            self.after(0, lambda: self.log(f"備份完成，存放於: {backup_dir}"))
        except Exception as e:
            self.after(0, lambda: self.handle_error(f"備份失敗: {e}"))
            self.after(0, lambda: self.check_button.config(state=NORMAL))
            return

        # 2. 下載新檔案
        self.after(0, lambda: self.log("開始下載更新檔案..."))
        self.after(0, lambda: self.progress.configure(value=0))
        files_to_update = self.update_manifest['files']
        total_files = len(files_to_update)
        
        try:
            for i, file_path in enumerate(files_to_update):
                file_url = GITHUB_REPO_URL + file_path
                self.after(0, lambda p=file_path: self.log(f"下載中: {p}"))
                
                local_dir = os.path.dirname(file_path)
                if local_dir:
                    os.makedirs(local_dir, exist_ok=True)

                # 加入 headers
                file_response = requests.get(file_url, headers=self.get_headers(), timeout=10)
                if file_response.status_code == 200:
                    with open(file_path, 'wb') as f:
                        f.write(file_response.content)
                else:
                    raise Exception(f"無法下載 {file_path} (HTTP {file_response.status_code})")
                
                # 更新進度條
                progress_val = (i + 1) / total_files * 100
                self.after(0, lambda v=progress_val: self.progress.configure(value=v))

            self.after(0, lambda: self.log("所有檔案下載完成。"))
            self.after(0, lambda: self.progress.configure(value=100))
            
            # 3. 更新完成
            self.current_version = self.latest_version
            self.after(0, lambda: self.current_version_label.config(text=self.current_version))
            self.after(0, lambda: self.status_label.config(text="更新成功！請重啟主程式。", bootstyle=SUCCESS))
            self.after(0, lambda: messagebox.showinfo("更新完成", "您的應用程式已成功更新到最新版本！"))
        except Exception as e:
            self.after(0, lambda: self.handle_error(f"更新錯誤: {e}"))
            self.after(0, lambda: self.log("建議從備份資料夾還原檔案。"))
            self.after(0, lambda e=e: messagebox.showerror("更新失敗", f"錯誤:\n{e}\n\n建議從 {backup_dir} 還原。"))
        finally:
            self.after(0, lambda: self.check_button.config(state=NORMAL))

if __name__ == "__main__":
    app = AppUpdater()
    app.mainloop()