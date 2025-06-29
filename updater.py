import tkinter as tk
from tkinter import ttk, messagebox
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
# 通常使用 main 或 master 分支
BRANCH_NAME = "main"

# GitHub Raw 內容的基礎 URL
GITHUB_REPO_URL = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/{BRANCH_NAME}/"

VERSION_FILE = "version.info"
MANIFEST_FILE = "manifest.json"

class AppUpdater(ttk.Window):
    def __init__(self):
        super().__init__(themename="superhero")
        self.title("應用程式更新工具")
        self.geometry("600x450")
        self.resizable(False, False)

        self.current_version = self.get_local_version()
        self.latest_version = "N/A"
        self.update_manifest = None

        self.setup_ui()
        self.check_for_updates()

    def get_local_version(self):
        """讀取本地版本號"""
        try:
            with open(VERSION_FILE, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except FileNotFoundError:
            return "0.0.0"

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
        self.latest_version_label = ttk.Label(version_frame, text="檢查中...", font=("Microsoft JhengHei UI", 12, "bold"), bootstyle=SUCCESS)
        self.latest_version_label.pack(side=LEFT, padx=5)

        # 狀態標籤
        self.status_label = ttk.Label(main_frame, text="正在初始化...", font=("Microsoft JhengHei UI", 11))
        self.status_label.pack(pady=20)
        
        # 進度條
        self.progress = ttk.Progressbar(main_frame, mode='determinate', bootstyle=STRIPED)
        self.progress.pack(fill=X, pady=10)

        # 按鈕
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=20)
        self.check_button = ttk.Button(button_frame, text="重新檢查", command=self.check_for_updates, state=DISABLED)
        self.check_button.pack(side=LEFT, padx=10)
        self.update_button = ttk.Button(button_frame, text="立即更新", command=self.start_update_thread, state=DISABLED, bootstyle=SUCCESS)
        self.update_button.pack(side=LEFT, padx=10)
        
        # 日誌
        log_frame = ttk.LabelFrame(main_frame, text="更新日誌", bootstyle=PRIMARY)
        log_frame.pack(fill=BOTH, expand=YES, pady=(10,0))
        self.log_text = tk.Text(log_frame, height=8, font=("Consolas", 10), relief="flat", state=DISABLED)
        self.log_text.pack(fill=BOTH, expand=YES, padx=5, pady=5)


    def log(self, message):
        """在日誌區域顯示訊息"""
        now = datetime.now().strftime("%H:%M:%S")
        self.log_text.config(state=NORMAL)
        self.log_text.insert(END, f"[{now}] {message}\n")
        self.log_text.see(END)
        self.log_text.config(state=DISABLED)
        self.update_idletasks() # 強制更新UI

    def check_for_updates(self):
        """檢查是否有新版本"""
        self.log("正在從 GitHub 檢查更新...")
        self.check_button.config(state=DISABLED)
        self.update_button.config(state=DISABLED)
        
        try:
            response = requests.get(GITHUB_REPO_URL + VERSION_FILE, timeout=10)
            if response.status_code == 200:
                self.latest_version = response.text.strip()
                self.latest_version_label.config(text=self.latest_version)
                self.log(f"取得最新版本號: {self.latest_version}")

                if self.latest_version > self.current_version:
                    self.status_label.config(text="發現新版本！請點擊「立即更新」。", bootstyle=WARNING)
                    self.update_button.config(state=NORMAL)
                    self.log("版本過舊，建議更新。")
                else:
                    self.status_label.config(text="您的程式已是最新版本。", bootstyle=SUCCESS)
                    self.log("無需更新。")
            else:
                self.handle_error("無法取得版本檔案。")
        except requests.exceptions.RequestException as e:
            self.handle_error(f"網路連線錯誤: {e}")
        
        self.check_button.config(state=NORMAL)

    def handle_error(self, message):
        """統一處理錯誤"""
        self.status_label.config(text=f"錯誤: {message}", bootstyle=DANGER)
        self.latest_version_label.config(text="錯誤")
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
        self.log("正在備份目前版本...")
        backup_dir = f"backup_{self.current_version}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        try:
            # 只備份 manifest 中列出的檔案
            manifest_response = requests.get(GITHUB_REPO_URL + MANIFEST_FILE, timeout=10)
            if manifest_response.status_code != 200:
                self.handle_error("無法下載 manifest 檔案，中止更新。")
                return

            self.update_manifest = manifest_response.json()
            os.makedirs(backup_dir, exist_ok=True)
            for file_path in self.update_manifest['files']:
                if os.path.exists(file_path):
                    # 建立備份資料夾結構
                    backup_file_path = os.path.join(backup_dir, file_path)
                    os.makedirs(os.path.dirname(backup_file_path), exist_ok=True)
                    shutil.copy(file_path, backup_file_path)
            self.log(f"備份完成，存放於: {backup_dir}")
        except Exception as e:
            self.handle_error(f"備份失敗: {e}")
            self.log("備份失敗，中止更新以確保安全。")
            self.check_button.config(state=NORMAL)
            return

        # 2. 下載新檔案
        self.log("開始下載更新檔案...")
        self.progress['value'] = 0
        files_to_update = self.update_manifest['files']
        total_files = len(files_to_update)
        
        try:
            for i, file_path in enumerate(files_to_update):
                file_url = GITHUB_REPO_URL + file_path
                self.log(f"下載中: {file_path}")
                
                # 建立本地資料夾（如果不存在）
                local_dir = os.path.dirname(file_path)
                if local_dir:
                    os.makedirs(local_dir, exist_ok=True)

                # 下載並寫入檔案
                file_response = requests.get(file_url, timeout=10)
                if file_response.status_code == 200:
                    with open(file_path, 'wb') as f:
                        f.write(file_response.content)
                else:
                    raise Exception(f"無法下載 {file_path}")
                
                # 更新進度條
                self.progress['value'] = (i + 1) / total_files * 100
                self.update_idletasks()

            self.log("所有檔案下載完成。")
            self.progress['value'] = 100
            
            # 3. 更新完成
            self.current_version = self.latest_version
            self.current_version_label.config(text=self.current_version)
            self.status_label.config(text="更新成功！您可以關閉此視窗並重新啟動主程式。", bootstyle=SUCCESS)
            messagebox.showinfo("更新完成", "您的應用程式已成功更新到最新版本！")
        except Exception as e:
            self.handle_error(f"更新過程中發生錯誤: {e}")
            self.log("更新失敗！建議從備份資料夾還原檔案。")
            messagebox.showerror("更新失敗", f"更新過程中發生錯誤:\n{e}\n\n建議從 {backup_dir} 還原檔案。")
        finally:
            self.check_button.config(state=NORMAL)


if __name__ == "__main__":
    app = AppUpdater()
    app.mainloop()