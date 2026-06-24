學生系統使用手冊

快速開始

1. 建置與啟動
- 建議使用虛擬環境（venv）並安裝 `requirements.txt`。

Windows (PowerShell):
```powershell
python -m venv venv
venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

2. 載入展示用資料（選用）
```powershell
venv\Scripts\python.exe manage.py load_demo_data
```
- 預設會建立範例帳號與課程：
  - 教師：`t001` / 密碼 `password`（顯示名稱：Prof. Alice）
  - 教師：`t002` / 密碼 `password`（顯示名稱：Dr. Bob）
  - 學生：`s001`、`s002`、`s003`、`s004`（密碼皆為 `password`）
  - 範例課程：`CS101`, `MATH201`, `ENG103`, `HIST210`（部分課程已分配教師與時段）

3. 登入
- 開啟瀏覽器：`http://127.0.0.1:8000/`
- 使用上方範例帳號或自行註冊。

主要功能
- 學生：
  - 我的課表（圖像化週格）：顯示課名、課程代碼、任課教師。
  - 列印/下載課表：下載 CSV，欄位含節次與每週的課程（每格格式：`代碼 名稱 (教師)`）。
  - 我的成績：匯出成績、檢視本學期與歷年成績。
- 教師：
  - 建立/編輯課程（教師可編輯，但刪除僅限管理員）。
  - 管理選課申請（審核/拒絕）。
  - 教師總覽與匯出：匯出任教課程的所有成績。
- 管理員：
  - 管理教師/學生帳號（刪除帳號）。
  - 從系統移除學生選課紀錄。

開發者備註
- `Course.schedule` 為逗號分隔的時段代碼（例如 `MON_1,TUE_3`）。
- 範例管理指令：`python manage.py load_demo_data`（建立假資料）；`python manage.py check`（系統檢查）。

如需協助，請提供錯誤訊息或瀏覽器截圖。