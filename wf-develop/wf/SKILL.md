---
name: wf
description: 当用户在 AIWorkFlow 工作空间中要求继续或推进流程、分析需求、审核或修改产物、处理阻塞问题与决策时使用。
---

# 推进 AIWorkFlow

以工作空间数据和任务包为事实源推进当前工作，不手工维护状态、编号、版本、依赖或记忆。

## 定位内核

解析当前 `SKILL.md` 的真实路径并定位：

```text
<wf-skill-dir>/tools/aiwf.py
```

文件不存在时停止并报告安装不完整，不使用线上目录或旧工具作为回退。

## 先读状态

使用用户指定目录或当前目录调用：

```text
python3 <aiwf.py> status --workspace <workspace>
```

- `needs_recovery`：停止语义工作并报告需要恢复。
- `review`：只处理用户对待审核 revision 的批准或修改意见。
- `blocked`：只记录用户对开放问题的决定。
- `working`：恢复同一个任务包。
- `ready`：准备当前阶段任务。

## 准备和执行

对继续、下一步或分析需求调用：

```text
python3 <aiwf.py> prepare --workspace <workspace> [--task-id <T-id>] [--instruction <current-user-instruction>]
```

读取返回任务包中的 `global_memory`、`decisions`、`inputs`、`stage_guide` 和必要 `sources`。遵循任务包目标与边界，自主分析需求；只写 `draft_output` 和 `result_output`，不要直接修改正式产物或 `.aiwf` 数据。
任务阶段默认由引擎选择下一个可处理任务；只有用户明确指定任务时才传 `--task-id`。

完成后调用：

```text
python3 <aiwf.py> submit --workspace <workspace> --work-id <work-id>
```

报告产物与 revision，等待用户审核，不自行批准。

## 审核与修改

用户明确批准唯一待审核产物时调用：

```text
python3 <aiwf.py> review --workspace <workspace> --artifact-id <id> --revision <n> --outcome approved
```

用户要求修改时保留反馈原文并调用：

```text
python3 <aiwf.py> review --workspace <workspace> --artifact-id <id> --revision <n> --outcome changes_requested --feedback <feedback>
```

修改请求会创建带原草稿和反馈的新任务包；继续完成该任务包并再次提交。

## 阻塞问题与决定

阶段指南判定必须停止时，一次提交本轮全部阻塞问题。每项包含 `question`、`reason`、`recommendation` 和受影响阶段 `impact`：

```text
python3 <aiwf.py> question --workspace <workspace> --work-id <work-id> --items-json <json-array>
```

用户回答后逐项原样记录：

```text
python3 <aiwf.py> decide --workspace <workspace> --question-id <Q-id> --decision <user-decision>
```

全部问题解决后，恢复引擎生成的 successor work。不要替用户补全尚未回答的选择。
