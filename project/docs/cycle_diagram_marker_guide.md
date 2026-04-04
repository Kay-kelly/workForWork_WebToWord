# Cycle Diagram Marker Guide

這份文件是給 `project/config/image_templates/cycle_diagram.json` 使用的簡短說明。

重點只有兩件事：

- 要改線時，該改哪一段 config
- 要加 marker 時，該直接用現有 anchor，還是先補新的 named anchor

## 1. 目前可用的 anchor 類型

目前 marker 可用的 `anchor` 有 3 種：

- `start`
  - 整條 path 的起點
  - 適合掛左側起始資訊

- `end`
  - 整條 path 的終點
  - 適合掛右側結束資訊

- `named_anchor`
  - 用 `anchor_ref` 指向 path 上已命名的幾何點
  - 適合掛在線上的特定位置，例如轉折點、高平台、低平台、尾段起點

### 什麼情況用 `start` / `end`

當你要掛的是左右兩端的固定資訊，而且不需要精準指定某個 block 內的幾何點時，用：

- `start`
- `end`

### 什麼情況用 `named_anchor`

當你要掛的是線上的特定位置，而且希望 marker 跟著 path 幾何穩定移動時，用：

- `anchor: "named_anchor"`
- `anchor_ref: "<anchor name>"`

不要用 `start + dx/dy` 或 `end + dx/dy` 去硬推一個其實屬於線上轉折點的位置。

## 2. 目前已可用的 named anchors

### 固定存在

這些 anchor 不管 `cycle_count` 是多少都存在：

- `path_start`
- `lead_kink`
- `lead_end`
- `outer_1_high`
- `outer_1_low`
- `outer_2_high`
- `outer_2_low`
- `tail_start`
- `path_end`

### 依 `cycle_count` 增加

中間的 inner anchors 會依 `cycle_count` 增加：

- `inner_1_high`
- `inner_1_low`
- `inner_2_high`
- `inner_2_low`
- `inner_3_high`
- `inner_3_low`
- ...

命名規則固定是：

- `inner_<index>_high`
- `inner_<index>_low`

外圈也維持 index 命名，不用 `last`：

- `outer_1_high`
- `outer_1_low`
- `outer_2_high`
- `outer_2_low`

## 3. marker config 最小範例

下面這個例子包含：

- 一顆掛在 `start`
- 一顆掛在 `lead_kink`
- 一顆掛在 `outer_2_low`

```json
{
  "markers": [
    {
      "marker_key": "info_start",
      "anchor": "start",
      "type": "filled_circle",
      "dx": 0,
      "dy": 0,
      "size": 20
    },
    {
      "marker_key": "info_lead_transition",
      "anchor": "named_anchor",
      "anchor_ref": "lead_kink",
      "type": "triangle_up",
      "dx": 0,
      "dy": 0,
      "size": 24
    },
    {
      "marker_key": "info_outer_low",
      "anchor": "named_anchor",
      "anchor_ref": "outer_2_low",
      "type": "hollow_circle",
      "dx": 0,
      "dy": 0,
      "size": 20
    }
  ]
}
```

## 4. 如果要改線，該改哪裡

這一段是之後最常回頭看的地方。

`cycle_diagram.json` 裡與 path 幾何最有關的設定都在 `path_builder`。

### `levels`

用途：

- 控制各個高低平台的垂直位置

目前常見欄位：

- `start`
- `end`
- `outer_high`
- `inner_high`
- `inner_low`
- `outer_low`

適合什麼情況改：

- 想調整 outer / inner 的高低差
- 想讓高平台更高、低平台更低
- 想讓整體折線節奏更像示意圖，而不是太平或太尖

### `left_lead_segments`

用途：

- 控制左側起始段的幾何形狀

適合什麼情況改：

- 想調整起始水平段長度
- 想調整進入第一個主上升段前的節奏
- 想把 `lead_kink` 附近的視覺做得更明確

### `outer_block`

用途：

- 控制第 1 個 cycle 與最後 1 個 cycle 的線型節奏

目前通常是：

- `rise`
- `hold`
- `fall`
- `hold`

適合什麼情況改：

- 想調整 outer block 的平台長度
- 想調整 outer block 上升 / 下降的水平距離
- 想讓第一段與最後一段看起來更像外圈循環

### `inner_block`

用途：

- 控制中間 cycles 的線型節奏

適合什麼情況改：

- 想調整 inner cycles 的平台長度
- 想讓中間 block 看起來更緊湊或更平穩
- 想微調 `cycle_count` 增加後的視覺節奏

### `right_tail_segments`

用途：

- 控制右側尾段怎麼從最後一個 cycle 收回到結束位置

適合什麼情況改：

- 想調整最後水平段前後的感覺
- 想讓右側回收段更像示意圖

### 改線時的實用判斷

你可以用這個簡單判斷：

- 想改高低差：先看 `levels`
- 想改左側起始節奏：看 `left_lead_segments`
- 想改第一段 / 最後一段節奏：看 `outer_block`
- 想改中間循環節奏：看 `inner_block`
- 想改右側收尾：看 `right_tail_segments`

## 5. 如果要在其他轉折點加 marker，該怎麼做

先判斷你要掛的位置，是不是已經有現成的 `named_anchor`。

### 情況 A：現有 `named_anchor` 已經夠用

例如你要掛在：

- `lead_kink`
- `outer_2_low`
- `inner_1_high`
- `tail_start`

那就直接在 `markers` 裡加：

```json
{
  "marker_key": "your_marker",
  "anchor": "named_anchor",
  "anchor_ref": "inner_1_high",
  "type": "filled_circle",
  "dx": 0,
  "dy": 0,
  "size": 20
}
```

### 情況 B：現有 anchor 不夠，需要新的轉折點

如果你要掛的是新的折點或新的 segment 端點，而目前清單裡沒有，建議做法是：

1. 先到 path builder 補一個新的 `named_anchor`
2. 再回 `cycle_diagram.json` 的 `markers` 掛上去

不要直接退回用手寫 pixel 座標去硬推位置。

### 建議命名規則

新 anchor 請沿用現在的命名方式：

- `outer_<index>_high`
- `outer_<index>_low`
- `inner_<index>_high`
- `inner_<index>_low`

如果之後要補更細的轉折點，建議用：

- `outer_1_rise_end`
- `outer_1_fall_end`
- `inner_2_rise_end`
- `inner_2_fall_end`
- `tail_start`

原則是：

- 用 block 類型 + index + 幾何語意
- 不要用 `last`
- 命名要能一眼看出它掛在哪一段

## 6. 後續擴充建議順序

先用最小方式往下長，不要直接做成通用 engine。

建議順序：

1. 先補 `named_anchors`
   - 優先補真正有需要掛 marker 的點

2. 再補更多轉折點
   - 例如 `rise_end`、`fall_end`
   - 先讓 marker 能穩定掛在更多線上幾何點

3. 最後才考慮更細的 anchor 模式
   - 例如更細的 segment 級 anchor
   - 或之後真的有需要再考慮 `path_index` 類型

目前最不建議的做法是：

- 一開始就做通用圖形引擎
- 用手寫 pixel 座標硬掛 marker
- 為了單一 case 加很多特殊邏輯

## 7. 實用提醒

- 要掛在線上的特定點：優先用 `named_anchor`
- 要改整體線型節奏：先看 `path_builder`
- 要改 marker 大小或相對間距：改 `markers` 內的 `size / dx / dy`
- 如果新的掛點名稱現在不存在：先補 `named_anchor`，再掛 marker
