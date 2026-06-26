# 舊 APSVP 系統整理：模型關係與資料服務

來源專案：`C:\Users\ai\Desktop\smithfu\repositories\agriculture\apsvp\apsvp`

## 1. 核心模型群

### configs app

檔案：`src/apps/configs/models.py`

| Model | 角色 | 重要關係 |
|---|---|---|
| `Config` | 商品大類，例如蔬菜、水果、豬、魚等 | M2M `charts` -> `Chart` |
| `AbstractProduct` | 商品樹基底，實際商品 app 都繼承它 | FK `config`、FK `type`、FK `unit`、FK self `parent` |
| `Source` | 資料來源 / 市場 / 產地來源 | M2M `configs`、FK `type` |
| `Type` | 交易類別，例如批發、產地等 | 被 product/source 參照 |
| `Unit` | 價格、數量、重量單位 | 被 product 參照 |
| `Chart` | 圖表定義 | `template_name` 決定 ChartContents template |
| `Month` | 監控月份 | 被 `MonitorProfile.months` 使用 |
| `Festival` | 某民國年 + 節慶名稱 | FK `FestivalName` |
| `FestivalName` | 節慶名稱與農曆月日 | 被 Festival / FestivalItems 使用 |
| `FestivalItems` | 節慶報表品項設定 | M2M `FestivalName`、`AbstractProduct`、`Source` |
| `Last5YearsItems` | 近五年月平均報表品項設定 | M2M `AbstractProduct`、`Source` |

`AbstractProduct` 是商品樹核心：

```text
Config
  -> AbstractProduct(parent=None)
      -> AbstractProduct(child)
          -> AbstractProduct(grand child / track item)
```

重要 method / property：

- `children(watchlist=None)`：取下一層商品，watchlist 模式會以 `watchlist.related_product_ids` 過濾。
- `children_all()`：取多層 descendant。
- `types(watchlist=None)`：依子商品或自身 type 取得可用類別。
- `sources(watchlist=None)`：watchlist 模式取 WatchlistItem 的 sources；非 watchlist 模式取 `Source`。
- `has_child`、`has_source`、`level`、`to_direct`：左側選單是否繼續展開或直接導向圖表。
- `related_product_ids`：自身、parents、children 的 id 集合，用於 watchlist 過濾。

### 商品子類別 apps

這些 model 幾乎都是空 subclass，目的在於用 multi-table inheritance 區分 domain，並讓 builder 用特定 model 查商品：

| App | Model | Config 概念 |
|---|---|---|
| `crops` | `Crop(AbstractProduct)` | 蔬菜 |
| `fruits` | `Fruit(AbstractProduct)` | 水果 |
| `flowers` | `Flower(AbstractProduct)` | 花卉 |
| `seafoods` | `Seafood(AbstractProduct)` | 水產 |
| `hogs` | `Hog(AbstractProduct)` | 豬 |
| `cattles` | `Cattle(AbstractProduct)` | 牛 |
| `rams` | `Ram(AbstractProduct)` | 羊 |
| `chickens` | `Chicken(AbstractProduct)` | 雞 |
| `ducks` | `Duck(AbstractProduct)` | 鴨 |
| `gooses` | `Goose(AbstractProduct)` | 鵝 |
| `rices` | `Rice(AbstractProduct)` | 米 |
| `feed` | `Feed(AbstractProduct)` | 飼料 |
| `naifchickens` | `Naifchickens(AbstractProduct)` | 畜產會雞類資料 |

多數子類別 model 的 `post_save` 會清掉 `AbstractProduct` 相關 cache。

## 2. Watchlist 模型群

檔案：`src/apps/watchlists/models.py`

| Model | 角色 | 重要關係 |
|---|---|---|
| `Watchlist` | 一組監看清單 / 期間 | FK `user` |
| `WatchlistItem` | Watchlist 裡的一個商品與來源集合 | FK `product`、M2M `sources`、FK `parent` -> Watchlist |
| `MonitorProfile` | 監控門檻、顏色、說明與月份 | FK `product`、FK `watchlist`、FK `type`、M2M `months` |

重要流程：

```text
Watchlist
  -> children() returns WatchlistItem queryset
  -> related_configs() returns Config ids from WatchlistItem.product.config
  -> related_product_ids returns watched products plus parents/children
```

`MonitorProfile` 主要用途：

- 左側選單 `contents/color-alert.html` 顯示警示色。
- Chart 1 / Chart 2 helper 讀 container 上的 `monitorProfiles`，在圖表中畫警示區間或提示。
- `product-profile.html` 顯示監控說明。
- 每日報表使用 `product_list()` 與 `sources()` 取得監控相關商品與來源。

## 3. 行情與報表模型

檔案：`src/apps/dailytrans/models.py`

| Model | 角色 | 重要關係 |
|---|---|---|
| `DailyTran` | 每日行情資料主表 | FK `product` -> `AbstractProduct`、FK `source` -> `Source` |
| `DailyReport` | 每日報表 Google Drive file id cache | date + file_id |
| `FestivalReport` | 節慶報表 Google Drive file id cache | FK `Festival`、file_id、file_volume_id |

`DailyTran` 欄位：

- price：`up_price`、`mid_price`、`low_price`、`avg_price`
- quantity：`volume`
- weight：`avg_weight`
- key：`product`、`source`、`date`
- update control：`not_updated`

`DailyTranQuerySet` 額外提供：

- `between_month_day_filter(start_date, end_date)`：跨年度依月日區間抓歷史同期資料。
- `filter_by_date_lte(days, products, sources)`：找小於等於指定日期的最近資料。

## 4. Chart aggregation service

檔案：`src/apps/dailytrans/utils.py`

主要 public functions：

| Function | 主要用途 | Chart |
|---|---|---|
| `get_query_set(_type, items, sources)` | 將 WatchlistItem 或 AbstractProduct 轉成 DailyTran queryset | 共用 |
| `get_group_by_date_query_set(query_set, start_date, end_date, specific_year)` | 依日期聚合，計算平均價、總量、平均重量 | 共用 |
| `get_daily_price_volume()` | 每日價量資料，高圖與 raw table | Chart 1 / 2 / 5 |
| `get_daily_price_by_year()` | 歷年每日價格對齊同一基準年 | Chart 3 |
| `get_monthly_price_distribution()` | 月別分布、分位數、平均 | Chart 4 |
| `get_integration()` | 本期、前期、五年同期、逐年整合比較 | Integration table |
| `to_unix()` / `to_date()` | JS timestamp 轉換 | 前後端共用 |

核心聚合邏輯：

```text
DailyTran queryset
  -> pandas DataFrame
  -> 若有 volume / avg_weight，使用加權平均
  -> group by date + source，再 group by date
  -> 輸出 highchart data 與 raw table data
```

平均價大意：

```text
avg_price = sum(avg_price * avg_weight_or_1 * volume_or_1)
            / sum(avg_weight_or_1 * volume_or_1)
```

如果資料多數沒有 volume，`sum_volume` 退化為來源數；如果多數沒有 weight，`avg_avg_weight` 退化為 1。

## 5. Event / Comment / Post 補充模型

事件：`src/apps/events/models.py`

- `EventType(TagTreeModel)`：樹狀事件類型。
- `Event`：FK user、content type、object id、date、name、context、M2M types。
- Chart 5 透過 content type + object id 查事件。

留言與 social wall：

- `src/apps/comments/models.py`：`Comment` 使用 GenericForeignKey。
- `src/apps/posts/models.py`：`Post` 社群牆。
- 主路由目前 `posts` / `comments` include 被註解，保留 API 與 template 但非主功能流。

帳號：`src/apps/accounts/models.py`

- `UserInformation` 是主畫面權限旗標來源，例如：
  - `watchlist_viewer`
  - `menu_viewer`
  - `monitor_info_viewer`
  - `festivalreport_viewer`
  - `last5yearsreport_viewer`
  - `amislist_viewer`
  - `reporter`

## 6. 匯入 builder 關係

排程入口：`src/dashboard/celery.py`

Task 命名：

| Task | App |
|---|---|
| `DailyCropBuilder` | `apps.crops.tasks` |
| `DailyFruitBuilder` | `apps.fruits.tasks` |
| `DailyFlowerBuilder` | `apps.flowers.tasks` |
| `DailyWholesaleSeafoodBuilder` | `apps.seafoods.tasks` |
| `DailyOriginSeafoodBuilder` | `apps.seafoods.tasks` |
| `DailyHogBuilder` | `apps.hogs.tasks` |
| `DailyCattleBuilder` | `apps.cattles.tasks` |
| `DailyRamBuilder` | `apps.rams.tasks` |
| `DailyChickenBuilder` | `apps.chickens.tasks` |
| `DailyDuckBuilder` | `apps.ducks.tasks` |
| `DailyGooseBuilder` | `apps.gooses.tasks` |
| `DailyRiceBuilder` | `apps.rices.tasks` |
| `DailyFeedBuilder` | `apps.feed.tasks` |
| `DailyNaifchickensBuilder` | `apps.naifchickens.tasks` |
| `DefaultWatchlistMonitorProfileUpdate` | `apps.watchlists.tasks` |
| `DeleteNotUpdatedTrans` | `apps.dailytrans.tasks` |
| `UpdateDailyReport` | `apps.dailytrans.tasks` |

常見 builder pattern：

```text
Task
  -> Builder(model=<domain model>)
  -> 讀 fixtures/<domain>/*.yaml 或固定來源設定
  -> 建 Api / WholeSaleApi / OriginApi / ScrapperApi
  -> api.request(date/start_date/end_date/...)
  -> api.load(response)
  -> DailyTran.objects.create / bulk_create / update / delete
```

`apps.dailytrans.builders.abstract.AbstractApi` 規定：

- class attributes：`API_NAME`、`ZFILL`、`SEP`、`ROC_FORMAT`
- instance setup：從 `settings.DAILYTRAN_BUILDER_API` 找 URL。
- `request()`、`hook()`、`load()` 由子類實作。
- `get()` 有最多 5 次 retry，每次失敗 sleep 15 秒並寫 log。

## 7. Fixtures 與初始資料

重要 fixtures：

- `src/fixtures/configs.yaml`：Config / Type / Source / Unit / Chart 等基礎設定。
- `src/fixtures/<domain>/...yaml`：各 domain 商品樹與來源。
- `src/fixtures/watchlists/*.yaml`、`mp-*.yaml`：不同年度或半年度 watchlist。
- `src/fixtures/festivals/*.yaml`：節慶、節慶名稱、節慶品項。
- `src/fixtures/last5years/last5yearsitems.yaml`：近五年報表選單。

新版若要從零重建，建議先把 fixtures 轉成明確 seed pipeline，順序大致是：

```text
Unit / Type / Chart
  -> Config
  -> Source
  -> AbstractProduct tree / subclass product tables
  -> Watchlist / WatchlistItem / MonitorProfile
  -> FestivalName / Festival / FestivalItems / Last5YearsItems
  -> DailyTran historical data import
```

## 8. 新版資料模型切分建議

舊系統最大耦合點：

- `AbstractProduct` 同時承擔商品樹、domain subclass、選單導航、source/type 推導。
- Watchlist filtering 與商品樹 method 混在 model instance method。
- Chart data service 回傳的是 template 直接吃的 dict，不是穩定 API schema。
- Redis cache 存 QuerySet pickle，跨版本與資料異動風險高。

新版可以考慮：

```text
ProductCatalogService
  - 商品樹查詢
  - type/source 查詢

WatchlistService
  - watchlist 可見商品與 source
  - monitor profile lookup

MarketDataService
  - DailyTran query
  - aggregation to stable DTO / JSON schema

ReportService
  - Excel / Google Drive / file cache
```

先保留 DB concept，但把「view extra_context function」改成 service + serializer，會比較容易測試與替換前端。
