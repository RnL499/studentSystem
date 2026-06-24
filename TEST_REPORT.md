測試報告 — StudentSystem (展示 / 主要修正)

測試摘要
- 測試日期：2026-06-24
- 環境：Windows, Python 3.13 (venv), Django 6.0.6

目標
1. 將學生課表改為格線式顯示（週一~週五, 第1~8節），顯示課名、課程代碼與教師名稱。
2. 提供列印/下載課表功能，輸出 CSV 檔案。
3. 修復模板語法錯誤與索引錯誤。
4. 提供示範資料以便快速驗證功能。

操作步驟與結果

1) 範例資料載入
- 指令：`python manage.py load_demo_data`
- 預期：建立教師 `t001,t002`、學生 `s001..s004`、多門課程與選課紀錄。
- 結果：命令執行成功，輸出 `Demo data loaded.`。驗證：資料表中已有對應使用者、課程與選課紀錄。

2) 模板語法修復
- 問題 A：`Could not parse the remainder: '=='MON'`。
  - 原因：模板中的比較表達式缺少空格（`d=='MON'`）。
  - 修正：改為 `{% if d == 'MON' %}`。
  - 驗證：刷新頁面後不再出現 TemplateSyntaxError。

- 問題 B：`Could not parse the remainder: '[d][p]' from 'grid[d][p]'`。
  - 原因：Django 模板不支援複雜的中括號多重索引表達式。
  - 修正：在 view 中預先建立 `rows`（每列代表一節，內含該節每週的課程清單），模板以迭代 `rows` 渲染。
  - 驗證：頁面能正確渲染格線式課表，無錯誤。

3) 課表內容與列印
- 課表主頁：顯示課名、課程代碼與教師名稱（教師以 `profile.full_name` 或 `username` 顯示）。
- 列印/下載：改為 CSV 下載，檔名 `schedule_<username>.csv`，內容有 BOM，方便 Excel 開啟。每格包含 `代碼 名稱 (教師)`；測試下載並以 Excel 開啟，格式正確。

4) 系統檢查
- 指令：`python manage.py check`
- 結果：`System check identified no issues (0 silenced).`

已驗證的文件與程式修改
- `grades/views.py`：修正 `student_schedule`/`student_schedule_print`，新增 `rows` 並回傳 CSV。
- `templates/uiux/student_schedule.html`：以 `rows` 渲染格線，顯示教師名稱。
- `templates/uiux/student_schedule_print.html`：改為由 view 回傳 CSV（不再直接以 HTML 列印）。
- `grades/management/commands/load_demo_data.py`：新增示範資料載入指令。
- `USER_MANUAL.md`、`TEST_REPORT.md`：新增說明與測試報告。

待辦 / 建議
- UI 美化：為不同課程著色、合併跨節顯示（目前每節獨立列出）。
- CSV 格式選項：提供長格式（每行一門課，含週次與節次）或短格式（目前為每節一列）。
- 權限測試：驗證教師與管理員的新增/刪除權限流程與錯誤處理。

結論
- 本次修正成功解決模板錯誤並完成格線式課表與 CSV 匯出，示範資料已能快速建立常見場景供展示或手動測試使用。若需要，我可以接著：
  - 美化 UI（顏色、合併跨節）、
  - 提供更多 CSV 格式或伺服器端 PDF 輸出；
  - 撰寫自動化測試（Django TestCase）來覆蓋主要流程。
