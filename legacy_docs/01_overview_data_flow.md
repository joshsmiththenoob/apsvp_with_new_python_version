# 舊 APSVP 系統整理：總覽與資料流

來源專案：`C:\Users\ai\Desktop\smithfu\repositories\agriculture\apsvp\apsvp`

整理日期：2026-06-24

## 1. 系統定位

舊系統是一個 Django 1.x 風格的行情查詢與報表平台，主要功能是：

- 以商品樹與監看清單產生左側選單。
- 使用 AJAX 載入圖表頁籤、圖表內容、原始資料表、整合比較表。
- 以 Celery 排程從多個來源匯入行情資料到 `DailyTran`。
- 產生每日報表、節慶報表、近五年月平均報表，部分報表會上傳 Google Drive 後以 iframe 呈現。
- 事件資料可被掛到 `Config`、`AbstractProduct` 等 content object，用於 Chart 5 顯示事件線。

## 2. Django 入口

主要設定與入口：

- `src/manage.py`
- `src/dashboard/configs/base.py`
- `src/dashboard/settings.py`
- `src/dashboard/urls.py`
- `src/dashboard/views.py`
- `src/dashboard/utils.py`
- `src/templates/index.html`

`ROOT_URLCONF = 'dashboard.urls'`。首頁使用 `Index` view 與 `index.html`，`index.html` 再 include：

- `header.html`
- `navigation.html`
- `main-panel.html`
- `footer.html`
- `shortcut.html`

前端主軸來自 SmartAdmin：`app.js`、自訂覆寫 `static/js/app.custom.js`，再由各 AJAX template 載入 Highcharts / DataTables helper。

## 3. 核心資料流

### 3.1 外部資料進資料庫

大致流程：

```text
Celery beat schedule
  -> app-specific task，例如 DailyCropBuilder / DailyFruitBuilder / DailyHogBuilder
  -> app-specific builder.py
  -> apps.dailytrans.builders.* API 類別
  -> request 外部 API / scraping / Google 或其他資料來源
  -> load / hook / DataFrame 清理
  -> DailyTran 新增、更新或刪除
```

關鍵檔案：

- `src/dashboard/celery.py`：beat schedule 定義。
- `src/apps/*/tasks.py`：各商品類別每日匯入 task。
- `src/apps/*/builder.py`：每個商品 domain 的 builder。
- `src/apps/dailytrans/builders/abstract.py`：API builder 抽象基底。
- `src/apps/dailytrans/builders/apis.py`：蔬果產地 API 範例，會比對 API 與 DB 後更新 `DailyTran`。
- `src/apps/dailytrans/models.py`：`DailyTran` 行情主表。

### 3.2 資料庫進圖表

大致流程：

```text
使用者點左側選單或產品查詢
  -> /chart-tab/...
  -> dashboard.views.ChartTabs
  -> dashboard.utils.*_chart_tab_extra_context
  -> templates/ajax/chart-tab.html
  -> 前端點第一個 tab
  -> /chart-content/...
  -> dashboard.views.ChartContents
  -> dashboard.utils.*_chart_contents_extra_context
  -> apps.dailytrans.utils.get_daily_price_volume / get_daily_price_by_year / get_monthly_price_distribution
  -> ajax/chart-N-content.html
  -> chartNHelper.js + Highcharts + DataTables
```

`ChartContents.get_template_names()` 會讀 `Chart.template_name`，所以圖表 id 與 template 對應由資料庫 `configs.Chart` 控制。註解中可見預期值：

- Chart 1：`ajax/chart-1-content.html`
- Chart 2：`ajax/chart-2-content.html`
- Chart 3：`ajax/chart-3-content.html`
- Chart 4：`ajax/chart-4-content.html`
- Chart 5：`ajax/chart-5-content.html`

### 3.3 資料庫進報表

每日報表：

```text
/navigation.html Daily Report
  -> /daily-report/
  -> dashboard.views.DailyReport
  -> ajax/daily-report.html
  -> POST /dailytrans/daily-report/download/
  -> apps.dailytrans.views.download_daily_report
  -> 若本地已有同日期 xlsx 則下載；否則 DailyReportFactory 產檔再下載
```

節慶報表：

```text
/navigation.html Festival Report
  -> /festival-report/
  -> dashboard.views.FestivalReport
  -> ajax/festival-report.html
  -> POST /dailytrans/festival-report/render/
  -> apps.dailytrans.views.render_festival_report
  -> FestivalReportFactory / Google Drive / DB cache 或自訂查詢資料表
```

近五年月平均報表：

```text
/navigation.html Last 5 Years Report
  -> /last5years-report/
  -> dashboard.views.Last5YearsReport
  -> ajax/last5years-report.html
  -> POST /dailytrans/last5years-report/render/
  -> apps.dailytrans.views.render_last5years_report
  -> Last5YearsReportFactory
  -> iframe template + Highcharts / DataTables
```

## 4. 快取使用

舊系統大量用 `dashboard.caches.redis_instance`，多數 ORM QuerySet 會以 pickle 存入 Redis：

- 商品子節點：`product{product_id}_children`、`watchlist{watchlist_id}_product{product_id}_children`
- Config 第一層商品：`config{config_id}_lv1_products`
- Watchlist children：`watchlist{watchlist_id}_children`
- Watchlist related configs：`watchlist{watchlist_id}_related_configs`
- Chart list：`content_type_config{config_id}_charts`、`content_type_product{product_id}_charts`
- 近五年品項：`last5_years_items`

重建新版時要特別注意：這些 method 表面上像即時查 DB，實際上會受 Redis 舊資料影響。

## 5. 權限與登入

`dashboard.views.login_required` 是自訂 decorator：

- 未登入的一般 request：redirect `settings.LOGIN_URL`。
- 未登入 AJAX request：回 JSON `{'login_url': settings.LOGIN_URL}` 且 status 403。

前端 `loadURL()`、事件 AJAX、報表 AJAX 都有處理 403 redirect。

## 6. 新版重建建議

可以先把新版切成四個邊界：

1. Reference data：`Config / Type / Source / Unit / AbstractProduct` 商品樹。
2. Watchlist data：`Watchlist / WatchlistItem / MonitorProfile` 左側選單與監看邏輯。
3. Transaction data：`DailyTran` 與 chart aggregation service。
4. Report data：`DailyReport / FestivalReport / Last5YearsItems / Festival*` 與 Google Drive export。

圖表頁建議先重建 API 層，不要直接複製舊 template 內嵌 JS 流程。舊系統把資料組裝、template、JS 初始化綁得很緊，新版可以改成：

```text
REST endpoint returns JSON
  -> frontend chart component consumes JSON
  -> table component consumes same JSON or table endpoint
```
