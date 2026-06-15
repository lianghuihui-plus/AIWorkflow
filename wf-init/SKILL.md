---
name: wf-init
description: 当用户要新建或初始化 AIWorkFlow 工作空间，并且当前目录是空目录、已有 PRD 路径，需要生成 README、CONTEXT、ISSUES、REVISIONS、JOURNAL、CHANGELOG、AGENT 初始文件时使用。
---

# 工作空间初始化

在当前空目录中初始化 AIWorkFlow 工作空间并生成所有初始文件。

> 继续已有工作空间：执行 `wf`，由主入口读取工作空间状态并判断下一步。
> 模板来源：使用当前 skill 目录下的 `templates/`；如无法读取模板文件，则按本 skill 中的变量规则生成等价文件，并提示检查 `wf-init` skill 目录软链接。

## 模板资料定位

初始化时如需读取模板，使用当前 `wf-init` skill 目录下的 `templates/`：

- `templates/README.md`
- `templates/AGENT.md`
- `templates/CONTEXT.md`
- `templates/ISSUES.md`
- `templates/REVISIONS.md`
- `templates/JOURNAL.md`
- `templates/CHANGELOG.md`

如果 `templates/` 缺失，仍可按本 skill 中的文件清单、变量规则和 `wf/contracts/` 生成等价文件；但完成提示必须说明模板资料缺失，建议检查 `wf-init` skill 目录软链接。

## 执行流程

### 步骤 1：当前目录校验

`wf-init` 只初始化当前目录，不创建父目录或工作空间子目录。

执行任何写入前，必须检查当前目录是否为空：

- 当前目录为空 → 继续初始化。
- 当前目录不存在 → 报错并停止，提示用户先创建目录并进入该目录。
- 当前目录存在任何文件或目录（包括隐藏文件）→ 报错并停止，不得覆盖、删除、迁移或复用已有内容。

报错模板：

```text
❌ 当前目录不是空目录，不能执行 wf-init。

请新建一个空目录，进入该目录后重新执行 wf-init。
```

### 步骤 2：交互问答

项目名称默认使用当前目录名（`basename 当前目录`），不单独询问。按表格顺序，一问一答收集。每问一个，等待用户回答后再继续。**Q2（PRD 路径）回答后，先执行步骤 3 处理路径，再继续 Q3。**

| 序号 | 提示语 | 必填 | 校验 |
|------|--------|------|------|
| 1 | `开发平台默认是 HarmonyOS，是否确认？如不是，请说明实际平台。` | 是 | 不能为空；用户确认时记录为 `HarmonyOS` |
| 2 | `原始 PRD 文档路径是？` | 是 | 文件或目录必须存在 |
| 3 | `项目代码路径是？（没有的话填"无"）` | 否 | 如提供，目录必须存在。填"无"则跳过 |

**校验失败 → 修正后继续当前问，不跳过。**

### 步骤 3：PRD 路径处理

拿到 PRD 路径后，自动判断并记录完整文件列表，**暂不拷贝**：
- **是文件**：记录该文件绝对路径。
- **是目录**：扫描目录下所有文件（.md / .txt / .pdf），逐条记录绝对路径。
- 不向用户确认，直接进入下一问。

### 步骤 4：创建工作空间目录结构

在当前目录下创建以下子目录：

```
./
├── prd/        ← 原始 PRD 文件副本
└── output/     ← 各阶段产物
    ├── specs/
    ├── reports/
    └── test-reports/
```

### 步骤 5：拷贝 PRD 文件

将步骤 3 中记录的全部 PRD 文件拷贝到 `prd/` 目录下，保持原文件名。拷贝后，后续所有生成文件中的 PRD 来源均指向 `prd/` 下的副本。

### 步骤 6：生成工作空间文件

优先从当前 skill 目录的 `templates/` 读取模板并生成以下文件：

- `README.md` ← `templates/README.md`
- `CONTEXT.md` ← `templates/CONTEXT.md`
- `ISSUES.md` ← `templates/ISSUES.md`
- `REVISIONS.md` ← `templates/REVISIONS.md`
- `JOURNAL.md` ← `templates/JOURNAL.md`
- `AGENT.md` ← `templates/AGENT.md`
- `CHANGELOG.md` ← `templates/CHANGELOG.md`

变量替换规则：

- `{项目名称}` → 当前目录名（`basename 当前目录`）
- `{平台}` → 步骤 2 确认或输入的开发平台，默认 `HarmonyOS`
- `{代码路径}` → 有代码路径则填绝对路径，填"无"则写 `无`
- `{代码路径信息}` → 有代码路径则 `仓库：{路径}`，填"无"则 `无代码仓库`
- `{PRD 份数}` → 步骤 3 记录的文件数量
- `{编码规范}` → 按 `{平台}` 渲染，不得把条件判断说明原文写入工作空间：
  - 平台为 `HarmonyOS` 时，写入下方 HarmonyOS/ArkTS 编码规范正文。
  - 平台不是 `HarmonyOS` 时，写入下方通用编码规范正文。
- `YYYY-MM-DD`、`YYYY-MM-DD HH:MM`、`HH:MM` → 当前日期时间

HarmonyOS/ArkTS 编码规范正文：

```markdown
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
```

通用编码规范正文：

```markdown
### 项目规范来源

- 先读取代码仓库已有规范、技术栈、目录结构和相邻代码风格。
- 不明确的编码约束必须写入 `ISSUES.md`，请求用户补充平台或项目规范。
- 不得把 HarmonyOS/ArkTS 专用规则套用到当前平台。

### 通用约束

- 保持现有架构、命名、格式化和测试模式。
- 不引入未经确认的新框架、第三方库或跨模块依赖。
- 修改代码后必须生成对应报告，并说明变更文件、验证方式和偏离项。
```

`CONTEXT.md` 初始化状态必须符合 `wf/contracts/context.md`：

```markdown
- 阶段：initialized
- 下一步：analyze-requirements
```

如果无法读取 `templates/`，可以使用本 skill 的规则生成等价文件，但必须完全符合 `templates/` 和 `wf/contracts/` 的当前格式，并在完成提示中说明模板资料缺失。

### 步骤 7：完成提示

```
✅ 工作空间初始化完成

项目名称：{当前目录名}
目标平台：XXX
PRD 文档：X 份
项目代码：有/无
工作空间目录：{当前目录绝对路径}

📁 已在当前目录创建工作空间结构（含 prd/、output/）
📄 已生成 README.md（入口文件）
📄 已生成 CONTEXT.md
📄 已生成 ISSUES.md
📄 已生成 REVISIONS.md
📄 已生成 JOURNAL.md
📄 已生成 AGENT.md
📄 已初始化 CHANGELOG.md

下一步：执行 wf 继续工作流
```
