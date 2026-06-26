# 舊 APSVP：Dashboard 前端實作流程

來源專案：`C:\Users\ai\Desktop\smithfu\repositories\agriculture\apsvp\apsvp`

整理日期：2026-06-24

本文件聚焦 `dashboard` 所驅動的前端行為：URL → View → Template → JS、左側選單、Chart 1–5、Integration table，以及每日／節慶／近五年報表。

## 1. 前端架構總覽

舊系統不是傳統的「每點一頁就整頁刷新」，而是 SmartAdmin 的 AJAX navigation：

```text
第一次 GET /
  -> Index view
  -> index.html 回傳完整 HTML shell
  -> shell 內固定保留 header、navigation、#main、#content、footer

之後點左側選單
  -> JS 把 href 寫進 location.hash
  -> hashchange -> checkURL()
  -> loadURL(url, $('#content'))
  -> Django 回傳 AJAX HTML fragment
  -> fragment 被塞進 #content
  -> fragment 裡的 inline script 初始化該頁功能
```

因此前端有三層載入：

1. **App shell**：`index.html`，只在第一次進站完整載入。
2. **Page fragment**：About、Product Selector、Chart Tabs、報表操作頁，載入到 `#content`。
3. **Nested fragment**：Chart content、Integration table、動態左選單、報表結果，載入到頁面內指定 container。

## 2. App Shell 如何建立

URL：`/`

View：`dashboard.views.Index`

Template：`src/templates/index.html`

`index.html` include：

```text
header.html
navigation.html
main-panel.html
footer.html
shortcut.html
```

`main-panel.html` 的核心只有：

```html
<div id="main" role="main">
  <div id="ribbon">
    <ol class="breadcrumb"></ol>
  </div>
  <div id="content"></div>
</div>
```

`#content` 是後續所有主頁面 fragment 的注入位置。breadcrumb 也是 JS 動態產生，不是 Django template 每頁重畫。

`index.html` 載入順序的重要部分：

```text
jQuery / jQuery UI / jquery.cookie
  -> app.config.seed.js
  -> bootstrap.min.js
  -> jarvis.widget.js
  -> app.js
  -> app.custom.js
  -> basefunction.js
  -> showTaskTime.js
  -> Bootstrap multiselect / select
```

`app.js` 提供 SmartAdmin 原始 navigation、widget、scriptLoader、pageSetUp；`app.custom.js` 覆寫或擴充 AJAX loader、登入失效處理、左選單 lazy loading、panel 操作。

## 3. 主 AJAX 導航

### 3.1 點擊左側 href

SmartAdmin 在 `static/vendor/js/app.js` 綁定：

```javascript
$(document).on('click', 'nav a[href!="#"]', ...)
```

若連結不是 `_blank` 且目前項目未 active，JS 不直接開 href，而是：

```text
window.location.hash = link.href
```

例如使用者點：

```text
/zh-hant/daily-report/
```

瀏覽器概念上先變成：

```text
/#/zh-hant/daily-report/
```

接著觸發 `hashchange`。

### 3.2 checkURL()

`checkURL()` 會：

1. 從 `location.href` 的 `#` 後面取 URL。
2. 清除舊的 `nav li.active`。
3. 找出 href 相符的 nav item 並標成 active。
4. 更新 `document.title`。
5. 呼叫 `loadURL(url + location.search, $('#content'))`。

`app.custom.js` 另外在 hashchange 後執行：

```javascript
history.replaceState(null, '', '/');
```

也就是載入後又把瀏覽器顯示 URL 改回 `/`。這是一個舊系統特有行為；新版若需要瀏覽器上一頁、深連結與可分享 URL，不建議照搬。

### 3.3 自訂 loadURL()

`static/js/app.custom.js` 的 `loadURL(url, container, data, type)` 是前端最核心函式。

參數：

- `url`：Django endpoint。
- `container`：HTML fragment 要放入的 jQuery container。
- `data`：GET/POST data，可省略。
- `type`：預設 GET，也支援 POST。

送 request 前會：

- 非安全 HTTP method 加 `X-CSRFToken`。
- 清除舊 DataTables。
- 清除舊 interval。
- destroy Jarvis widgets。
- 呼叫舊頁面的 `pagedestroy()` / `globalPageDestory()`。
- destroy sparkline、datepicker、select2、mask、slider 等 plugin instance。
- 清空 container。
- 放入 loading spinner。
- 若 container 是 `#content`，更新 breadcrumb 並捲到頁首。

成功後：

- `container.html(data)` 注入 fragment。
- 淡入顯示。
- 呼叫 `updateCeleryScheduleUi()`。

403 時：

- 解析後端 `{'login_url': ...}`。
- 導向登入頁。

這也是為什麼 Django AJAX views 回傳的是 HTML，不是 JSON：舊前端把後端 template 當成可直接執行的 UI component。

## 4. AJAX Fragment 的初始化模式

大部分 AJAX template 底部都有：

```javascript
pageSetUp();

var pagefunction = function () {
  // bind events / create charts / create DataTables
};

var scripts = [/* dependencies */];
scriptLoader(scripts, pagefunction);
```

流程是：

```text
HTML fragment 注入 DOM
  -> inline script 執行
  -> scriptLoader 檢查並載入頁面需要的 JS
  -> dependencies 載入完成
  -> 執行 pagefunction()
```

所以每個 template 同時負責三件事：

- HTML 結構。
- 將 Django context serialize 進 JavaScript。
- 初始化與事件綁定。

這是舊系統前端耦合最重的地方。

## 5. 左側選單流程

### 5.1 第一層由 Index 產生

`Index.get_context_data()` 查出目前 `user_watchlist`，並把 Config 分為：

- `totals`
- `agricultures`
- `livestocks`
- `fisheries`

`navigation.html` 直接 render 這些第一層選單。

部分 AMIS 商品群不是由資料庫樹動態 render，而是在 `navigation.html` 中 hard-code 大量 URL：

```text
/chart-tab/chart/?config=5&type=1&sources=...&products=...
```

### 5.2 下一層 lazy loading

可展開的 anchor 具有：

```html
<a href="#"
   data-load
   data-load-url="/jarvismenu/.../">
```

或同時具有可導航 href：

```html
<a href="/chart-tab/watchlist/.../"
   data-load
   data-load-url="/jarvismenu/.../">
```

`app.custom.js` 在 `nav a[data-load]` 上監聽 click：

```text
點擊
  -> preventDefault
  -> GET data-load-url
  -> 顯示小 spinner
  -> JarvisMenu view
  -> ajax/jarvismenu.html 回傳一個 <ul>
  -> JS 把 <ul> insertAfter(anchor)
  -> 移除並重新初始化 jarvismenu accordion
  -> 標記 data-load=true，避免重複載入
  -> 再 trigger click，讓節點展開或導航
```

後端 `jarvismenu_extra_context()` 決定下一層是：

```text
Config
  -> AbstractProduct
  -> Type 或 child AbstractProduct
  -> Source
  -> Chart Tabs
```

`item.to_direct` 決定該節點 href 是 `#` 還是 chart-tab URL。

### 5.3 選單警示圖示

`contents/color-alert.html` 根據 `MonitorProfile` 顯示 danger / warning icon。

`app.custom.js` 還會掃描父層 `a[color-alert]`，若子孫有 danger 或 warning，clone 一個警示 icon 到父層。這讓尚未展開的分類也能顯示底下存在警示。

## 6. Chart Tabs 的二段載入

不論從 watchlist 左選單或 Product Selector 進來，第一個 endpoint 都只回傳頁籤，不直接畫圖。

### 6.1 第一段：Chart tabs

Watchlist 模式 URL：

```text
/chart-tab/watchlist/<wi>/resource/<ct>-<oi>/
/chart-tab/watchlist/<wi>/resource/<ct>-<oi>/sub-resource/<lct>-<loi>/
```

Product Selector 模式 URL：

```text
/chart-tab/chart/?config=<id>&type=<id>&products=<ids>&sources=<ids>
```

View：`dashboard.views.ChartTabs`

Template：`ajax/chart-tab.html`

後端只決定有哪些 `Chart`，template 為每個 chart 建立：

```html
<a data-load-url="/chart-content/.../"
   data-load
   href="#chart-1"
   data-toggle="tab">
```

以及對應的空 container：

```html
<div class="tab-pane" id="chart-1"></div>
```

### 6.2 第二段：點 tab 才載入 chart content

`chart-tab.html` 綁定 Bootstrap tab 的 `shown.bs.tab`：

```text
shown.bs.tab
  -> 讀 anchor.data-load-url
  -> 找 href 指定的 tab-pane
  -> loadURL(chartContentUrl, tabPane)
  -> 將 anchor 的 data-load 標成已載入
```

頁面初始化後會自動：

```javascript
$('#chart-functions-tab a[data-toggle="tab"][data-load]:eq(0)').trigger('click');
```

所以第一張圖自動載入，其他圖直到使用者點擊才載入。

已載入的 tab 再被點擊時不重送 request，只對既有 Highcharts 執行 `reflow()`。

## 7. ChartContents 共通流程

URL：`/chart-content/chart/<ci>/...`

View：`dashboard.views.ChartContents`

`ChartContents` 不固定 template，而是：

```text
Chart.objects.get(id=ci).template_name
```

所以 chart id 與 template 的關係由 DB 控制。

Context 主要包含：

- `series_options`：後端聚合後、可直接餵給 Highcharts 的資料。
- `unit_json`：價格／數量／重量單位。
- `chart`：Chart model。
- watchlist 模式可能再含 `monitor_profiles_json`。
- Chart 5 再含 event form、content type、object id。

若 `series_options` 為空，改回 `ajax/no-data.html`。

## 8. Chart 1 前端流程

Template：`ajax/chart-1-content.html`

JS：`static/js/highcharts/chart1Helper.js`

後端資料：最近 14 天 `get_daily_price_volume()`。

前端初始化順序：

```text
chart1Helper.init(chartId)
  -> 讀 tab container 上的 monitorProfiles / watchlistProfiles

chart1Helper.create(..., seriesOptions, unit)
  -> Highcharts 價格、數量、重量 series
  -> 日期範圍存進 chart1Helper.manager.dateRange

dataTableHelper.createRaw(...)
  -> 原始資料表轉 DataTable

integrationHelper.loadTable(container, min, max)
  -> 以目前 chart 日期範圍 POST Integration table endpoint
```

Chart 1 是唯一會在初始畫圖後立刻再請求 Integration table 的 chart。

## 9. Chart 2 前端流程

Template：`ajax/chart-2-content.html`

JS：`static/js/highcharts/chart2Helper.js`

後端資料：不限制最近 14 天的 `get_daily_price_volume()`。

前端初始化：

```text
chart2Helper.init()
  -> chart2Helper.create()
  -> dataTableHelper.createRaw()
```

結構與 Chart 1 類似，但不載入 Integration table。

## 10. Chart 3 前端流程

Template：`ajax/chart-3-content.html`

JS：`static/js/highcharts/chart3Helper.js`

後端資料：`get_daily_price_by_year()`，把不同年份日期對齊到同一個基準年以疊圖比較。

每個 Type 可以有三組圖：

- price
- volume
- weight

設定 panel 有：

- `display-years`：決定哪些年度 series 顯示。
- `average-years`：決定平均線使用哪些年度。

按 Submit 時不呼叫後端：

```text
chart3Helper.updateChartSeries()
  -> replaceAvgSeries(chart, averageYears)
  -> displaySeries(chart, displayYears)
```

也就是 Chart 3 的年度切換與平均線重算主要在瀏覽器端完成。

## 11. Chart 4 前端流程

Template：`ajax/chart-4-content.html`

JS：`static/js/highcharts/chart4Helper.js`

後端資料：`get_monthly_price_distribution()`，包含每月 min、25%、median、75%、max、mean。

Highcharts 使用類似 box plot 的資料物件：

```text
{x, low, q1, median, q3, high, mean}
```

設定 panel 只有 `average-years`。

按 Submit 時會重新送後端：

```text
讀目前 chart tab 的 data-load-url
  -> POST average_years[]
  -> ChartContents 重新計算 monthly distribution
  -> loadURL() 用新的 fragment 整個替換 Chart 4 container
```

Chart 3 與 Chart 4 的差異很重要：

- Chart 3：現有資料在前端切換。
- Chart 4：選年度後重新 POST，後端重算分布。

## 12. Chart 5 前端流程

Template：`ajax/chart-5-content.html`

JS：

- `static/js/highcharts/chart5Helper.js`
- `static/js/datatables/dataTableHelper.js`

Chart 5 由兩部分組成：行情圖 + 事件表。

### 12.1 行情與事件旗標

```text
ChartContents
  -> get_daily_price_volume()
  -> Chart 5 template
  -> chart5Helper.create() 畫價格線
  -> chart.loadEvents()
  -> GET /events/api/event/?content_type=...&object_id=...&datatable=false
  -> 將事件轉成 Highcharts flags series
  -> flags 掛在 avg_price series 上
```

事件更新、新增、刪除成功後：

```text
DataTable reload
  -> chart5Helper.loadEvents()
  -> 所有 Chart 5 重抓事件並重畫 flags
```

### 12.2 Event DataTable CRUD

`dataTableHelper.createEvent()` 使用 server-side DataTables：

```text
GET /events/api/event/
  query: content_type, object_id, datatable=true
```

操作：

- New：POST `/events/api/event/`
- Edit：PUT `/events/api/event/<id>/`
- Delete：DELETE `/events/api/event/<id>/`
- Batch file：POST `/events/api/eventbatchfile/`，再逐筆 POST event endpoint。

CSRF token 都由 AJAX beforeSend 加入。

## 13. Raw Data Table

Chart 1–4 的 raw table 由 template 先 render HTML rows，再由：

```javascript
dataTableHelper.createRaw(tableId)
```

轉成 DataTable。

功能包含：

- 搜尋與排序。
- responsive table。
- CSV / Excel / Print / Copy。
- 日期欄預設倒序。

它不是 AJAX DataTable；資料已經在 ChartContents HTML response 裡。

## 14. Integration Table 前端流程

Integration table 是 Chart 1 的第三層 AJAX fragment。

### 14.1 初始化 request

`chart-1-content.html` 取得 Highcharts 的日期範圍：

```javascript
var min = chart1Helper.manager.dateRange.min;
var max = chart1Helper.manager.dateRange.max;
integrationHelper.loadTable($container, min, max);
```

`integrationHelper.loadTable()` POST：

```text
start_date=<JS timestamp>
end_date=<JS timestamp>
to_init=true
```

URL 依來源模式不同：

- Watchlist：`/integration-table/chart/<ci>/watchlist/...`
- Product selector：`/integration-table/chart/<ci>/type/<type>/products/<products>/?sources=...`

後端：`IntegrationTable`

初始 template：`ajax/integration-panel.html`

### 14.2 初始 HTML

Template 結構：

```text
integration-panel.html
  -> 每個 Type 一個 accordion panel
  -> include contents/integration-table.html
  -> table tbody include ajax/integration-row.html
```

初始 rows 通常是：

- This Term
- Last Term
- 5 Years

`dataTableHelper.createIntegration()` 將 HTML table 轉成 DataTable，建立 export buttons 與 `Load Historical Data` button。

### 14.3 載入歷年資料

按 `Load Historical Data`：

```text
integrationHelper.loadRowFunction()
  -> 從 table 的 data-type-id 取得 Type
  -> 從父 container 的 ajaxData 取得 URL、min、max
  -> POST 同一 URL
     start_date
     end_date
     to_init=false
     type=<typeId>
  -> IntegrationTable 改用 ajax/integration-row.html
  -> 回傳只有 <tr>...</tr>
  -> DataTables rows.add($trs).draw()
```

接著：

- 對新增 cell 畫 sparkline。
- `compareIntegrationRow()` 以 `data-base=true` 的本期資料為基準，顯示紅／綠百分比差異。
- Button 改成「All Result Successfully Loaded」並 disabled。

## 15. Product Selector 前端流程

URL：`/product-selector/`

Template：`ajax/product-selector.html`

這是一個三步 Bootstrap Wizard。

```text
Step 1 載入 Config
  -> POST /product-selector-ui/step/1/

Next
  -> POST /product-selector-ui/step/2/
     config_id=<selected config>

Next
  -> POST /product-selector-ui/step/3/
     config_id=<selected config>
     type_id=<selected type>

Enquiry
  -> 組合 query string
  -> GET /chart-tab/chart/?config=...&type=...&products=...&sources=...
  -> fragment 載入 #sub-content
```

Wizard 每一步都是 `product-selector-ui.html` fragment；最後才進入前述 Chart Tabs 二段載入流程。

## 16. 每日報表前端流程

主操作頁：

```text
/daily-report/
  -> dashboard.views.DailyReport
  -> ajax/daily-report.html
```

前端：

1. Datepicker 預設昨天。
2. 使用者按下載。
3. POST `/dailytrans/daily-report/download/`。
4. 設定 `xhrFields.responseType = 'blob'`。
5. 後端回 xlsx bytes 與 `Content-Disposition`。
6. JS 建立 Blob URL 與暫時 `<a download>`。
7. 自動觸發下載，再 revoke Blob URL。

這條目前實際使用的是「直接下載 Excel」流程。

另有舊 endpoint `/dailytrans/daily-report/render/` 與 `daily-report-iframe.html`，會把 Google Drive file id render 成 preview iframe，但目前 `daily-report.html` 的 `data-load-url` 已指向 download endpoint。

## 17. 節慶報表前端流程

主操作頁：

```text
/festival-report/
  -> dashboard.views.FestivalReport
  -> ajax/festival-report.html
```

畫面有三種 request mode，但都 POST 同一 endpoint：

```text
/dailytrans/festival-report/render/
```

### 17.1 一般節慶報表

送出：

```text
roc_year
festival_id
refresh=false
oneday=false
custom_search=false
```

結果 `festival-report-iframe.html` 顯示兩個 Google Drive iframe：

- 價格報表。
- 數量報表。

有權限者可按 refresh，再 POST `refresh=true` 重新產檔與替換 Google Drive file。

### 17.2 節慶品項單日查詢

送出：

```text
day/month/year
festival_id
oneday=true
custom_search=false
```

結果 template 直接 render HTML table，前端可用：

- `table2csv` 下載 CSV。
- jsPDF + autoTable 下載 PDF。

### 17.3 自訂日期與品項

前端 multiselect 最多選 30 個品項，送出：

```text
day/month/year
item_search[]
custom_search=true
oneday=false
```

結果 render 價格表與數量表，兩者都能下載 CSV / PDF。

此頁的結果不是 iframe-only；同一 template 依 context 切換 iframe、alert 或 HTML table。

## 18. 近五年報表前端流程

主操作頁：

```text
/last5years-report/
  -> dashboard.views.Last5YearsReport
  -> ajax/last5years-report.html
```

`Last5YearsReport` 將 `Last5YearsItems` 整理成：

```text
display name -> product ids + source ids
```

使用者選品項後 POST：

```text
/dailytrans/last5years-report/render/

sel_item_id_list
sel_item_source_list
sel_item_name
```

結果 template：`apps/dailytrans/templates/last5years-report-iframe.html`

雖然檔名有 iframe，但實際不是 iframe：

- 後端把 pandas DataFrame 轉成 HTML table。
- template 直接用 inline JavaScript 建 Highcharts。
- 價格、數量、重量、價重等資料存在時各畫一張圖。
- HTML table 再轉成 DataTable，提供 Copy / Excel。

這條流程沒有共用 chart1–5 helper，而是 template 內手寫 Highcharts options。

## 19. Celery 任務狀態前端

`index.html` 全域載入 `showTaskTime.js`。

當頁面有對應 task metadata 時，JS 會請求：

```text
GET/POST /get-celery-task-schedule/
  taskName
  taskKey
```

後端向 Flower API 查 Celery task，再回：

- state
- succeeded
- nextTime

`loadURL()` 成功後會嘗試呼叫 `updateCeleryScheduleUi()`，因此每次 AJAX 換頁或載入圖表，都可能同步更新資料更新時間提示。

## 20. 前端狀態存放位置

舊系統沒有集中式 state store，狀態散在：

- URL hash：目前主頁 fragment。
- DOM attributes：`data-load-url`、`data-load`、`data-type-id`。
- DOM element property：Integration container 的 `ajaxData`。
- Global variables：`pagefunction`、`scripts`、`window.ajax`、chart helper managers。
- Chart tab container property：`monitorProfiles`、`watchlistProfiles`。
- jQuery plugin instance：Highcharts、DataTables、Jarvis widgets、datepicker、multiselect。
- Django-rendered inline JSON：`series_options`、`unit_json`、event ids。

新版重建時，這些狀態應明確集中到 router、page component state、API response model。

## 21. 前端請求序列範例

### 從左側商品點進 Chart 1

```text
GET /
  -> index.html shell

點 Config
  -> GET /jarvismenu/<wi>/config/<configId>/
  -> 插入下一層 <ul>

點 Product leaf
  -> hashchange
  -> GET /chart-tab/watchlist/<wi>/resource/abstractproduct-<id>/...
  -> chart-tab.html 塞入 #content

chart-tab.html 自動點第一個 tab
  -> GET /chart-content/chart/1/watchlist/<wi>/resource/...
  -> chart-1-content.html 塞入 #chart-1
  -> chart1Helper 畫圖與 raw table

Chart 1 初始化 Integration
  -> POST /integration-table/chart/1/watchlist/...
  -> integration-panel.html 塞入 integration container
  -> DataTable + sparkline
```

### 從 Product Selector 進 Chart 4

```text
GET /product-selector/
  -> product-selector.html

POST /product-selector-ui/step/1/
POST /product-selector-ui/step/2/ config_id
POST /product-selector-ui/step/3/ config_id,type_id

GET /chart-tab/chart/?config=...&type=...&products=...&sources=...
  -> chart-tab.html

點 Chart 4
  -> GET /chart-content/chart/4/type/.../products/.../?sources=...
  -> chart-4-content.html

變更 average years
  -> POST 同一 chart-content URL, average_years[]
  -> 後端重算並替換整個 Chart 4 fragment
```

## 22. 新版重建時的前端切分建議

可以把舊流程對應成以下元件與 API：

```text
AppLayout
  - Header
  - SidebarTree
  - MainContent + real router

SidebarTree
  - GET children API
  - node expansion state
  - alert state

ProductSelector
  - GET configs/types/products/sources API
  - local wizard state

ChartWorkspace
  - chart tabs
  - GET chart data JSON
  - Chart1 / Chart2 / Chart3 / Chart4 / Chart5 components

RawDataTable
IntegrationTable
EventManager

DailyReportPage
FestivalReportPage
LastFiveYearsReportPage
```

建議避免照搬：

- HTML fragment endpoint。
- template 內 inline JavaScript。
- 全域 `pagefunction`。
- 以 DOM attribute 當主要 state。
- hash 後立即 `history.replaceState('/', ...)`。
- Query 結果直接 serialize 成 template-specific dict。

較穩定的新流程：

```text
URL router
  -> page component
  -> JSON API
  -> typed frontend state
  -> chart/table components render
```

這樣仍能保留舊系統的使用者操作順序，但可以把 Django template、jQuery plugin lifecycle 與資料聚合解耦。
