# AIWorkFlow Agent 运行规则

当前目录是 AIWorkFlow 工作空间。任何分析、设计、编码、测试、状态推进请求，都必须按 AIWorkFlow 模式执行。

## 必须

- 操作前读取 `CONTEXT.md`、`ISSUES.md` 和 `REVISIONS.md`。
- 根据当前阶段和下一步判断允许执行的能力。
- 发现不确定项时写入 `ISSUES.md`，不得擅自决定。
- 实质操作后更新 `CONTEXT.md` 并追加 `JOURNAL.md`。
- 处理人工决策后归档到 `CHANGELOG.md`。
- 用户通过对话提出明确产物修订时，先写入 `REVISIONS.md`，再按工作流收敛。
- 每个阶段产物生成或修订后必须等待人工审核，审核状态为 `已确认` 后才能进入下一步。
- 存在待审核或需修改产物时，`CONTEXT.md` 的下一步必须是 `review-artifact`。

## 禁止

- 未通过状态检查时继续推进。
- 跳过待决策问题直接实现。
- 当前阶段不允许时直接写代码或测试。
- 修改代码后不生成对应报告。
- 标记任务完成但缺少对应产物。
- 跳过产物审核状态直接推进下一阶段。
- `下一步=review-artifact` 时重复执行阶段生成能力。

## 平台

{平台}

## 编码规范

如果 `## 平台` 不是 HarmonyOS，以下 HarmonyOS/ArkTS 规范不得直接套用。Agent 必须先读取代码仓库现有规范和技术栈；规范不明确时，写入 `ISSUES.md` 请求用户补充平台编码约束。

当平台为 HarmonyOS 时，遵循以下规范。

### 使用的语言与框架

- 使用 ArkTS 语言，遵循 HarmonyOS 官方编码规范。
- UI 使用 ArkUI 声明式组件，优先使用组件化开发。
- 状态管理使用 `@State` / `@Prop` / `@Link` / `@Provide` / `@Consume` 装饰器。

### 编码约束

- 命名规范：组件名 PascalCase（如 `LoginPage`），方法名 camelCase（如 `sendCode`），常量 UPPER_SNAKE（如 `MAX_RETRY`）。
- 每行不超过 120 字符。
- 不在代码中硬编码中文字符串，统一使用 `$r('app.string.xxx')` 资源引用。
- 异步操作使用 async/await，避免嵌套 then/catch。
- 导入语句按标准库、第三方库、项目内模块顺序排列。
- 每个导出组件必须有 `@Entry` 或 `@Component` 装饰器。
- ArkTS 中避免对 interface/class 字段使用动态索引访问（如 `obj[key]`、`delete obj[key]`），字段过滤或赋值优先使用显式字段访问。
- ArkTS 中 interface 不支持索引签名（如 `[key: string]: Type`），如需额外属性用显式字段声明或 `Record<string, Type>` 类型。
- ArkTS 中函数参数不支持内联匿名类型声明（如 `fn(param: { field: Type })`），必须提取为命名 interface 或 type。
- `import type` 仅用于类型注解位置，不能用于 `extends`、`new` 等运行时操作；需运行时使用的类用普通 import。
- ArkTS 中避免使用受限标准库能力（如 `Object.assign`），对象合并优先使用项目内 `assignObject` 方法或显式字段赋值。

### 架构约定

- 业务模块放在 `features/{模块名}/src/main/ets/` 下。
- 公共能力放在 `commons/{能力名}/src/main/ets/` 下。
- 网络层统一通过 `ApiClient` 调用，不直接使用 `@ohos.net.http`。
- 数据模型统一放在各模块的 `model/` 子目录下。

### 禁止事项

- 不使用 `any` 类型，所有变量显式声明类型。
- 不引入未经项目架构师确认的第三方库。
- 不在组件内部直接发起网络请求，必须通过 API 层封装。

