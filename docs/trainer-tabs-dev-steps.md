# Trainer 选项卡重构 — 开发步骤

> 目标：UI 与 `characterStats` / `SpellAttributes` 分层一致；修复合并伤害读写不准。本文只列步骤，不含代码。

## 界面结构

```
顶部卡片：☑ 无敌  ☑ 超级攻击
下方 QTabWidget：
  Tab「基础」     — 角色全局属性 + 角色层咒语加成
  Tab「隐藏」     — 局内/商店向（见字段表）
  Tab「{咒语名}」— 按已装备咒语动态生成，每条咒语一页
```

## 字段归属

| Tab | stat key | 备注 |
|-----|----------|------|
| 基础 | max_health, health_regen, armor, dodge, movement_speed | |
| 基础 | critical_chance, critical_damage, pickup_radius, xp_gain, luck | |
| 基础 | char_spell_damage, char_spell_range, char_spell_fire_rate | **新建 key**，仅角色层 type 0/6/2 |
| 隐藏 | rerolls, bans→文案「替换」, pins→「锁定», revive_health_pct, gold_gain, revives, revive_speed | bans 只改 i18n |
| 咒语×N | spell_damage, spell_range, spell_fire_rate | 绑定该 Tab 对应 spell id，非合并值 |

**删除**：原合并 `panel_source='spell_damage'` 的单栏「伤害」。

---

## 步骤 1 — 后端：咒语枚举

1. 在 `spell_stats.py` 新增 `list_equipped_spells(mem, player_stats_ptr) -> list[SpellHandle]`（含稳定 spell key、display name、`stats_list_ptr`）。
2. 废弃「字典迭代取最后一个」的 `primary_spell_stat_ptr` 作为主路径；按 key 查指定咒语 stat。
3. `refresh_handles` / tick 时对比 spell 列表 hash，变化时通知 UI rebuild。

## 步骤 2 — 后端：读写拆分

1. `stats_meta.py`：拆 `CHARACTER_STATS` 为三组常量（`BASIC_STATS` / `HIDDEN_STATS` / 咒语 stat 模板）；角色层咒语三栏用新 key。
2. `stat_calc.py`：
   - 读：角色层 / 咒语层分别 `sum_modifiers`（或对齐游戏公式，见步骤 6）。
   - 写：删除「合并写入 + 清空角色 modifier」的 `write_spell_damage_panel_percent` 路径；每层独立 `write_modifier_sum_panel_value`。
3. `session.py`：`read_all_stats()` 返回 `{key: value}` + `spells: [{id, name, stats: {...}}]`；`write_stat(key, value, spell_id=None)`。

## 步骤 3 — ViewModel

1. `TrainerViewModel` 信号改为 `stats_updated(dict, list)` 或嵌套结构。
2. `apply_stat(key, value, spell_id=None)` 透传 session。
3. spell 列表变化时发 `spells_changed`（供 Panel rebuild Tab）。

## 步骤 4 — UI 骨架

1. `trainer_panel.py`：保留顶部 `header`（无敌 + 超级攻击）；下方 `stats_card` 内改为 `QTabWidget` + 每 Tab 内 `QScrollArea` + `QGridLayout`。
2. Tab「基础」「隐藏」：启动时静态创建 spinbox，key 绑定步骤 2 的 meta。
3. 咒语 Tab：收到 `spells_changed` 时 diff rebuild（同 id 复用 widget，避免闪跳；保留当前 Tab 索引或 spell id）。

## 步骤 5 — i18n

1. `zh-CN.json` / `en.json`：Tab 标题 `trainer.tab.basic` / `trainer.tab.hidden` / `trainer.tab.spell`（`{name}` 占位）。
2. 新增 `trainer.stat.char_spell_damage` 等三栏；`trainer.stat.bans` → 中文「替换」。
3. `ui/i18n.py`：Tab 与 stat 标签 helper。

## 步骤 6 — 数值对齐（可与步骤 2 并行验证）

1. 用 CLI `stats` + 游戏内面板对比 Tab1 角色层、咒语 Tab 各字段。
2. 确认 `HiddenStatModifier`、未知 modifier 类、calc_type 公式是否需纳入读写；偏差 ≤1 再定稿。
3. 超级攻击仍走现有 `apply_super_attack`（遍历所有咒语 damage stat），与 Tab 写入不冲突。

## 步骤 7 — 自测清单

- [ ] 仅 Tab「基础」改角色伤害，咒语 Tab 不变
- [ ] 仅某一咒语 Tab 改伤害，其他咒语与角色层不变
- [ ] 进局 / 获得新咒 / 丢咒后 Tab 数量与名称正确
- [ ] 800ms 刷新不丢焦点、不乱跳 Tab
- [ ] Enter 提交 / Esc 取消仍生效
- [ ] 无敌、超级攻击开关与改属性可同时用

## 建议提交顺序

1. 步骤 1 + 2（后端可单测 CLI）
2. 步骤 3
3. 步骤 4 + 5（UI 可见）
4. 步骤 6 微调
5. 步骤 7 通过后更新 `README.md` Trainer 说明（可选）
