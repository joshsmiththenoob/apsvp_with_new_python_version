# Dashboard：Request → Context → Template → JavaScript → 網頁

整理日期：2026-06-25

適用專案：`apsvp_from_zero_new_python_version`

## 1. 這份文件的目的

這份文件是寫給熟悉 Django 後端、但還不熟悉前端流程的開發者。

讀完後，應該能回答以下問題：

1. 瀏覽器送出 request 後，Django 如何找到正確的 view？
2. View 如何查詢與整理資料，並放入 context？
3. Template 如何把 context 轉成 HTML？
4. JavaScript 何時執行？如何安全地取得 Django 提供的資料？
5. 使用者最後在瀏覽器看到的畫面，是在哪一層產生的？
6. 新版 APSVP 應該如何逐步開發，而不重複舊版前後端高度耦合的問題？

## 2. 文件放置建議

本文件放在：

```text
docs/dashboard_request_context_template_js_flow.md
```

建議保留兩種文件目錄：

```text
legacy_docs/
  舊版系統考古、既有流程與重建時的參考資料

docs/
  新版系統目前架構、開發規範、操作流程與設計決策
```

不建議把新版文件也放進 `legacy_docs/`，否則日後容易分不清楚「舊系統實際行為」與「新版建議做法」。

## 3. 目前新版專案的實際狀態

目前 dashboard 是一個很小的 Django 5.2 骨架：

```text
config/urls.py
  -> apps/dashboard/urls.py
      -> apps/dashboard/views.py
          -> apps/dashboard/templates/dashboard/index.html
          -> apps/dashboard/templates/dashboard/chart_page.html
```

目前尚未出現：

- dashboard 的資料庫 model。
- 查詢或資料整理 service。
- JavaScript 檔案。
- CSS 檔案。
- AJAX / Fetch API。
- 圖表套件。
- JSON API。
- Template 繼承與共用 layout。

因此，現在看到的是「Django server-side rendering 的第一步」，還沒有走到 JavaScript 處理資料的階段。

## 4. 現有首頁 `/` 的完整流程

### 4.1 瀏覽器送出 request

使用者開啟：

```text
GET /
```

瀏覽器送出的 HTTP request 會先進入 Django。

### 4.2 專案主路由

設定檔 `config/settings.py` 指定：

```python
ROOT_URLCONF = "config.urls"
```

所以 Django 先讀 `config/urls.py`。

其中：

```python
path("", include("apps.dashboard.urls"))
```

意思是：

> 所有未被前面路由攔截的根路徑，都繼續交給 `apps.dashboard.urls` 判斷。

### 4.3 App 路由

`apps/dashboard/urls.py` 目前有：

```python
path("", views.IndexView.as_view(), name="index")
```

空字串代表根目錄，因此 `/` 會交給 `IndexView`。

### 4.4 View 建立 context

`IndexView` 繼承 `TemplateView`，並指定：

```python
template_name = "dashboard/index.html"
```

收到 GET request 後，`TemplateView` 會執行 `get_context_data()`。

目前程式先呼叫：

```python
context = super().get_context_data(**kwargs)
```

這一步會保留 Django class-based view 原本提供的 context，再加入：

```python
context["title"] = "重要農產品價量平台 Mini"
context["menu_items"] = [
    {"name": "每日價量查詢", "url": "/chart/"},
    {"name": "監控清單", "url": "#"},
    {"name": "每日報表", "url": "#"},
]
```

此時可以把 context 想成：

```python
{
    "view": <目前的 IndexView instance>,
    "title": "重要農產品價量平台 Mini",
    "menu_items": [
        {"name": "每日價量查詢", "url": "/chart/"},
        {"name": "監控清單", "url": "#"},
        {"name": "每日報表", "url": "#"},
    ],
}
```

最後：

```python
return context
```

Django 會把這份 context 交給 `dashboard/index.html`。

### 4.5 Template 將 context 轉成 HTML

Template 中：

```django
<title>{{ title }}</title>
<h1>{{ title }}</h1>
```

`{{ title }}` 會被換成：

```text
重要農產品價量平台 Mini
```

選單部分：

```django
{% for item in menu_items %}
    <li>
        <a href="{{ item.url }}">{{ item.name }}</a>
    </li>
{% endfor %}
```

Django template engine 會跑三次迴圈，產生三個 `<li>`。

重要觀念：

- `{{ ... }}`：輸出一個值。
- `{% ... %}`：執行 template 邏輯，例如 `for`、`if`、`url`、`static`。
- Template 不會把 Python 程式直接送到瀏覽器。
- 瀏覽器收到的是 Django 已經 render 完成的 HTML 字串。

### 4.6 Django 回傳 response

完整概念如下：

```text
Browser
  -> GET /
  -> config.urls
  -> apps.dashboard.urls
  -> IndexView
  -> get_context_data()
  -> context
  -> dashboard/index.html
  -> render 成 HTML
  -> HttpResponse
  -> Browser 解析並顯示 HTML
```

目前首頁沒有 JavaScript，所以瀏覽器收到 HTML 後，只需要建立 DOM 並顯示畫面。

## 5. 現有 `/chart/` 流程與目前的缺口

使用者點擊「每日價量查詢」後，瀏覽器會送出：

```text
GET /chart/
```

路由：

```python
path("chart/", views.ChartPageView.as_view(), name="chart_page")
```

View：

```python
class ChartPageView(TemplateView):
    template_name = "dashboard/chart_page.html"
```

這個 view 沒有覆寫 `get_context_data()`，所以不會提供首頁自訂的：

- `title`
- `menu_items`

但是 `chart_page.html` 仍然使用這兩個變數。

Django template 遇到不存在的變數時，預設通常輸出空字串而不是直接報錯。因此 `/chart/` 可能會看到：

- 空白的 `<title>`。
- 空白的 `<h1>`。
- 沒有任何選單項目。

這不是前端 JavaScript 問題，而是 view 沒有準備 template 所需的 context。

另外，`index.html` 與 `chart_page.html` 目前幾乎完全相同。日後若直接複製修改，header、menu 或 HTML 結構很容易逐漸不一致。

## 6. 建議先建立的心智模型

把一個 Django 頁面拆成五層：

| 層 | 責任 | 常見檔案 |
|---|---|---|
| URL | 決定 request 交給哪個 view | `urls.py` |
| View | 接 request、呼叫 service、建立 context | `views.py` |
| Service / Query | 查 DB、計算、整理業務資料 | `services.py`、`selectors.py` |
| Template | 把 context 轉成 HTML 結構 | `templates/**/*.html` |
| JavaScript | 處理互動、呼叫 API、更新局部 DOM、畫圖 | `static/**/*.js` |

最重要的責任分界：

```text
View / Service 決定「資料是什麼」
Template 決定「頁面初始結構」
JavaScript 決定「頁面載入後如何互動」
CSS 決定「畫面長什麼樣子」
```

不要讓 JavaScript 負責農產品價格的業務計算，也不要讓 view 組合大量 HTML 字串。

## 7. 新版建議採用的整體流程

對目前的能力與專案階段，建議採用「Django template 為主，JSON API 漸進加入」。

### 7.1 第一次開啟圖表頁

```text
GET /chart/
  -> ChartPageView
  -> ChartQueryService 查詢選單、預設品項、日期
  -> View 建立 context
  -> chart_page.html render 初始頁面
  -> Browser 顯示查詢表單與空的圖表容器
```

### 7.2 JavaScript 載入圖表資料

```text
chart_page.html 載入 chart_page.js
  -> JS 讀取初始參數
  -> fetch("/api/charts/daily-price/?...")
  -> Django API view
  -> ChartQueryService 查詢與聚合資料
  -> JsonResponse
  -> JS 收到 JSON
  -> 圖表 library render
  -> 使用者看到圖表
```

這種做法的好處是：

- 一開始仍可使用熟悉的 Django template。
- 圖表資料使用 JSON，不必把整頁 HTML 重新下載。
- 後端資料整理可以單獨測試。
- 未來若更換圖表套件或前端框架，API 仍可保留。
- 比舊版的「HTML fragment + inline script」更容易追蹤。

## 8. Context 應該放什麼

適合放入 template context：

- 頁面標題。
- 導覽選單。
- 查詢表單的選項。
- 使用者權限。
- 預設日期。
- API URL。
- 少量初始顯示資料。

不建議直接塞入 context：

- 幾萬筆 `DailyTran`。
- 巨大的圖表 series。
- 未經明確序列化的 QuerySet。
- 需要 JavaScript 再猜測結構的複雜 Python object。
- 含敏感欄位的 model instance。

View 的 context 最好能一眼看懂：

```python
context.update(
    {
        "page_title": "每日價量查詢",
        "product_options": product_options,
        "default_start_date": default_start_date,
        "default_end_date": default_end_date,
        "chart_data_url": reverse("dashboard:daily_price_api"),
    }
)
```

其中 `product_options` 應由 service 或 selector 整理，而不是讓 template 做複雜 ORM 判斷。

## 9. Template 如何把資料交給 JavaScript

### 9.1 少量字串：使用 `data-*`

適合放 URL、ID、狀態：

```django
<div
    id="daily-price-chart"
    data-api-url="{{ chart_data_url }}"
    data-default-product-id="{{ default_product_id }}"
></div>
```

JavaScript：

```javascript
const chartElement = document.querySelector("#daily-price-chart");
const apiUrl = chartElement.dataset.apiUrl;
const productId = chartElement.dataset.defaultProductId;
```

### 9.2 結構化資料：使用 `json_script`

若要把 list 或 dict 安全交給 JS：

```django
{{ chart_config|json_script:"chart-config" }}
```

JavaScript：

```javascript
const chartConfig = JSON.parse(
    document.querySelector("#chart-config").textContent
);
```

這比以下方式安全且穩定：

```django
<script>
    const data = {{ chart_config|safe }};
</script>
```

不要因為資料看起來是 JSON 就隨意使用 `safe`；資料若含特殊字元或使用者輸入，可能造成格式錯誤或 XSS 風險。

### 9.3 大量或會變動的資料：使用 JSON endpoint

圖表 series 建議由 JS 使用 `fetch()` 取得：

```javascript
const response = await fetch(`${apiUrl}?product_id=${productId}`);

if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
}

const payload = await response.json();
```

API response 應維持固定 schema，例如：

```json
{
  "meta": {
    "product_id": 123,
    "product_name": "高麗菜",
    "price_unit": "元/公斤"
  },
  "series": [
    {
      "name": "平均價",
      "points": [
        {"date": "2026-06-23", "value": 35.2},
        {"date": "2026-06-24", "value": 36.1}
      ]
    }
  ]
}
```

JavaScript 只負責把這個 schema 轉成圖表套件需要的格式。

## 10. 一個 request 到圖表顯示的責任對照

```text
使用者選商品並按「查詢」
  |
  v
JavaScript 讀取 form 欄位
  |
  v
fetch() 送 GET request
  |
  v
urls.py 比對 API URL
  |
  v
API view 驗證 product_id / 日期
  |
  v
Service 查 DB 並聚合 DailyTran
  |
  v
API view 回 JsonResponse
  |
  v
JavaScript 檢查 HTTP status 並解析 JSON
  |
  v
JavaScript 呼叫 chart library
  |
  v
Chart library 修改 DOM / Canvas / SVG
  |
  v
瀏覽器重新繪製畫面
```

「網頁呈現」其實有兩個時間點：

1. Django template 產生初始 HTML。
2. JavaScript 收到 JSON 後，再更新圖表區域。

## 11. 建議的新版目錄

先維持簡單，不需要立刻導入 React、Vue 或龐大的前端工具鏈：

```text
apps/dashboard/
  urls.py
  views.py
  services.py
  selectors.py
  tests/
    test_views.py
    test_services.py
    test_api.py
  templates/dashboard/
    base.html
    index.html
    chart_page.html
    includes/
      sidebar.html
      chart_filters.html
  static/dashboard/
    css/
      dashboard.css
    js/
      chart_page.js

docs/
  dashboard_request_context_template_js_flow.md
```

檔案角色建議：

- `base.html`：共用 `<head>`、header、sidebar，以及 CSS / JS 載入位置。
- `index.html`：首頁自己的內容。
- `chart_page.html`：圖表頁的 form、loading、error 與 chart container。
- `includes/`：可重用、但仍屬於 server-rendered HTML 的小區塊。
- `selectors.py`：單純查詢資料。
- `services.py`：聚合、計算、組合 response DTO。
- `chart_page.js`：只處理圖表頁互動。

這只是建議結構，應在真正需要時再建立檔案，不必先建立一堆空模組。

## 12. 舊版哪些觀念值得保留

從 `legacy_docs/` 可看出舊版已經有清楚的使用者工作流程：

- 左側商品樹。
- Product Selector。
- Chart 1–5。
- Raw Data Table。
- Integration Table。
- 每日、節慶與近五年報表。

這些「功能與操作順序」值得保留。

舊版後端也已證明幾種資料服務是核心：

- 每日價量。
- 歷年比較。
- 月分布。
- 整合比較。
- 事件資料。

新版可以把它們重建為明確 service 與 JSON schema。

## 13. 舊版哪些實作不建議照搬

舊版主要流程是：

```text
AJAX request
  -> Django render HTML fragment
  -> 插入 DOM
  -> fragment 內的 inline script 執行
  -> 載入 Highcharts / DataTables helper
```

不建議新版照搬以下做法：

- Template 內放大量 inline JavaScript。
- 每次互動都重新下載一大段 HTML。
- JS 全域變數保存頁面狀態。
- 用 DOM attributes 當完整 state store。
- View 直接產生特定圖表套件才能使用的複雜資料。
- ORM QuerySet 直接塞進 Redis pickle。
- URL hash 與手動 DOM 注入取代正常路由。

新版建議保留 Django 的正常頁面路由，再讓圖表與動態表格使用 JSON API。

## 14. 適合目前能力的開發順序

### 階段一：先把純 Django 頁面做好

目標：

- 建立 `base.html`。
- 讓首頁與圖表頁共用 header / sidebar。
- 每個 view 都清楚提供 template 需要的 context。
- 使用 `{% url %}`，不要在 Python 或 template hard-code `"/chart/"`。

此階段不需要 JavaScript。

### 階段二：加入查詢表單

目標：

- 使用普通 HTML `<form method="get">`。
- View 從 `request.GET` 讀取商品與日期。
- Service 查詢資料。
- Template 先用 HTML table 顯示結果。

這一步很適合後端工程師，因為可以先確認查詢、驗證與資料正確性。

### 階段三：把同一份資料改成 JSON API

目標：

- 建立明確 API URL。
- 驗證 query parameters。
- Service 回傳穩定的 Python dict / DTO。
- View 用 `JsonResponse` 回傳。
- 為 response schema 寫測試。

### 階段四：加入最小 JavaScript

目標：

- 表單 submit 時用 `fetch()`。
- 顯示 loading。
- 成功時更新 table 或圖表。
- 失敗時顯示可讀錯誤。
- 不要先加入複雜 framework。

### 階段五：加入圖表套件

目標：

- JS 將 API schema 轉成 chart options。
- 將建立與更新 chart 的程式封裝成小函式。
- 保持 API 不依賴 Highcharts、Chart.js 或其他特定套件。

### 階段六：再做商品樹、Watchlist 與多圖表

等單一圖表頁流程穩定後，再擴充：

- Sidebar tree API。
- Watchlist。
- Chart tabs。
- Integration table。
- Event manager。

不要一開始就同時重建舊版所有 AJAX 層。

## 15. 每個頁面都應回答的問題

開發新頁面前，先寫下：

1. 頁面的 URL 是什麼？
2. 哪個 view 處理？
3. View 接受哪些 GET / POST 參數？
4. 哪個 service 負責業務邏輯？
5. Template 需要哪些 context keys？
6. 初始 HTML 有哪些 container？
7. 是否真的需要 JavaScript？
8. JS 會呼叫哪個 API？
9. API response schema 是什麼？
10. loading、空資料、錯誤狀態如何顯示？

如果這十題能回答，前後端流程通常就不會失控。

## 16. Debug 時從哪裡查

### 網址出現 404

依序檢查：

```text
config/urls.py
  -> app urls.py
  -> path 是否符合
  -> URL 尾端斜線是否一致
```

### Template 找不到

檢查：

- App 是否在 `INSTALLED_APPS`。
- `APP_DIRS` 是否為 `True`。
- 路徑是否符合 `templates/dashboard/...`。
- `template_name` 是否寫成 `dashboard/xxx.html`。

### 頁面有 HTML，但文字或選單是空的

檢查：

- View 是否真的把 key 放進 context。
- Template 的變數名稱是否拼對。
- 是否在另一個 view 重用了同一個 template，卻沒提供相同 context。

目前 `/chart/` 的 `title` 與 `menu_items` 就屬於這一類。

### JavaScript 沒執行

依序檢查：

- `<script src="...">` 是否真的載入。
- 瀏覽器 Network 是否 404。
- Console 是否有 syntax error。
- JS 執行時 DOM 是否已建立。
- Selector 是否找得到 element。

### Fetch 有送出，但畫面沒更新

依序檢查：

- Network request URL。
- HTTP status。
- Response 是否為預期 JSON。
- `response.ok` 是否檢查。
- JSON 欄位名稱是否與 JS 使用的一致。
- 圖表 container 是否存在且有尺寸。

## 17. 測試建議

後端工程師可以先守住最熟悉、也最有價值的部分：

- URL 是否對應正確 view。
- View response status 是否正確。
- Template 是否使用正確檔案。
- Context 是否包含必要 key。
- Service 聚合結果是否正確。
- API schema 是否穩定。
- 無效參數是否回傳 400。
- 無資料是否回傳空陣列，而不是不一致的格式。

前端初期至少人工確認：

- 頁面載入。
- 表單可以送出。
- loading 會結束。
- 成功資料會顯示。
- 空資料有提示。
- API 失敗有錯誤訊息。

## 18. 現階段最重要的下一步

依目前程式狀態，建議下一個實作順序是：

1. 建立共用 `base.html`，消除 `index.html` 與 `chart_page.html` 的重複。
2. 讓 `ChartPageView` 明確提供自己的 `title` 與頁面 context。
3. 把 menu URL 改成 Django named URL。
4. 先用普通 GET form 完成一條「選商品 → 後端查詢 → HTML table」流程。
5. 確認資料正確後，再把查詢抽成 JSON API。
6. 最後才加入 JavaScript 圖表。

對不熟前端的 Django 工程師來說，這條路線最容易觀察每一層，也最容易測試與除錯。

## 19. 一句話總結

新版可以把整體流程固定成：

```text
URL 接 request
  -> View 驗證輸入並呼叫 Service
  -> Service 整理業務資料
  -> Template 建立初始 HTML
  -> JavaScript 需要動態資料時呼叫 JSON API
  -> JavaScript 更新指定 DOM
  -> Browser 呈現最終畫面
```

先讓 Django 頁面與資料正確，再逐步增加 JavaScript；不要從舊版複製整套 HTML fragment 與 inline script 架構。
