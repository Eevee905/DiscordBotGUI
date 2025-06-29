# 伊布7專用 GUI 管理工具

![GUI預覽圖](https://via.placeholder.com/800x450.png?text=在這裡放一張你的程式預覽圖)
<!-- [請修改] 將上面的 URL 換成你程式的實際預覽圖。你可以將圖片上傳到 GitHub issue，然後複製圖片連結來使用 -->

這是一款使用 Python 和 Tkinter (ttkbootstrap) 開發的 Discord 圖形化介面管理工具。它允許使用者透過直觀的 GUI 介面來瀏覽伺服器、頻道、成員，並進行訊息收發、建立邀請等操作。

## ✨ 主要功能

*   **伺服器與頻道瀏覽**：以樹狀結構清晰展示所有伺服器和頻道。
*   **即時訊息檢視**：查看指定頻道的歷史訊息，並可自動接收新訊息。
*   **訊息發送**：在任何你有權限的文字頻道中發送訊息，並支援附加檔案。
*   **成員管理**：查看伺服器成員列表、狀態，並可快速開啟私訊聊天室。
*   **私訊聊天**：為每個私訊對象開啟獨立的聊天視窗，並載入歷史訊息。
*   **邀請連結生成**：快速為頻道建立可自訂有效期和使用次數的邀請連結。
*   **多頁籤介面**：將主要功能、批量操作、統計和日誌分頁管理，介面整潔。
*   **現代化主題**：採用 `ttkbootstrap` 實現美觀且可切換的 UI 主題。
*   **自動更新**：內建更新程式，一鍵即可將工具更新到最新版本。

## 🚀 開始使用

### 環境需求

*   Python 3.8 或更高版本

### 安裝步驟

1.  **下載專案**
    點擊此頁面右上角的 `Code` -> `Download ZIP`，或使用 Git clone：
    ```bash
    git clone https://github.com/[請修改-你的GitHub使用者名稱]/[請修改-你的專案名稱].git
    cd [請修改-你的專案名稱]
    ```

2.  **安裝依賴庫**
    本專案需要一些外部 Python 庫。你可以透過 `requirements.txt` 檔案一次性安裝所有必要的依賴。

    ```bash
    pip install -r requirements.txt
    ```
    > 如果你沒有 `requirements.txt` 檔案，請手動安裝以下函式庫：
    > ```bash
    > pip install discord.py ttkbootstrap Pillow pytz
    > ```

3.  **設定 Bot Token**
    *   首次執行 `bot_open_GUI_v3.py`，程式會提示你設定 Bot Token。
    *   點擊功能表列的 `設置` -> `首選項`。
    *   在「機器人Token」欄位中，貼上你的 Discord Bot Token。
    *   點擊「保存」並重新啟動程式。

    > **重要**：你的 Bot Token 會被儲存在本地的 `discord_gui_config.json` 檔案中，請妥善保管此檔案，不要洩漏給他人。

4.  **執行主程式**
    一切準備就緒後，執行主程式即可：
    ```bash
    python bot_open_GUI_v3.py
    ```

## 🔄 如何更新

本工具內建了方便的更新程式，當有新版本發布時，你無需重新下載整個專案。

1.  執行 `updater.py` 檔案：
    ```bash
    python updater.py
    ```
2.  更新程式會自動檢查是否有新版本。
3.  如果發現新版本，點擊「立即更新」按鈕即可。
4.  更新完成後，關閉更新程式並重新執行 `bot_open_GUI_v3.py`。

## 📜 檔案結構說明

```
.
├── bot_open_GUI_v3.py       # 主程式
├── updater.py               # 更新程式
├── requirements.txt         # 依賴庫列表
├── version.info             # 版本號檔案
├── icons/                   # 圖示資源資料夾
└── README.md                # 說明文件
```

## 🤝 貢獻

歡迎提交 Pull Request 或開啟 Issue 來為本專案做出貢獻。

1.  Fork 本專案
2.  建立你的功能分支 (`git checkout -b feature/AmazingFeature`)
3.  提交你的變更 (`git commit -m 'Add some AmazingFeature'`)
4.  推送到分支 (`git push origin feature/AmazingFeature`)
5.  開啟一個 Pull Request

## 📄 授權

本專案採用 MIT 授權。詳情請見 `LICENSE` 檔案。
<!-- 如果你沒有 LICENSE 檔案，可以移除這行 -->