# 舊 APSVP 系統整理：URL -> View -> Template -> JS 流程

來源專案：`C:\Users\ai\Desktop\smithfu\repositories\agriculture\apsvp\apsvp`

## 1. URL 總覽

主路由在 `src/dashboard/urls.py`。

非 i18n prefix：

| URL | View / Include | 用途 |
|---|---|---|
| `/accounts/` | `apps.accounts.urls` | 登入、登出、改密碼 |
| `/events/` | `apps.events.urls` | 事件 API |
| `/dailytrans/` | `apps.dailytrans.urls` | 報表 render / download |
| `/jsi18n/` | `javascript_catalog` | 前端 gettext |
| `/set-user-language/<lang>/` | `Index` | 切換語言後回首頁 |
| `/set-user-watchlist/<wi>/` | `Index` | 切換 watchlist 後回首頁 |
| `/get-celery-task-schedule/` | `get_celery_task_schedule` | 前端查 Celery 任務狀態 |

有 i18n prefix 的頁面與 AJAX：

| URL | View | Template | 用途 |
|---|---|---|---|
| `/` | `Index` | `index.html` | 主畫面 shell |
| `/about/` | `About` | `ajax/about.html` | 關於頁 |
| `/browser-not-support/` | `BrowserNotSupport` | `browser-not-support.html` | IE fallback |
| `/jarvismenu/<wi>/<ct>/<oi>/` | `JarvisMenu` | `ajax/jarvismenu.html` | 左選單延遲載入下一層 |
| `/jarvismenu/<wi>/<ct>/<oi>/<lct>/<loi>/` | `JarvisMenu` | `ajax/jarvismenu.html` | 左選單延遲載入，保留上一層 context |
| `/chart-tab/chart/` | `ChartTabs` | `ajax/chart-tab.html` | 產品查詢模式的 chart tabs |
| `/chart-tab/watchlist/<wi>/resource/<ct>-<oi>/` | `ChartTabs(watchlist_base=True)` | `ajax/chart-tab.html` | Watchlist 模式 chart tabs |
| `/chart-content/chart/<ci>/type/<type>/products/<products>/` | `ChartContents(product_selector_base=True)` | DB `Chart.template_name` | 產品查詢模式 chart content |
| `/chart-content/chart/<ci>/watchlist/<wi>/resource/...` | `ChartContents(watchlist_base=True)` | DB `Chart.template_name` | Watchlist 模式 chart content |
| `/integration-table/chart/<ci>/...` | `IntegrationTable` | `ajax/integration-panel.html` 或 `ajax/integration-row.html` | 整合比較表 |
| `/daily-report/` | `DailyReport` | `ajax/daily-report.html` | 每日報表操作頁 |
| `/festival-report/` | `FestivalReport` | `ajax/festival-report.html` | 節慶報表操作頁 |
| `/last5years-report/` | `Last5YearsReport` | `ajax/last5years-report.html` | 近五年月平均報表操作頁 |
| `/product-selector/` | `ProductSelector` | `ajax/product-selector.html` | 商品查詢 wizard |
| `/product-selector-ui/step/<step>/` | `ProductSelectorUI` | `ajax/product-selector-ui.html` | wizard 每一步的選項 |

`apps.dailytrans.urls`：

| URL | Function view | 用途 |
|---|---|---|
| `/dailytrans/daily-report/render/` | `render_daily_report` | Google Drive iframe 顯示，每日報表舊流程 |
| `/dailytrans/daily-report/download/` | `download_daily_report` | 下載 xlsx，目前 daily-report.html 使用這條 |
| `/dailytrans/festival-report/render/` | `render_festival_report` | 節慶報表 iframe / 表格 |
| `/dailytrans/last5years-report/render/` | `render_last5years_report` | 近五年月平均報表 iframe |

`apps.events.api.urls`：

| URL | API view | 用途 |
|---|---|---|
| `/events/api/eventtype/` | `EventTypeListCreateAPIView` | 事件類型列表 / 新增 |
| `/events/api/eventtype/<pk>/` | `EventTypeRetrieveUpdateDestroyAPIView` | 事件類型 CRUD |
| `/events/api/event/` | `EventListCreateAPIView` | 事件列表 / 新增 / DataTables source |
| `/events/api/event/<pk>/` | `EventRetrieveUpdateDestroyAPIView` | 事件 CRUD |
| `/events/api/event-autocomplete/` | `autocomplete` | 事件類型 autocomplete |
| `/events/api/eventbatchfile/` | `EventBatchFileAPIView` | Chart 5 批次匯入事件 Excel |

## 2. 主畫面流程

```text
GET /
  -> dashboard.views.Index
  -> index.html
  -> include navigation.html / main-panel.html / footer.html / shortcut.html
  -> load static/js/app.custom.js
  -> 使用者點左側 href
  -> SmartAdmin navAsAjax / loadURL() 將內容放入 #content
```

`Index.get_context_data()` 準備：

- `watchlists`：全部 watchlist，依 `user.info.watchlist_viewer` 過濾 `watch_all=True`。
- `user_watchlist`：URL 指定 watchlist 或 default watchlist。
- `totals`：Config id 2, 3, 4。
- `agricultures`：Config id 1, 5, 6, 7。
- `livestocks`：Config id 8, 9, 10, 11, 12, 14。
- `fisheries`：Config id 13 的第一層 products。

## 3. 左側選單流程

Template：`src/templates/navigation.html`

靜態第一層分類：

- Main
- Admin
- Grand Totals
- Agricultures
- Livestocks
- Fisheries
- AMIS 自訂清單區塊：由 `user.info.amislist_viewer` 控制，內含很多 hard-coded `/chart-tab/chart/?config=...` 連結。

動態展開：

```text
navigation.html <a data-load data-load-url="/jarvismenu/...">
  -> static/js/app.custom.js 監聽 nav a[data-load]
  -> AJAX GET data-load-url
  -> dashboard.views.JarvisMenu
  -> dashboard.utils.jarvismenu_extra_context
  -> ajax/jarvismenu.html 回傳 <ul><li>...</li></ul>
  -> app.custom.js insertAfter($this)
  -> 重新初始化 jarvismenu accordion
```

`jarvismenu_extra_context()` 依 `ct` 分支：

- `config`：找 `Config.first_level_products(watchlist)`，下一層 `ct='abstractproduct'`。
- `abstractproduct`：依 product 狀態決定下一層是 `type`、子 `abstractproduct`、或 `source`。
- `type`：若上一層是 product，可能列 product children 或 source。
- `source`：通常已是可直接進 chart tab 的 leaf。

## 4. Watchlist 圖表流程

```text
使用者點左側某 leaf / config
  -> href /chart-tab/watchlist/<wi>/resource/<ct>-<oi>/...
  -> ChartTabs(watchlist_base=True)
  -> watchlist_base_chart_tab_extra_context()
  -> ajax/chart-tab.html
  -> JS 自動 trigger 第一個 chart tab
  -> /chart-content/chart/<ci>/watchlist/<wi>/resource/...
  -> ChartContents(watchlist_base=True)
  -> watchlist_base_chart_contents_extra_context()
  -> apps.dailytrans.utils 依 chart id 聚合 DailyTran
  -> ajax/chart-N-content.html
  -> chartNHelper.js 畫 Highcharts、DataTables
```

Watchlist 模式資料篩選：

- `content_type=config`：`watchlist.children().filter(product__config__id=object_id)`
- `content_type=abstractproduct`：`watchlist.children().filter_by_product(product__id=object_id)`
- `content_type=type`：以 `last_object_id` product 找 watchlist items，再限制 `Type`。
- `content_type=source`：以 `last_object_id` product 找 watchlist items，再限制 `Source`。

## 5. Product Selector 流程

```text
/navigation.html Product Selector
  -> /product-selector/
  -> ProductSelector
  -> ajax/product-selector.html
  -> Step 1 POST /product-selector-ui/step/1/
  -> Step 2 POST /product-selector-ui/step/2/ with config_id
  -> Step 3 POST /product-selector-ui/step/3/ with config_id,type_id
  -> 使用者查詢
  -> /chart-tab/chart/?config=...&type=...&products=...&sources=...
  -> ChartTabs(product selector mode)
  -> /chart-content/chart/<ci>/type/<type>/products/<products>/?sources=...
```

`product_selector_ui_extra_context()`：

- Step 1：全部 `Config`。
- Step 2：`Config.types()`。
- Step 3：`Config.products().filter(track_item=True, type=...)`，再套特殊規則：
  - config 5：花果菜特殊 parent / FB 類處理。
  - config 13 + type 2：產地魚貨改用 `track_item=False` parent。
  - 部分類別顯示 parent 或 code。

## 6. Chart content 與 JS

### Chart 1

- Template：`ajax/chart-1-content.html`
- Backend：`get_daily_price_volume()`，Chart 1 額外限制最近 14 天。
- JS：`static/js/highcharts/chart1Helper.js`
- 同頁會初始化 raw datatable 與 integration table。

### Chart 2

- Template：`ajax/chart-2-content.html`
- Backend：`get_daily_price_volume()`，不限制日期。
- JS：`static/js/highcharts/chart2Helper.js`
- 初始化 raw datatable。

### Chart 3

- Template：`ajax/chart-3-content.html`
- Backend：`get_daily_price_by_year()`。
- JS：`static/js/highcharts/chart3Helper.js`
- 有顯示年份與平均年份設定 panel。

### Chart 4

- Template：`ajax/chart-4-content.html`
- Backend：`get_monthly_price_distribution()`。
- JS：`static/js/highcharts/chart4Helper.js`
- 預設選最近五個完整年度，可 POST `average_years[]`。

### Chart 5

- Template：`ajax/chart-5-content.html`
- Backend：`get_daily_price_volume()` + `EventForm` + content type/object id。
- JS：`static/js/highcharts/chart5Helper.js`、`dataTableHelper.createEvent()`。
- 事件資料走 `/events/api/event/`，批次匯入走 `/events/api/eventbatchfile/`。

## 7. Integration table 流程

Chart 1 會載入整合表：

```text
chart-1-content.html
  -> integrationHelper.loadTable($container, min, max)
  -> POST /integration-table/chart/<ci>/...
  -> IntegrationTable.get_context_data()
  -> get_integration(..., to_init=True)
  -> ajax/integration-panel.html
  -> contents/integration-table.html
  -> DataTables 初始化
  -> 使用者按 Load Historical Data
  -> POST 同一 URL, to_init=False, type=<typeId>
  -> ajax/integration-row.html
```

`get_integration()` 會產生：

- This Term
- Last Term
- 5 Years
- 使用者按載入後，再回傳歷年逐年資料列。

## 8. 報表頁流程

### Daily Report

```text
/daily-report/
  -> DailyReport
  -> ajax/daily-report.html
  -> 使用者選 date 後 POST /dailytrans/daily-report/download/
  -> download_daily_report
  -> 找本地 xlsx 或 DailyReportFactory 產生
  -> responseType blob，前端建立 <a download>
```

### Festival Report

```text
/festival-report/
  -> FestivalReport.get_context_data()
  -> festival_list / roc_year_list / item_list
  -> ajax/festival-report.html
  -> POST /dailytrans/festival-report/render/
```

`render_festival_report()` 有三條分支：

- 一般節慶報表：查 `Festival` 與 `FestivalReport` cache，沒有就 `FestivalReportFactory` 產 Excel、上傳 Google Drive、寫 DB。
- `oneday=True`：指定單日、指定節慶品項，直接回資料。
- `custom_search=True`：指定日期與最多 30 個品項，回 DataFrame JSON / HTML 資料。

### Last 5 Years Report

```text
/last5years-report/
  -> Last5YearsReport
  -> Last5YearsItems cache / DB
  -> ajax/last5years-report.html
  -> POST /dailytrans/last5years-report/render/
  -> Last5YearsReportFactory
  -> last5years-report-iframe.html
```
