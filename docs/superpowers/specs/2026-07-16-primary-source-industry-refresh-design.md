# 分析前一手行业数据刷新设计

## 目标

每次执行 `stock-memory-analyzer` 的正式分析前，先使用可访问的一手资料刷新 GPU 规格、GPU 出货量、GPU 型号占比、NVIDIA 数据中心 Compute 营收和 HBM 供给参数。只有刷新结果通过来源与完整性校验，或用户明确授权使用旧快照时，才打开本机 `panda_data` 登录窗口并生成报告。

该流程解决两个现有问题：分析入口只检查本地时间戳而不更新行业数据，以及 `gpu_hbm_specs` 顶层时间戳与子模块时间戳不同步导致的新鲜度误报。

## 边界

- 行情、财务、估值和公开申报衍生数据继续由 `panda_data` 获取。
- 行业刷新在请求 `panda_data` 凭据前完成，不读取、不保存也不传递账号或密码。
- GPU 规格与 NVIDIA 营收可作为一手披露事实；GPU 出货量、型号占比和 HBM 供给参数若官方未直接披露，只能作为以一手事实为锚点的模型估算。无法从一手披露获得的 ASP、良率或产能分配等输入必须明确标为模型假设并降低置信度，不能伪装成来源事实。
- 不使用二手媒体、聚合网站或无出处数字替代一手资料。
- 不在 Python 内维护脆弱的网页爬虫。Skill 负责通过可用的联网工具读取官方页面和文件，本地代码负责验证、保存快照和执行门禁。
- 本次改动不扩展支持股票范围，也不改变投资研究边界。

## 一手来源定义

一手来源必须由相关公司或监管机构直接发布，且可访问、可定位到具体页面或文件。例如：

- NVIDIA 官方产品页、产品数据表、季度财报、投资者演示和 SEC 文件；
- Micron 官方财报、投资者演示、技术或产品资料和 SEC 文件；
- 分析其他已支持公司时，可使用该公司官方 IR 或 SEC 文件补充与其直接相关的披露。

每条来源记录以下字段：

| 字段 | 要求 |
| --- | --- |
| `publisher` | 发布公司或监管机构 |
| `title` | 页面、数据表或文件标题 |
| `url` | 可访问的一手来源 URL |
| `region` | 来源入口区域，例如 `global`、`cn`、`asia` 或 `regulatory` |
| `language` | 页面或文件的主要语言 |
| `published_at` | 发布日期；官方未显示时记录 `null` 并说明 |
| `as_of` | 数据所代表的截至日期或报告期 |
| `accessed_at` | 本次分析访问日期 |
| `verified_at` | 本次分析实际复核内容并确认仍有效的日期时间 |
| `evidence` | 支撑数据的简短释义，不复制长段原文 |

URL 的主机必须符合内置的一手来源允许列表。重定向后的最终 URL 也要重新校验，防止用看似官方的入口跳转到第三方页面。

## 多区域官方来源与可用性

“国内外都可以获取”采用同一发布方的多区域官方入口和监管披露冗余，不使用国内或海外第三方转载替代原文。区域入口解决网络可达性，不能改变来源级别，也不能因为更容易访问就覆盖更新的官方披露。

| 数据模块 | 全球或监管入口 | 中国或亚洲入口 | 使用方式 |
| --- | --- | --- | --- |
| `gpu_specs` | NVIDIA 全球产品页、官方技术文档与数据表 | NVIDIA 中国数据中心、Hopper 架构与开发者页面 | 以能定位到具体型号、HBM 类型、容量和带宽的最新官方资料为准；中国页字段不全时使用全球技术文档补齐 |
| `nvda_compute_revenue` | NVIDIA IR 季度业绩、年报及 SEC 10-Q/10-K | NVIDIA 中国官网不作为财务披露主源 | 公司 IR 与 SEC 报告期交叉核验；SEC 不可达时保留公司 IR 单一来源状态，不使用媒体转述 |
| `gpu_shipments`、`gpu_mix` | NVIDIA IR、SEC 文件、官方产品发布和平台量产说明 | NVIDIA 中国官方产品与技术页面 | 只把官方披露当作估算输入，结合明确的 ASP、产品周期和型号占比假设输出区间与敏感性，不声称官方披露了精确出货量 |
| `hbm_supply` | Micron IR、SK hynix 官方新闻中心、Samsung 全球新闻中心与 IR、TSMC IR | Micron 中国、SK hynix 中国、TSMC 简体中文官网与 IR | 汇总各供应商和先进封装官方披露作为估算锚点；未披露的位元供给、良率和客户分配输出区间，不包装成事实 |

首批来源目录使用以下官方入口；具体季度或产品文档 URL 由每轮联网检索在这些官方入口内发现并写入快照：

- NVIDIA 全球产品与技术资料：<https://www.nvidia.com/en-us/data-center/h100/>、<https://www.nvidia.com/en-us/data-center/h200/>、<https://docs.nvidia.com/enterprise-reference-architectures/hgx-ai-factory/latest/components.html>；
- NVIDIA 中国产品与技术入口：<https://www.nvidia.cn/data-center/>、<https://www.nvidia.cn/data-center/products/>、<https://www.nvidia.cn/data-center/resources/>、<https://www.nvidia.cn/data-center/technologies/hopper-architecture/>、<https://developer.nvidia.cn/cuda/gpus>；
- NVIDIA 财务披露：<https://investor.nvidia.com/financial-info/annual-reports-and-proxies/default.aspx> 及当前最新季度业绩；监管交叉核验使用 <https://www.sec.gov/edgar/browse/?CIK=1045810&owner=exclude>；
- Micron 全球与中国入口：<https://investors.micron.com/quarterly-results>、<https://www.micron.cn/in-china> 及 Micron 中国官方 HBM 产品资料；
- SK hynix 全球与中国入口：<https://news.skhynix.com/>、<https://www.skhynix.com.cn/>；
- Samsung 半导体新闻与财务披露：<https://news.samsung.com/global/category/products/semiconductors>、<https://www.samsung.com/global/ir/financial-information/earnings-release/>；
- TSMC 全球、简体中文与投资者入口：<https://www.tsmc.com/schinese>、<https://investor.tsmc.com/schinese> 及 <https://investor.tsmc.com/english>。

初始允许域名如下，后续增加来源必须经过代码和设计评审：

- NVIDIA：`nvidia.com`、`nvidia.cn`、`docs.nvidia.com`、`developer.nvidia.com`、`developer.nvidia.cn`、`investor.nvidia.com`、`nvidianews.nvidia.com`；
- 美国监管：`sec.gov`、`data.sec.gov`；
- Micron：`micron.com`、`micron.cn`、`investors.micron.com`；
- SK hynix：`skhynix.com`、`skhynix.com.cn`、`news.skhynix.com`；
- Samsung：`samsung.com`、`news.samsung.com`；
- TSMC：`tsmc.com`、`investor.tsmc.com`、`pr.tsmc.com`。

域名匹配必须满足 `host == allowed_domain` 或 `host.endswith("." + allowed_domain)`，禁止用字符串包含关系匹配。联网工具和本地校验器都要复核最终重定向 URL。流程不要求用户配置 VPN、代理或其他绕过措施；某个区域入口不可达时改试同一发布方的其他官方入口，全部不可达才进入刷新失败流程。

### 获取、选择与冲突规则

1. 每个候选来源在目录中声明发布方、模块、区域、语言、官方索引页或文档 URL 和优先级。
2. 每次分析都实际访问可用的中国/亚洲入口、全球入口或监管入口，收集可达候选；不得仅复用上次“已访问”的标记。
3. 按 `as_of` 或财务报告期选择最新数据；相同报告期再按 `published_at` 和来源权威层级选择。不得按搜索结果排序、响应先后或语言判断新旧。
4. 可获得两份一手资料时执行交叉核验，例如 NVIDIA IR 与 SEC；产品规格只有一份官方数据表时允许以单一来源通过，但快照要标记 `single_source`。
5. 区域镜像内容冲突时，以全球产品数据表、公司 IR 或监管文件为优先，并保存差异；如果不能判断是发布时间差异还是实质矛盾，该模块刷新失败，不自动选边。
6. `published_at` 表示发布日，`as_of` 表示数据截止日或报告期，`accessed_at` 表示访问日，`verified_at` 表示本轮已实际复核。四者不得互相替代。
7. 稳定的 GPU 规格不会仅因页面发布已久就显示“过时”；只要本轮重新访问并确认仍是当前官方规格，就更新 `verified_at`，同时保留原 `published_at` 和产品周期。
8. NVIDIA 营收以最新已发布财务报告期为准，在下一次财报发布前仍可标为本轮已核验；不得把自然日龄直接等同于财务数据失效。
9. GPU 出货量、型号占比与 HBM 供给估算每次都使用本轮核验的一手输入重新计算，输出范围、关键假设、敏感性和置信度。

## 数据分类与契约

每次刷新生成一个独立快照，包含五个必需模块：

| 模块 | 类型 | 最低要求 |
| --- | --- | --- |
| `gpu_specs` | `fact` | GPU 型号、HBM 类型、容量、发布日期或产品周期，以及 NVIDIA 官方来源 |
| `nvda_compute_revenue` | `fact` | 报告期、Compute 营收或可从官方披露直接拆出的值、单位和 NVIDIA 官方来源 |
| `gpu_shipments` | `estimate` | 估算结果、单位、官方营收输入、ASP 输入、公式、假设和局限 |
| `gpu_mix` | `estimate` | 各型号占比、总和校验、官方产品周期输入、推导规则、假设和局限 |
| `hbm_supply` | `estimate` 或 `fact` | 供给参数、单位；估算时记录官方产能或资本开支输入、公式、假设和局限 |

快照结构采用以下稳定接口：

```json
{
  "schema_version": 1,
  "refresh_id": "20260716T160527Z",
  "created_at": "2026-07-16T16:05:27+08:00",
  "modules": {
    "gpu_specs": {
      "status": "fresh",
      "kind": "fact",
      "data": {},
      "sources": []
    },
    "gpu_shipments": {
      "status": "fresh",
      "kind": "estimate",
      "data": {},
      "inputs": {},
      "formula": "shipments = compute_revenue / weighted_asp",
      "assumptions": [],
      "limitations": [],
      "sources": []
    }
  }
}
```

其他三个模块使用相同约定。事实模块不得包含未标记的估算值；估算模块必须同时具有 `inputs`、`formula`、`assumptions`、`limitations` 和一手 `sources`。

## 组件设计

### Skill 编排

`SKILL.md` 将分析流程改为以下顺序：

1. 确认单一股票代码。
2. 告知用户正在刷新一手行业数据。
3. 使用联网工具访问允许的一手来源，为五个模块构建候选快照。
4. 调用本地刷新工具验证并原子写入快照。
5. 若全部模块有效，打开平台对应的本机登录窗口。
6. 若存在刷新失败，先进行用户决策流程；未得到明确同意前不得打开登录窗口或生成报告。
7. 登录成功后，将本次快照路径交给分析入口并生成 HTML。

### 本地刷新与门禁工具

新增 `utils/industry_refresh.py`，职责限定为：

- 验证快照 schema、必需模块、字段类型、单位和日期；
- 验证来源 URL 属于允许的一手域名；
- 验证估算模块具有输入、公式、假设和局限；
- 拒绝只更新时间戳而没有有效数据或来源的刷新；
- 将通过校验的快照原子写入 `output/runtime/industry_snapshot.json`；
- 写入前保留上一份有效快照为 `industry_snapshot.previous.json`；
- 生成不含凭据的刷新状态文件供启动脚本和报告使用。

`output/` 已被 `.gitignore` 排除，因此运行快照不会进入仓库提交。快照只包含公开行业数据和来源信息。

### 分析入口

`analyze.py` 增加本次行业快照参数并执行强制门禁：

- 正常模式要求快照存在、schema 有效且五个模块状态均为 `fresh`；
- 使用旧数据时要求状态文件带有本轮显式授权标记，并且旧快照本身曾通过完整校验；
- Windows 和 macOS 启动脚本在显示账号提示前调用无凭据的快照预检；没有快照、快照不完整或没有授权时立即退出，不请求 `panda_data` 凭据、不生成报告；
- GPU/HBM 相关分析只读取本轮快照，不再从多个不一致的顶层和子级时间戳推断状态；DRAM、NAND、下游需求、CapEx、技术节点和对标公司等既有模块继续读取 `industry_data.json`，并沿用各自的新鲜度与来源检查。

Windows 和 macOS 启动脚本传递快照路径及旧数据授权状态，但命令行和状态文件始终不包含 `panda_data` 凭据。

## 刷新失败与用户决策

刷新失败时，Skill 在聊天中按模块展示：

- 失败模块与失败类别，例如官方页面不可访问、字段缺失或估算校验失败；
- 上一份有效快照的 `as_of`、访问日期和来源；
- 使用旧数据会影响哪些结论和评分。

随后询问：

```text
本次未能完整刷新以下行业数据：[模块列表]。现有旧数据截至 [日期]，来源为 [来源摘要]。
是否允许本次使用旧数据继续分析？报告会明确标记旧数据及其影响。
```

决策规则：

- 禁止静默回退旧数据，任何旧数据继续分析都必须绑定用户本轮的明确同意；
- 用户明确同意：创建本轮授权状态，使用上一份完整有效快照继续；
- 用户拒绝：停止分析；
- 用户未回复或表达不明确：停止并等待，不默认继续；
- 没有上一份完整有效快照：即使用户希望继续也必须停止，因为不存在可验证的旧数据；
- 禁止把失败刷新产生的半成品与旧快照混合后伪装为完整新数据。

旧数据授权只对当前一次分析有效，不写入长期偏好，也不能被下一次分析复用。

## 新鲜度与报告展示

新鲜度按五个子模块分别计算，不再只读取 `gpu_hbm_specs._last_updated`。汇总状态取五个模块中最差的状态，并在报告中显示每一项的：

- 状态：`fresh`、`cached-authorized`、`failed`；
- 数据类型：事实或估算；
- `published_at`、`as_of`、`accessed_at` 与 `verified_at` 的不同含义；
- 来源链接；
- 估算公式和主要假设。

若用户授权旧数据，HTML 顶部和相关 HBM 图表附近都显示醒目的“本次使用旧行业数据”提示。综合评分继续计算，但必须披露哪些维度使用旧输入，不能将结果描述为已由最新资料验证。

## 错误与安全处理

- 网络失败、页面结构变化、来源不允许、数据矛盾和解析缺失使用不同错误类别，不把网络问题表述成数据不存在。
- 写快照采用临时文件加原子替换；校验失败时保留上一份有效快照不变。
- 刷新日志只记录模块、来源域名、日期、状态和错误类别，不记录整页正文，不记录任何账号、密码或 token。
- `panda_data` 登录仍在可见的本机临时终端完成，行业刷新文件与登录进程相互独立。
- 官方资料存在冲突时保留冲突记录并判定该模块刷新失败，由用户决定是否回退旧快照。

## 测试设计

使用 Python 标准库 `unittest` 和离线 JSON fixtures，避免测试依赖实时网页或登录账号。

代码测试至少覆盖：

1. 五个完整模块和合法一手来源能够通过验证；
2. 缺少任一必需模块时验证失败；
3. 第三方来源或官方重定向到第三方时验证失败；
4. 估算模块缺少公式、输入、假设或局限时验证失败；
5. 型号占比之和不符合允许误差时验证失败；
6. 刷新失败不会覆盖上一份有效快照；
7. 未获用户授权时旧快照不能进入分析；
8. 授权只绑定一个刷新 ID 和一次分析；
9. 子模块新鲜度能够正确聚合，不再受旧顶层时间戳影响；
10. 报告正确显示一手事实、模型估算和旧数据授权警告。
11. 中国或亚洲官方入口不可达时能够改试同一发布方的全球官方入口，反向情况亦然；
12. 多个可达来源按最新 `as_of` 或报告期选择，而不是使用最先响应的页面；
13. 同报告期的官方来源内容冲突且无法解释时刷新失败；
14. 重定向到未允许域名或伪造子域名边界时验证失败；
15. 稳定产品规格在本轮实际复核后更新 `verified_at`，但不篡改 `published_at` 或 `as_of`；
16. 单一官方规格来源能够通过并标记 `single_source`，估算数据不能用该标记掩盖假设缺失。

Skill 行为测试使用以下真实场景：

- 用户要求分析 MU，所有一手来源可访问：必须先刷新，再登录分析；
- 部分官方来源不可访问且存在有效旧快照：必须询问用户，不能静默继续；
- 部分官方来源不可访问且没有有效旧快照：必须停止，不能生成半成品报告。

## 成功标准

- 每次正式分析都有唯一刷新 ID 和可追溯的一手来源快照；
- 未刷新成功且未获旧数据授权时，分析入口无法生成报告；
- 报告不再仅用一个顶层日期概括所有 GPU/HBM 模块；
- 中国、亚洲、全球或监管官方入口任一可达时均可参与刷新，并始终按数据截止期选择最新披露；
- 事实与估算在数据结构、日志和 HTML 中均清晰区分；
- Windows PowerShell 与 macOS Terminal.app 登录流程保持可用且不泄露凭据；
- 所有新增单元测试、现有语法检查和 Skill 结构检查通过。
