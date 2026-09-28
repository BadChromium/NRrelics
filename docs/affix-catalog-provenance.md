# 词条类别元数据：来源与限制

`data/affix_catalog.json` 按精确词条 ID 将中文名称与社区整理的游戏参数关联，不按 ID 前缀或数字范围猜测类别。它是离线编辑辅助，不替代 OCR，也不是游戏合法组合的权威判定器。

## 来源与授权说明

- [ip1259/Elden-Ring-Nightreign-Legal-Relic-Generator 的 AttachEffectParam.csv](https://github.com/ip1259/Elden-Ring-Nightreign-Legal-Relic-Generator/blob/aee6cba271501f95633fb662a6736cd6de2bae54/AttachEffectParam.csv)：参数来源。该仓库附带 GPLv3 许可文本，引用的 CSV 和许可保留在 `docs/third-party/affix-parameters/`，供查阅来源及适用条款。
- [slavone/nighreign_relic_calculator 的解析实现](https://github.com/slavone/nighreign_relic_calculator/blob/3cc38a5cdfd37865e7888064251d156d5abd5825/parse_relics.mjs)：类别语义参考。其说明将共享 `compatibilityId` 的效果视为不能在同一遗物上共同出现。
- 中文名称与精确 ID 来自提供的 `普通.csv`、`深夜.csv`。描述性备注不作为可执行规则；全角标点只在元数据查找时规范化，不改变预设或 OCR 匹配文本。

## 覆盖范围

部分 ID 未能对应到来源参数，它们在目录中保留为未确认记录。参数快照不是对所有游戏版本、固定奖励或未实装词条的完整保证。无法确认的条目仍可手动分组，但不据此给出确定的同族或冲突结论。

## 三种不同概念

1. **必须组**是用户规则：组内满足任意一个词条，所有组都要满足。无需元数据也可手工设定。
2. **同族建议**基于共同的非负 `attachFilterParamId`，不是按 `+N` 后缀推断。只有用户明确操作才扩展候选，不自动放宽已有等级要求。
3. **冲突类别**基于相同的非负 `compatibilityId`，可能比同族宽得多，仅用于编辑提示。不能把同类别的不同增益都当成等价替代。

`exclusivityId` 仅保留为来源字段，不作缺乏依据的解释。

例如 `强化祷告`、`强化祷告＋１`、`强化祷告＋２` 的 ID 分别是 `6611300`、`6611301`、`6611302`，共享同族字段 `6611300` 和冲突类别 `100`。因此可明确建立 `["强化祷告+1", "强化祷告+2"]` 的 OR 组，但不能将类别 100 下其他攻击增益都加入祷告替代组。

只有两个组的每一种跨组候选组合都已确认冲突时，才提示组间冲突。共享候选可同时满足两个组；缺失或歧义元数据不能证明冲突。没有警告不代表该组合一定能在游戏中出现。此目录不用于重建正负词条的抽取配对关系。
