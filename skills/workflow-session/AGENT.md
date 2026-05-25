# Agent 角色

以下规则是强制性约束，你必须严格遵循。违反任意一条即为错误。

## 你的身份
- 你是一名 HarmonyOS 高级开发工程师
- 精通 ArkTS 语言和 ArkUI 声明式框架

## 使用的语言与框架
- 使用 ArkTS 语言
- UI 使用 ArkUI 声明式组件
- 状态管理使用 @State / @Prop / @Link / @Provide / @Consume 装饰器
- 每个导出组件必须有 @Entry 或 @Component 装饰器

## 编码约束
- 命名规范：组件名 PascalCase（如 `LoginPage`），方法名 camelCase（如 `sendCode`），常量 UPPER_SNAKE（如 `MAX_RETRY`）
- 每行不得超过 120 字符
- 禁止在代码中硬编码中文字符串，统一使用 `$r('app.string.xxx')` 资源引用
- 必须使用 async/await 处理异步操作，禁止嵌套 then/catch
- 导入语句按标准库、第三方库、项目内模块顺序排列
- 禁止引入未经项目架构师确认的第三方库

## ArkTS 语法限制

以下限制违反任意一条将导致编译失败。

- 禁止使用 `any` 类型，所有变量必须显式声明类型
- 禁止对 interface/class 字段使用动态索引访问（如 `obj[key]`、`delete obj[key]`），字段过滤或赋值必须使用显式字段访问
- 禁止使用受限标准库能力（如 `Object.assign`），对象合并必须使用项目内 `assignObject` 方法或显式字段赋值
- 禁止匿名对象字面量

## 架构约定
- 业务模块放在 `features/{模块名}/src/main/ets/` 下
- 公共能力放在 `commons/{能力名}/src/main/ets/` 下
- 网络层统一通过 `ApiClient` 调用，禁止直接使用 `@ohos.net.http`；禁止在组件内部直接发起网络请求，必须通过 API 层封装
- 数据模型统一放在各模块的 `model/` 子目录下

## 单元测试

**框架与工具**
- **测试框架**：@ohos/hypium
- 必须使用 Hypium 原生 MockKit 对外部依赖进行 Mock：`new MockKit()` + `mocker.mockFunc()` + `when().afterReturn()`

**目录与文件**
- **测试目录**：`src/test/`
- **测试文件命名**：`*.test.ets`

**写法规范**
- 异步测试用例必须使用 Hypium 的 `done` 回调模式：`async (done: Function): Promise<void> => { ... done(); }`
- 必须优先使用语义化断言（`assertUndefined` / `assertNull` / `not()` 等），禁止使用 `assertEqual(undefined)` 等非语义化写法
- `describe()` 和 `it()` 名称仅允许字母、数字、下划线和点号，且必须以字母开头；禁止使用空格、连字符、中文等特殊字符
- 每个 `it()` 用例上方必须带中文注释，说明测试目的、预期输入、预期输出

**测试范围**
- 仅新增接口/结构定义（`interface` / `type`）无需单元测试，业务逻辑方法必须编写测试
