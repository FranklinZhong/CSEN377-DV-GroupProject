
# MedInsight 完整 User Story（增强版）

基于你们当前的项目方向、课程要求以及数据架构，我把整个项目重新整理成了一个“完整产品级 User Story + UX 交互设计方案”。

这个版本不仅包含功能，还重点考虑：

* 用户第一次打开网站时的感受
* 医疗信息的认知负担
* “探索感”与“可信度”
* 动画与交互的节奏
* 用户对风险信息的焦虑控制
* 可视化叙事（visual storytelling）
* AI 模块如何真正提升体验，而不是只作为“噱头”

整体设计与你们项目文档中的：

* 透明人体统一隐喻
* 三层可视化结构
* 官方数据 + 用户数据双视角
* Overview → Zoom → Details 原则

完全一致。

---

# 一、项目核心定位（升级版）

## 产品一句话

> “MedInsight 让普通用户第一次真正‘看见’药物如何作用于人体。”

不是传统：

* 药品数据库
* 说明书网页
* 冷冰冰副作用列表

而是：

## 一个“人体级药物探索系统”

用户能：

* 看见药物作用在哪里
* 看见副作用如何演化
* 看见真实患者如何反馈
* 看见风险什么时候开始上升
* 理解“官方数据”和“用户感受”之间的差异

---

# 二、完整用户旅程（User Journey）

---

# 阶段 1：首页（Landing + Search Experience）

---

# User Story 1：

## 用户第一次进入网站，希望快速理解网站是做什么的

### 页面结构

顶部：

```text
MedInsight
See How Drugs Affect the Human Body
```

中央：

透明人体缓慢呼吸式 glow animation。

人体上：

* 心脏轻微闪烁
* 肺部有呼吸动态
* 神经系统有微弱电流感

（目的：让用户立刻理解“人体可视化”是核心）

背景：

* 深色医疗科技风
* 半透明网格
* 微粒漂浮

---

# 1.1 搜索模块（核心入口）

## 双模式搜索

```text
[A-Z Index Search]
[Keyword Search]
```

默认：

* keyword search 打开
* index search 可展开

这样符合现代用户习惯。

---

# 三、索引搜索 User Story（A-Z Search）

---

# User Story 2：

## 用户不知道药品完整拼写，希望通过首字母逐步缩小范围

---

## 1.1 Index Search UI

顶部：

```text
A B C D E F G ...
```

hover：

* 字母 glow
* 人体局部产生微弱扫描线效果

点击字母：

例如点击：

```text
M
```

页面展开：

```text
MA
ME
MI
MO
MU
MY
```

这是非常关键的 UX 提升。

因为：
用户通常只记得前几个字母。

---

# 1.1.1 一级索引

点击 `M`

右侧：

```text
Metformin
Morphine
Methotrexate
...
```

按字母排序显示。
支持 infinite scroll。

---

# 1.1.2 二级索引（增强 UX）

点击：

```text
ME
```

结果变成：

```text
Melatonin
Metformin
Methadone
Methotrexate
...
```

优势：

相比传统数据库：

✅ 搜索压力小
✅ 减少拼写错误
✅ 医疗名词容错性更高

---

# 1.1.3 Hover Preview（新增增强功能）

这是建议你们新增的。

hover 药品名时：

右侧透明人体立即出现：

* 主要作用区域 glow
* 风险等级颜色
* overall rating
* 热门副作用 tag

例如：

```text
Metformin
⭐ 4.1
Main System: Metabolic
Common Effects:
[Nausea] [Weight Loss]
```

用户不用点进去就能快速筛选。

这是非常高级的 UX。

---

# 四、关键词搜索 User Story

---

# User Story 3：

## 用户知道药品名，希望快速找到目标药品

---

# 1.2 Keyword Search

---

## 输入实时联想

用户输入：

```text
met
```

dropdown：

```text
Metformin
Metoprolol
Methotrexate
Metoclopramide
```

---

# 1.2.1 dropdown interaction

每个药品项：

左侧：

* 小型人体 icon

右侧：

* 药品名
* 用途
* 风险等级颜色

例如：

```text
Metformin
Diabetes Treatment
🟢 Low Severe Risk
```

---

# 1.2.2 模糊搜索（重点）

点击 Search 后：

系统执行：

* Levenshtein similarity
* prefix similarity
* sound similarity

因为医疗单词经常拼错。

例如：

输入：

```text
amoxcillin
```

仍返回：

```text
Amoxicillin
```

这是非常重要的人机友好性。

---

# 五、药品详情页（核心系统）

---

# 页面结构（重要）

建议采用：

```text
------------------------------------------------
Top Summary Bar
------------------------------------------------
Left Sidebar | Center Human Body | Right Insight
------------------------------------------------
Bottom Timeline + Review Expansion
------------------------------------------------
```

这是最适合医疗信息认知负担的结构。

---

# 六、顶部 Summary Bar（新增强烈推荐）

---

# User Story 4：

## 用户进入药品页面，希望 5 秒内理解药物概况

---

顶部固定栏：

```text
Metformin
FDA Approved
Type 2 Diabetes
Overall Rating: 4.1
Risk Level: Moderate
```

右侧：

```text
[Compare Drug]
[Save Snapshot]
[Export Report]
```

---

# 七、透明人体主界面（核心）

文档中的透明人体设计非常正确。

这里进一步升级 UX。

---

# User Story 5：

## 用户希望“看见”药物如何影响身体

---

# 2.2 默认状态

进入页面：

人体 slowly glow。

默认：

```text
Mixed Mode
```

即：

* 正面
* 负面
  一起显示。

绿色：
benefit

红色：
side effect

---

# 2.2.1 身体高亮层级

建议做：

## 三层 glow

### Level 1（轻微）

柔和轮廓。

### Level 2（中等）

半透明区域扩散。

### Level 3（严重）

动态脉冲。

这样用户会自然理解严重程度。

---

# 2.2.2 Hover Interaction（必须）

hover 肝脏：

右侧出现：

```text
Liver
Common Side Effects:
- Elevated liver enzymes
- Hepatic stress

Frequency:
23%
```

同时：

人体其他区域 dim。

增强 focus。

---

# 2.2.3 Click Interaction（重点）

点击身体部位：

右侧展开：

## “Insight Card”

包含：

### 官方解释

来自：
FDA Label API。

---

### 用户评论摘要

例如：

```text
“Many users reported stomach discomfort during first 2 weeks.”
```

---

### AI Simplified Explanation（新增）

这是强烈建议增加的。

因为普通用户看不懂医学术语。

例如：

```text
“Hepatobiliary disorder”
```

AI 转换：

```text
“This means the drug may affect liver function.”
```

这会极大提升 usability。

---

# 八、Effect Switch Bar（增强）

---

# User Story 6：

## 用户希望专注于某类影响

---

顶部：

```text
[All]
[Benefits]
[Side Effects]
[High Severity]
```

切换时：

人体采用：

* 平滑颜色过渡
* glow fading
* 非突兀动画

这样非常重要。

医疗 UI 最忌：
突然闪烁。

---

# 九、时间演化动画（核心创新点）

你们这个设计其实是整个项目最有 research value 的部分。

---

# User Story 7：

## 用户希望理解“风险是否正在恶化”

---

# 2.3 Timeline Animation

---

## 默认：

自动播放。

时间轴：

```text
2014 ---- 2016 ---- 2018 ---- 2020 ...
```

人体部位亮度变化。

---

# 2.3.1 新增：Narrative Mode（强烈推荐）

系统自动生成：

```text
“In 2019 Q3, cardiovascular reports increased rapidly.”
```

对应人体：
心脏闪烁。

这是 AI storytelling。

会让项目非常高级。

---

# 2.3.2 Signal Event（CUSUM）

文档已有。

建议增强：

时间轴上：

```text
⚠ Signal Spike
```

hover：

```text
Reports increased by 240% compared to previous quarter.
```

---

# 2.3.3 Side Effect Bubble（非常棒）

你们原方案很好。

进一步优化：

气泡：

* 不要同时出现太多
* 最多 3 个
* 自动聚类

否则会信息爆炸。

---

# 2.3.4 Timeline Scrubbing（重要）

拖动时间轴：

人体即时变化。

这是：
Overview → Detail 的核心。

---

# 十、患者评论 Isotype（项目亮点）

---

# User Story 8：

## 用户希望知道“真实患者到底怎么评价”

---

# 2.4 多人体 Isotype

---

## 展开动画

点击：

```text
Patient Experiences
```

底部 drawer 上滑展开。

避免页面跳转。

---

# 2.4.1 人体聚类设计

建议：

按身体系统聚类：

```text
Digestive
Nervous
Skin
Sleep
```

每个 cluster：

* 红/绿小人
* 数量真实映射比例

---

# 2.4.2 Hover UX

hover cluster：

左上角：

```text
Most Mentioned:
Stomach Pain
Fatigue
Nausea
```

---

# 2.4.3 评论卡片（新增推荐）

点击 cluster：

展开真实评论：

```text
“I had severe nausea for 3 days.”
```

并高亮：
对应身体部位。

这会让项目非常有“真实感”。

---

# 11. AI 增强模块（Detailed User Story）

这一部分的核心目标不只是“加 AI 功能”。

而是：

# 降低医疗信息理解门槛 + 提升探索感 + 增强可信度

否则用户会觉得：
“只是把数据换了个动画展示”。

AI 模块真正的价值应该是：

* 帮用户理解
* 帮用户比较
* 帮用户发现异常
* 帮用户减少认知负担

---

# 11.1 Drug Compare Mode（双药对比模式）

---

# User Story

## 用户场景

用户正在服用：

* Metformin

医生又推荐：

* Ozempic

用户希望：

> “两种药到底有什么区别？”
> “哪个副作用更严重？”
> “哪个更容易影响胃？”
> “真实用户更喜欢哪个？”

传统药品网站只能：

* 表格
* 说明书
* PDF

用户很难建立“人体层面的理解”。

---

# 用户操作流程

---

## Step 1：进入 Compare Mode

在药品详情页顶部：

```text id="p3b6k2"
[Compare Drug]
```

点击后：

页面 smooth transition。

中央人体向左移动。

右侧出现：

```text id="m4rx1e"
Search another drug...
```

---

## Step 2：搜索第二种药物

用户输入：

```text id="m4r7cc"
oze
```

dropdown：

```text id="cl1d2k"
Ozempic
Ozurdex
...
```

点击：
Ozempic。

---

## Step 3：双人体同步展示

页面变成：

```text id="t3o6z1"
Metformin          Ozempic
[Human]            [Human]
```

两个人体：

* 同步旋转
* 同步时间轴
* 同步交互

用户可以：

### hover 同一部位

例如 hover 胃部：

左边：

```text id="l7k2az"
Metformin
Nausea: 24%
```

右边：

```text id="f8d2mw"
Ozempic
Nausea: 41%
```

系统自动：

* 数值比较
* 风险颜色变化
* 生成差异摘要

---

# AI Summary Card（核心）

人体中央自动生成：

```text id="h2mz0v"
AI Comparison Summary

Ozempic shows stronger appetite suppression
but higher gastrointestinal side effects.

Metformin has longer-term safety stability.
```

这是整个 Compare Mode 的核心。

因为用户：
不是来看“数字”。

而是来看：

# “差异 insight”

---

# 用户感受设计（UX）

---

## 用户不会感到“医学压力”

因为：

不是：

* 冷冰冰表格

而是：

* 身体层级对比

这会让用户感觉：

> “我真的理解了差异。”

---

## 微交互设计

### 当某个副作用明显更高时：

人体对应部位：

* pulse 一次
* 出现 warning ring

例如：

```text id="a2g1xr"
⚠ Higher nausea reports
```

---

# 可扩展功能（高级）

---

## Compare Timeline

两个时间轴同步播放：

```text id="yb81fa"
2014 → 2025
```

用户能看到：

某个药物副作用是否：

* 突然增长
* 长期稳定
* 存在 signal spike

---

## Compare Reviews

底部 isotype：

左右对比：

```text id="g2x8da"
Positive Reviews
█████████

Negative Reviews
███
```

帮助用户快速建立：

真实患者 perception。

---

# UX 目标总结

Compare Mode 解决的是：

## 用户真实问题：

```text id="uy1w3z"
“哪种药更适合我？”
```

虽然系统不能直接给医疗建议，

但它能：

# 提供“可理解的比较认知”

这是巨大价值。

---

# 11.2 Explain Like I’m Not a Doctor（AI 通俗化解释）

---

# User Story

## 用户场景

普通用户看到：

```text id="h2d9lm"
Hepatobiliary disorder
```

会产生：

* 不理解
* 焦虑
* 放弃阅读

这是所有医疗网站最大的问题。

---

# 用户目标

用户希望：

> “用正常人能看懂的话解释。”

---

# 用户操作流程

---

## Step 1：点击 Simplify

医学术语旁边：

```text id="m3k1xs"
[Simplify]
```

---

## Step 2：AI 转换解释

展开：

```text id="t4y8va"
This means the drug may affect liver function
and could cause fatigue or abnormal liver tests.
```

---

# 多层级解释（重点）

这是强烈推荐增加的 UX。

---

## Level 1：一句话解释

适合普通用户。

---

## Level 2：为什么发生

用户点击：

```text id="e8d3km"
Why does this happen?
```

展开：

```text id="d9f2bx"
The liver helps process drugs.
Some medications increase stress on liver cells.
```

---

## Level 3：严重程度

AI 自动生成：

```text id="q3d1hf"
Usually mild and temporary.
Seek medical attention if symptoms persist.
```

---

# AI Tone Design（非常重要）

医疗 AI 最大问题：

## 要避免：

* 吓人
* 绝对化
* 误诊感

因此语气必须：

### 使用：

* “may”
* “can”
* “reported in some cases”

### 避免：

* “will damage”
* “dangerous”
* “severe” （除非数据支持）

---

# Hover Explain（高级 UX）

用户 hover label：

```text id="f1k8pz"
tachycardia
```

tooltip：

```text id="x8r2na"
Fast heart rate
```

不需要点击。

减少认知中断。

---

# AI Contextual Explanation（高级）

AI 根据：

* 当前高亮身体部位
* 当前时间节点
* 当前 side effect

动态生成 contextual explanation。

例如：

用户正在查看：

```text id="v7z2ox"
Heart
```

时间轴：

```text id="j8c3nm"
2021 Q2
```

AI：

```text id="r2w4qa"
Cardiovascular reports increased during this period,
especially among elderly patients.
```

这会让系统具有：

# “医疗叙事感”

而不只是 dashboard。

---

# UX 目标总结

这个模块解决的是：

# “医学信息不可理解”

问题。

也是整个产品：

最影响 usability 的模块之一。

---

# 11.3 Risk Radar（风险感知系统）

---

# User Story

## 用户场景

用户进入药品页面后，

面对：

* 人体图
* timeline
* labels
* reviews

可能会：

# 信息过载（information overload）

用户真正想知道的是：

```text id="r4v1pa"
“所以这个药总体危险吗？”
```

---

# 风险雷达的目标

用：

# 一眼能理解的风险概览

降低用户认知负担。

---

# 页面位置

透明人体右上方：

```text id="d7k2xm"
Risk Overview
```

---

# 雷达结构

采用：

## 五维风险模型

```text id="r5m8va"
Cardiovascular
Neurological
Digestive
Psychological
Long-term Safety
```

形成 radar chart。

---

# 动态联动（重点）

hover：

```text id="e2s9xa"
Digestive Risk
```

人体：

* 胃部 glow
* 肠道 highlight

右侧：

```text id="z3v7pn"
Most Reported:
Nausea
Vomiting
Loss of appetite
```

形成：

# Visualization linkage

这是高级可视化的重要原则。

---

# 风险等级表达（重点）

不要只用颜色。

因为：

* 色盲问题
* 医疗恐慌问题

因此：

## 多模态表达

| 等级       | 表现              |
| -------- | --------------- |
| Low      | 柔和圆角            |
| Moderate | 轻微 pulse        |
| High     | 波纹扩散            |
| Critical | warning outline |

---

# Confidence Indicator（非常重要）

医疗系统必须避免：

# “绝对确定性幻觉”

因此每个风险旁边：

```text id="u2n8xa"
Confidence: Medium
Based on 183 reports
```

用户知道：

* 数据量多少
* 可信度如何

---

# AI Risk Summary

AI 自动生成：

```text id="p7w2ms"
Most adverse reports are digestive-related
and typically occur during early treatment stages.
```

这是整个 Radar 的核心。

用户不需要自己读图。

---

# Timeline 联动（高级）

用户拖动时间轴后：

Radar 实时变化。

例如：

```text id="x4n9zt"
2017 → Low
2021 → Moderate Spike
```

用户能感知：

# 风险演化

而不是静态结果。

---

# UX 目标总结

Risk Radar 解决的是：

# “用户无法快速建立全局认知”

的问题。

它相当于：

整个系统的信息导航器。

---

# 12. Error Handling & Empty States（错误处理与空状态体验）

---

# User Story

## 用户场景

医疗系统中：

用户经常：

* 拼错药名
* 搜索不存在的药
* 输入俗称
* 输入缩写

如果系统只显示：

```text id="j7f2mz"
No Results
```

用户会：

* 挫败
* 怀疑系统
* 放弃使用

---

# 12.1 智能拼写纠错

---

## 用户输入

```text id="e9c2mq"
amoxcillin
```

系统：

```text id="s1x3pf"
Did you mean:
Amoxicillin?
```

同时：

透明人体出现：

扫描动画。

表示：

系统正在“搜索人体数据库”。

增强科技感。

---

# 12.2 模糊结果推荐

如果不存在完全匹配：

系统显示：

```text id="r6k3na"
Similar medications:
```

例如：

```text id="v8m1op"
Amoxicillin
Ampicillin
Azithromycin
```

---

# 12.3 无数据情况（重要）

某些副作用数据不足时：

不要：

```text id="j4n8ys"
No data
```

而是：

```text id="x3v1da"
Insufficient reporting data for this period.
```

同时：

人体区域显示：

低透明度灰色。

而不是空白。

避免 UI “坏掉”的感觉。

---

# 12.4 Timeline 空状态

如果某个年份缺失：

timeline 不中断。

而是：

柔和 fade。

hover：

```text id="o2k7zy"
Reporting volume too low for reliable analysis.
```

---

# 12.5 网络加载体验（高级）

人体先显示：

```text id="v5d8sa"
Scanning biological impact...
```

然后逐步：

* 身体轮廓出现
* 器官 glow
* labels 浮现

用户会觉得：

# 系统在“分析药物”

而不是：

页面卡顿。

---

# 12.6 AI 无法解释时

如果 AI confidence 太低：

不要胡编。

显示：

```text id="y9f1ma"
AI explanation unavailable due to limited evidence.
```

这是医疗 AI 非常重要的可信度设计。

---

# UX 目标总结

Error Handling 的核心：

不是“提示错误”。

而是：

# 维持用户探索流程不中断

这是高级 UX 的关键。

---

# 13. Accessibility & Inclusive Design（无障碍与包容性设计）

---

# User Story

## 用户场景

医疗信息：

本身认知压力就很高。

如果：

* 动画太强
* 颜色太复杂
* 文字太专业

很多用户会：

# 无法持续使用

特别是：

* 老年用户
* 色盲用户
* 焦虑用户
* 低医学背景用户

---

# 13.1 Color Blind Support

---

## 用户问题

当前设计：

* 红 = 副作用
* 绿 = 正面作用

但：

红绿色盲用户无法区分。

---

# 解决方案

除了颜色：

增加：

## Pattern Encoding

| 类型       | Pattern  |
| -------- | -------- |
| Positive | 柔和波纹     |
| Negative | 锯齿纹理     |
| Severe   | 高频 pulse |

这样：

即使看不到颜色，

仍然能区分。

---

# 13.2 Reduce Motion Mode

---

# User Story

部分用户：

* 对动态敏感
* 容易眩晕
* 医疗焦虑

不适合：

大量 glow + pulse。

---

# 用户操作

右上角：

```text id="f2z9qa"
Accessibility
```

打开：

```text id="m1d8wk"
[Reduce Motion]
```

---

# 效果

关闭：

* 自动播放
* pulse
* 浮动气泡
* 呼吸动画

人体变成：

静态柔和高亮。

---

# 13.3 Reading Mode（新增推荐）

---

# User Story

部分用户：

不喜欢复杂可视化。

更喜欢：

# 文本化阅读

---

# 用户点击

```text id="r4n2ya"
Reading Mode
```

页面切换为：

```text id="q9w8pz"
Drug Summary
Side Effects
Timeline Summary
Patient Reviews
```

类似：

Apple Health Report 风格。

---

# 13.4 字体与布局可调节

---

# 用户需求

老年用户：

希望：

* 字更大
* 对比更强

---

# 设置项

```text id="x6m2oa"
Text Size
Contrast
Spacing
```

---

# 13.5 Screen Reader Support

---

# 用户场景

视觉障碍用户：

使用 screen reader。

---

# 系统设计

hover 身体部位时：

自动生成：

```text id="d7f3mv"
Liver highlighted.
Reported adverse effects include elevated liver enzymes.
```

支持辅助阅读。

---

# 13.6 Emotion-sensitive Design（高级）

这是医疗系统非常容易忽视的。

---

# 用户问题

如果：

* 红色太多
* warning 太强
* 风险太突出

用户可能：

# 医疗焦虑上升

---

# 设计原则

系统避免：

* 血红色
* 闪烁警报
* 恐怖词汇

采用：

* 柔和暖红
* 半透明 glow
* 中性描述

例如：

不用：

```text id="q1x7dc"
DANGEROUS
```

而用：

```text id="n8k2fz"
Elevated reporting frequency observed
```

---

# 13.7 Cognitive Load Control（高级 UX）

系统不会：

一次展示所有数据。

而是：

# Progressive Disclosure

用户：

* hover → 简略
* click → 展开
* advanced mode → 深层数据

减少认知疲劳。

---

# UX 目标总结

Accessibility 的核心不是：

# “满足规范”

而是：

# 让不同认知能力的人都能理解医疗信息

这是 MedInsight 非常重要的产品价值。

# 14 测试过程中可能出现的数据问题和解决方案。

下面是你们 **user story 中最可能出现的数据问题 → 前端/后端解决方案**。

---

## 14.1 搜索页：药品不存在 / 拼写错误

### 问题

用户输入：

```txt
metformn
amoxcillin
ozempick
```

可能查不到精确药品名。

### 解决方案

前端不要直接显示：

```txt
No result
```

而是显示：

```txt
没有找到完全匹配结果。
你是否想搜索：
[Metformin] [Amoxicillin] [Ozempic]
```

后端做：

```txt
prefix search + fuzzy search + alias mapping
```

前端状态：

```txt
Searching...
↓
No exact match, showing similar drugs
```

---

## 14.2 A-Z 索引：某个字母下没有药品

### 问题

点击 `X`、`Q`、`Z` 可能结果很少或为空。

### 解决方案

显示空状态，但不要让页面看起来坏掉：

```txt
No drugs found under "X".
Try keyword search instead.
```

同时推荐热门药物：

```txt
Popular searches:
[Metformin] [Ibuprofen] [Aspirin]
```

---

## 14.3 药品详情页：FDA Label API 没有 indications_and_usage

### 问题

FDA Label API 可能返回：

```txt
无该药
字段缺失
indications_and_usage 为空
API 格式变化
```

你们的好处模式依赖 FDA Drug Label API 的 `indications_and_usage` 字段。

### 解决方案

前端：

```txt
Official benefit information is currently unavailable.
Showing side effect and patient review data instead.
```

人体好处模式按钮置灰：

```txt
[Benefits unavailable]
```

后端：

```txt
try FDA API
↓ fail
read cached result
↓ fail
return empty but valid JSON
```

不要让前端收到 500 后整页崩掉。

---

## 14.4 FAERS 数据：某药没有副作用报告

### 问题

某些小众药物在 FAERS 中可能报告数量很少。

### 解决方案

人体副作用图不要全空白，可以显示：

```txt
No sufficient FAERS reports found for this drug.
This does not mean the drug has no side effects.
```

同时显示 confidence：

```txt
Data confidence: Low
Based on 3 reports
```

这是医疗项目里很重要，避免误导用户。

---

## 14.5 FAERS 时间轴：某些季度缺失

### 问题

你们 timeline 使用 FAERS 2014 至今季度数据。
实际数据可能出现：

```txt
2018Q1 有数据
2018Q2 缺失
2018Q3 有数据
```

### 解决方案

后端补齐季度：

```json
{
  "quarter": "2018Q2",
  "report_count": 0,
  "missing": true
}
```

前端时间轴显示灰色断点：

```txt
2018 Q2: No data available
```

不要直接跳过，否则动画会误导用户，以为趋势连续。

---

## 14.6 FAERS 数据量太大导致查询慢

### 问题

如果前端一次请求完整 FAERS 原始数据，会非常慢。

### 解决方案

不要返回 raw records。

后端提前聚合成：

```json
{
  "drug": "Metformin",
  "timeline": [
    {
      "quarter": "2020Q1",
      "bodyPart": "stomach",
      "frequency": 0.72
    }
  ]
}
```

前端只拿聚合结果。

API 应该是：

```txt
GET /api/drugs/{id}/timeline
```

而不是：

```txt
GET /api/faers/raw
```

---

## 14.7 WebMD 评论：评论文本为空 / rating 缺失

### 问题

WebMD 评论可能有：

```txt
review_text 为空
rating 为空
age 缺失
sex 缺失
日期格式不统一
```

调研报告也提到需要去除空值、异常评分、统一日期格式。

### 解决方案

pipeline 阶段处理：

```txt
空 review_text → 丢弃
rating 缺失 → 不用于 overall rating
age/sex 缺失 → 标为 unknown
date 错误 → 标为 invalid_date
```

前端显示：

```txt
Demographic data incomplete.
Showing available review summaries only.
```

---

## 14.8 NLP 提取不到身体部位

### 问题

spaCy / NER 可能无法从评论中识别身体部位。

例如：

```txt
"I felt weird after taking it."
```

没有明确身体部位。

### 解决方案

不要强行映射到人体。

存入：

```txt
bodyPart: "unknown"
```

前端在 isotype 中增加：

```txt
General / Unspecified
```

避免错误地高亮某个器官。

---

## 14.9 情感分析误判

### 问题

VADER 对医学评论可能误判。

例如：

```txt
"The pain was gone, but nausea was terrible."
```

既有正面也有负面。

### 解决方案

不要只用 positive / negative 二分类。

增加：

```txt
positive
negative
mixed
neutral
```

前端显示：

```txt
Mixed experience
```

isotype 中可以用第三类灰色小人。

---

## 14.10 FDA / SNOMED 外部 API 连接失败

### 问题

外部 API 可能挂掉或限流。

### 解决方案

前端显示：

```txt
External medical terminology service is temporarily unavailable.
Core visualization is still available.
```

后端做缓存：

```txt
drug_label_cache
snomed_cache
ai_explanation_cache
```

缓存命中时不重新请求 API。

---

## 14.12 Timeline 动画数据过密

### 问题

如果某季度 side effects 太多，气泡会同时出现几十个，用户看不清。

### 解决方案

前端限制：

```txt
每秒最多显示 3 个 bubble
只显示 top 5 side effects
其余归入 "+12 more"
```

hover 后再展开详情。

---

## 14.13 数据源之间药品名不一致

### 问题

同一种药可能有不同名字：

```txt
Metformin
Metformin HCL
Glucophage
metformin hydrochloride
```

FAERS、WebMD、FDA Label API 可能不一致。

### 解决方案

建立标准药品表：

```txt
drug_id
generic_name
brand_names
aliases
```

前端只使用统一 `drug_id`。

用户看到：

```txt
Metformin
Also known as: Glucophage, Metformin HCL
```

---

## 14.14 官方数据和用户评论矛盾

### 问题

FAERS 显示某副作用报告频繁，但 WebMD 评论不明显，或者反过来。

### 解决方案

不要强行统一结论。

前端显示：

```txt
Official reports and patient reviews show different patterns.
```

并分开标注：

```txt
Official FAERS signal
Patient-reported concern
```

这反而是你们项目的 insight。

---

## 14.15 整页加载失败

### 问题

如果某个 API 失败，不能整页白屏。

### 解决方案

前端采用模块级 loading：

```txt
Summary Bar       loaded
Human Body        loaded
Timeline          failed
Reviews           loading
AI Explanation    unavailable
```

每个模块独立失败，互不影响。

---

## 推荐前端状态设计

每个模块都应该有 5 种状态：

```txt
loading
success
empty
error
partial
```

例如 timeline：

```txt
Loading timeline...
No timeline data available.
Failed to load timeline. Retry.
Partial data available.
```

---

## 最推荐你们写进 user story 的一句话

```txt
当某一数据源缺失或 API 请求失败时，系统不应中断用户探索流程，而应降级显示其他可用数据源，并明确标注数据缺失原因与可信度。
```

---

## 最终建议

你们的数据问题主要不是“有没有数据”，而是：

```txt
数据不完整
数据源不一致
外部 API 不稳定
数据量太大
AI 输出不确定
```

所以系统设计重点是：

```txt
后端聚合、缓存、标准化
前端模块级 loading/error/empty 状态
所有医疗结论显示 confidence
```

这样即使 FDA API 挂了、某药 WebMD 评论少、FAERS 某季度缺失，用户仍然能继续使用系统，而不是看到一个坏掉的页面。
