---
layout: post
title: "从几个框架看 Context Compress 的实现"
date: 2025-08-04 23:35:22 +0800
categories: [分享]
article_type: 1
typora-root-url: ../../github.io
---

![](/assets/img/context-compress-caption.jpg)

# 什么是 Context Compress

从结果上看，是指用聊天摘要替换整个聊天上下文，保留对核心主题 high-level 总结的同时，节省后续任务所需的 tokens 数量。

好处和原因可以归结为：

1. 节省 token 的用量。这是一个刚性的需求，LLM 对每次输入的 token 数量有限制，长对话会迅速消耗 token，导致后续消息被截断或丢失，影响上下文理解。压缩后，通过将冗余和无关的内容去除，只保留关键信息，可以大幅减少 token 占用
2. 提升推理效率。由于输入更短、信息更密集，LLM 处理速度更快、响应更及时，推理时不会被无关内容干扰
3. 降低推理成本。模型按 token 计费，token 数量越少，推理成本越低
4. 提高性能。由于只保留了 high-level 摘要和关键信息，这有助于后续任务的上下文理解和快速回顾历史

也正是因为上述原因，现在的 Agent 产品都支持对上下文裁剪、压缩和概括，这次选择了几个或新或有一定竞争力的框架进行了实现层面的分析。

# 大家的做法

## Suna

此前分析 Suna 的时候，Suna 是专门开发了一个 context manager，用于 token 计算和 memory 压缩。

压缩时，先精心构造了一段 prompt，然后调用 LLM：

```python
f"""You are a specialized summarization assistant. Your task is to create a concise but comprehensive summary of the conversation history.

The summary should:
1. Preserve all key information including decisions, conclusions, and important context
2. Include any tools that were used and their results
3. Maintain chronological order of events
4. Be presented as a narrated list of key points with section headers
5. Include only factual information from the conversation (no new information)
6. Be concise but detailed enough that the conversation can continue with this summary as context

VERY IMPORTANT: This summary will replace older parts of the conversation in the LLM's context window, so ensure it contains ALL key information and LATEST STATE OF THE CONVERSATION - SO WE WILL KNOW HOW TO PICK UP WHERE WE LEFT OFF.


THE CONVERSATION HISTORY TO SUMMARIZE IS AS FOLLOWS:
===============================================================
==================== CONVERSATION HISTORY ====================
{messages}
==================== END OF CONVERSATION HISTORY ====================
===============================================================
"""
        }
        
        try:
            # Call LLM to generate summary
            response = await make_llm_api_call(
                model_name=model,
                messages=[system_message, {"role": "user", "content": "PLEASE PROVIDE THE SUMMARY NOW."}],
                temperature=0,
                max_tokens=SUMMARY_TARGET_TOKENS,
                stream=False
            )
            
            if response and hasattr(response, 'choices') and response.choices:
                summary_content = response.choices[0].message.content
                
                # Track token usage
                try:
                    token_count = token_counter(model=model, messages=[{"role": "user", "content": summary_content}])
                    cost = completion_cost(model=model, prompt="", completion=summary_content)
                    logger.info(f"Summary generated with {token_count} tokens at cost ${cost:.6f}")
                except Exception as e:
                    logger.error(f"Error calculating token usage: {str(e)}")
                
                # Format the summary message with clear beginning and end markers
                formatted_summary = f"""
======== CONVERSATION HISTORY SUMMARY ========

{summary_content}

======== END OF SUMMARY ========

The above is a summary of the conversation history. The conversation continues below.
"""
```

但在 7 月份，context manager 的实现被重构了，在重构后的版本里移除了 LLM，转而使用了更为传统的方式：直接基于文本内容的长度进行截断。实现如下：

```python
def compress_message(self, msg_content: Union[str, dict], message_id: Optional[str] = None, max_length: int = 3000) -> Union[str, dict]:
    """Compress the message content."""
    if isinstance(msg_content, str):
        if len(msg_content) > max_length:
            return msg_content[:max_length] + "... (truncated)" + f"\n\nmessage_id \"{message_id}\"\nUse expand-message tool to see contents"
        else:
            return msg_content
    elif isinstance(msg_content, dict):
        if len(json.dumps(msg_content)) > max_length:
            # Special handling for edit_file tool result to preserve JSON structure
            tool_execution = msg_content.get("tool_execution", {})
            if tool_execution.get("function_name") == "edit_file":
                output = tool_execution.get("result", {}).get("output", {})
                if isinstance(output, dict):
                    # Truncate file contents within the JSON
                    for key in ["original_content", "updated_content"]:
                        if isinstance(output.get(key), str) and len(output[key]) > max_length // 4:
                            output[key] = output[key][:max_length // 4] + "\n... (truncated)"
            
            # After potential truncation, check size again
            if len(json.dumps(msg_content)) > max_length:
                # If still too large, fall back to string truncation
                return json.dumps(msg_content)[:max_length] + "... (truncated)" + f"\n\nmessage_id \"{message_id}\"\nUse expand-message tool to see contents"
            else:
                return msg_content
        else:
            return msg_content
```

值得注意的是，Suna 还专门提供了一个 expand-message tool 用于让 LLM 在适当的时候获取完整的消息内容："...Use expand-message tool to see contents"，tool 的实现就是一个简单的 db 检索而已，详见 [ExpandMessageTool](https://github.com/kortix-ai/suna/blob/main/backend/agent/tools/expand_msg_tool.py)。

### 变更的动机分析

新的 context manager 不再把 “上下文压缩” 简化为一次性摘要，而是引入了多层级、按类型细分的压缩策略，包括：

- compress_tool_result_messages
- compress_user_messages
- compress_assistant_messages
- compress_message
- middle_out_messages

这种设计的出现，可能是为了解决旧实现的三类问题：

1. 稳定性。旧做法依赖单次摘要，然后删除整批历史消息，容易误删最近仍会被引用的 ToolResult、用户指令，导致后续工具调用失配或 memory 断层。新版先识别 “tool_result”、“user”、“assistant” 三种角色，再按 “**保留最近一条、压缩旧条**” 的顺序逐层处理，理论上能降低了上下文缺口
2. 可控性 & 模型适配。随着 Qwen-VL-MoE-200k、Claude-Sonnet-200k 等大 window 模型上线，Agent 产品的 token 往往需要在 40k～200k 不同容量之间动态调节。为了适应技术的发展，compress_messages 在进入压缩前会先根据模型名**修正 ‎max_tokens**，如 Sonnet 选用了 200k – 64k – 28k 的 max tokens，再递归根据 ‎token_threshold 动态调整，比旧实现 “写死上限” 更灵活一些
3. 性能 & 成本考虑。旧版在触顶时会将整段历史提交 LLM 以创建摘要，既耗费推理时间，也产生额外 token 费用。现在改成都在本地完成，不再额外调用 LLM，总体能节省不少费用，而且 **让耗时稳定在 O(1)** ：
   1. 直接本地字符串截断，见 safe_truncate
   2. 规则化删除 tool arguments，见 remove_meta_messages
   3. 只取一半的列表，见 middle_out_messages

除了技术层面，背后或许有更大的考虑：

1. Suna 自身定位。Suna 在发布之初的视频介绍中，说希望 Suna 能像真正的队友一样 “Reason、Plan、Take Actions”，那么工具调用记录（‎tool_execution）的可追溯性显然比摘要文本更重要，因此有动机保留结构化 JSON 并只删冗余字段
2. 合规要求。Suna 的用户或多或少有对 AI 合规的诉求，项目如果要引入合规 Label，服务端必须做到可回放历史指令链路，而把上下文压成一段新文字会破坏审计链，但如果只做局部截断 + 标记 (truncated)、而不是整体改写，既满足回放又能避免爆窗

总之，真实原因不得而知，但根据 GitHub 的 issue 记录、Suna 项目的演进方向窥探一二。

## Qwen Agent

Qwen Agent 有两种处理方式。

### 方式一：truncate roughly

和 Suna 一样，同样是引入了 token 计算和根据消息类型智能裁剪，但没有 Suna 可以 expand-message 的策略。

roughly 实现如下：

```python
def _truncate_input_messages_roughly(messages: List[Message], max_tokens: int):
    # 1. 保护系统消息
    if messages and messages[0].role == SYSTEM:
        sys_msg = messages[0]
        available_token = max_tokens - _count_tokens(sys_msg)
    else:
        available_token = max_tokens
     
    # 2. 从最新消息开始保留
    new_messages = []
    for i in range(len(messages) - 1, -1, -1):
        if messages[i].role == SYSTEM:
            continue
        cur_token_cnt = _count_tokens(messages[i])
         
        if cur_token_cnt <= available_token:
            new_messages = [messages[i]] + new_messages
            available_token -= cur_token_cnt
        else:
            # 3. 对超长消息进行智能截断
            if messages[i].role == USER:
                _msg = _truncate_message(messages[i], max_tokens=available_token)
                if _msg:
                    new_messages = [_msg] + new_messages
                break
            elif messages[i].role == FUNCTION:
                # 工具结果保留首尾重要信息
                _msg = _truncate_message(messages[i], max_tokens=available_token, keep_both_sides=True)
                if _msg:
                    new_messages = [_msg] + new_messages
     
    return new_messages
 
def _truncate_message(msg: Message, max_tokens: int, keep_both_sides: bool = False):
    if isinstance(msg.content, str):
        content = tokenizer.truncate(msg.content, max_token=max_tokens, keep_both_sides=keep_both_sides)
    else:
        text = []
        for item in msg.content:
            if not item.text:
                return None
            text.append(item.text)
        text = '\n'.join(text)
        content = tokenizer.truncate(text, max_token=max_tokens, keep_both_sides=keep_both_sides)
    return Message(role=msg.role, content=content)
```

### 方式二：file retrieval

Qwen Agent 还实现了一个专门的 Agent，用于将 messages 保存到文件，然后通过 RAG 在历史对话中进行检索：

```python
class DialogueRetrievalAgent(Assistant):
    """This is an agent for super long dialogue."""

    def _run(self,
             messages: List[Message],
             lang: str = 'en',
             session_id: str = '',
             **kwargs) -> Iterator[List[Message]]:
        """Process messages and response

        Answer questions by storing the long dialogue in a file
        and using the file retrieval approach to retrieve relevant information

        """
        assert messages and messages[-1].role == USER
        new_messages = []
        content = []
        for msg in messages[:-1]:
            if msg.role == SYSTEM:
                new_messages.append(msg)
            else:
                content.append(f'{msg.role}: {extract_text_from_message(msg, add_upload_info=True)}')
        # Process the newest user message
        text = extract_text_from_message(messages[-1], add_upload_info=False)
        if len(text) <= MAX_TRUNCATED_QUERY_LENGTH:
            query = text
        else:
            if len(text) <= MAX_TRUNCATED_QUERY_LENGTH * 2:
                latent_query = text
            else:
                latent_query = f'{text[:MAX_TRUNCATED_QUERY_LENGTH]} ... {text[-MAX_TRUNCATED_QUERY_LENGTH:]}'

            *_, last = self._call_llm(
                messages=[Message(role=USER, content=EXTRACT_QUERY_TEMPLATE[lang].format(ref_doc=latent_query))])
            query = last[-1].content
            # A little tricky: If the extracted query is different from the original query, it cannot be removed
            text = text.replace(query, '')
            content.append(text)

        # Save content as file: This file is related to the session and the time
        content = '\n'.join(content)
        file_path = os.path.join(DEFAULT_WORKSPACE, f'dialogue_history_{session_id}_{datetime.datetime.now():%Y%m%d_%H%M%S}.txt')
        save_text_to_file(file_path, content)

        new_content = [ContentItem(text=query), ContentItem(file=file_path)]
        if isinstance(messages[-1].content, list):
            for item in messages[-1].content:
                if item.file or item.image or item.audio:
                    new_content.append(item)
        new_messages.append(Message(role=USER, content=new_content))

        return super()._run(messages=new_messages, lang=lang, **kwargs)
```

实用性和效果不得而知，很可能花了很大力气只能解决一点点问题。

## smolagents

HuggingFace 的开源框架，社区有人希望提供 memory 压缩能力，但目前还没有进展：https://github.com/huggingface/smolagents/issues/1385。

从讨论中可以看出潜在的方案同 Suna 早期的做法，让 LLM 根据 prompt 对历史中的 user、assisstant 创建摘要，考虑到 Suna 于 7 月移除了该实现，可能业界在慢慢意识到此种方案的局限性？

当前的实现则平平无奇：

```python
MAX_LENGTH_TRUNCATE_CONTENT = 20000

def truncate_content(content: str, max_length: int = MAX_LENGTH_TRUNCATE_CONTENT) -> str:
    if len(content) <= max_length:
        return content
    else:
        return (
            content[: max_length // 2]
            + f"\n..._This content has been truncated to stay below {max_length} characters_...\n"
            + content[-max_length // 2 :]
        )
```

## JoyAgent

近期京东开源的、完整的端到端 Agent 产品，而且 0 生态依赖，不像 Coze 绑定火山、Qwen 绑定阿里，很有潜力。

Context Compress 这块儿有点粗鲁，首先是 history：

```java
public List<Map<String, Object>> truncateMessage(AgentContext context, List<Map<String, Object>> messages, int maxInputTokens) {
    if (messages.isEmpty() || maxInputTokens < 0) {
        return messages;
    }
    log.info("{} before truncate {}", context.getRequestId(), JSON.toJSONString(messages));
    List<Map<String, Object>> truncatedMessages = new ArrayList<>();
    int remainingTokens = maxInputTokens;
    Map<String, Object> system = messages.get(0);
    if ("system".equals(system.getOrDefault("role", ""))) {
        remainingTokens -= tokenCounter.countMessageTokens(system);
    }

    for (int i = messages.size() - 1; i >= 0; i--) {
        Map<String, Object> message = messages.get(i);
        int messageToken = tokenCounter.countMessageTokens(message);
        if (remainingTokens >= messageToken) {
            truncatedMessages.add(0, message);
            remainingTokens -= messageToken;
        } else {
            break;
        }
    }
    // use assistant 保证完整性
    Iterator<Map<String, Object>> iterator = truncatedMessages.iterator();
    while (iterator.hasNext()) {
        Map<String, Object> message = iterator.next();
        if (!"user".equals(message.getOrDefault("role", ""))) {
            iterator.remove(); // 安全删除当前元素
        } else {
            break;
        }
    }

    if ("system".equals(system.getOrDefault("role", ""))) {
        truncatedMessages.add(0, system);
    }
    log.info("{} after truncate {}", context.getRequestId(), JSON.toJSONString(truncatedMessages));

    return truncatedMessages;
}
```

可以看到除了 system、user、assistant 外，其他的消息类型全干掉。

然后是消息粒度上：

```java
for (Message message : messages) {
    String content = message.getContent();
        if (content != null && content.length() > getMessageSizeLimit()) {
        log.info("requestId: {} message truncate,{}", requestId, message);
        content = content.substring(0, getMessageSizeLimit());
    }
    sb.append(String.format("role:%s content:%s\n", message.getRole(), content));
}
```

就很粗鲁。

## Qwen Code / Gemini CLI

Qwen Code 是近期在国内大火的 Vibe Coding 产品，它也实现了高效的上下文压缩能力。

由于 Qwen Code 是对 Gemini CLI 的二次开发，所以分析的实际上是 Gemini CLI 的设计，涉及压缩的核心实现 tryCompressChat 完全一样，加上 Coding 场景长上下文很常见，也算有一定的代表性。

Gemini CLI 采用的策略不像上面那些粗鲁的家伙，它会先对历史进行分割：

```typescript
// 计算需要压缩的历史记录位置（保留最近的消息到 COMPRESSION_PRESERVE_THRESHOLD，默认设置的是 30%）
let compressBeforeIndex = findIndexAfterFraction(
  curatedHistory,
  1 - this.COMPRESSION_PRESERVE_THRESHOLD, // 0.7
);

// 不错的小细节：确保分割点在用户消息处，从而避免在模型回复中间分割
while (
  compressBeforeIndex < curatedHistory.length &&
  (curatedHistory[compressBeforeIndex]?.role === 'model' ||
    isFunctionResponse(curatedHistory[compressBeforeIndex]))
) {
  compressBeforeIndex++;
}

// 分割历史记录
const historyToCompress = curatedHistory.slice(0, compressBeforeIndex);
const historyToKeep = curatedHistory.slice(compressBeforeIndex);
```

然后再对 historyToCompress 进行压缩：

```typescript
// 填充要压缩的消息
this.getChat().setHistory(historyToCompress);

// 使用专门的 prompt 让模型生成结构化摘要
const { text: summary } = await this.getChat().sendMessage(
  {
    message: {
      text: 'First, reason in your scratchpad. Then, generate the <state_snapshot>.',
    },
    config: {
      systemInstruction: { text: getCompressionPrompt() },
    },
  },
  prompt_id,
);
```

最后将 summary 封装成 user 消息：

```typescript
this.chat = await this.startChat([
  {
    role: 'user',
    parts: [{ text: summary }],
  },
  {
    role: 'model',
    parts: [{ text: 'Got it. Thanks for the additional context!' }],
  },
  ...historyToKeep,
]);
```

tryCompressChat 完整源码见：[tryCompressChat](https://github.com/google-gemini/gemini-cli/blob/main/packages/core/src/core/client.ts#L678)。

prompt 也是精心构造的：

```typescript
/**
 * Provides the system prompt for the history compression process.
 * This prompt instructs the model to act as a specialized state manager,
 * think in a scratchpad, and produce a structured XML summary.
 */
export function getCompressionPrompt(): string {
  return `
You are the component that summarizes internal chat history into a given structure.

When the conversation history grows too large, you will be invoked to distill the entire history into a concise, structured XML snapshot. This snapshot is CRITICAL, as it will become the agent's *only* memory of the past. The agent will resume its work based solely on this snapshot. All crucial details, plans, errors, and user directives MUST be preserved.

First, you will think through the entire history in a private <scratchpad>. Review the user's overall goal, the agent's actions, tool outputs, file modifications, and any unresolved questions. Identify every piece of information that is essential for future actions.

After your reasoning is complete, generate the final <state_snapshot> XML object. Be incredibly dense with information. Omit any irrelevant conversational filler.

The structure MUST be as follows:

<state_snapshot>
    <overall_goal>
        <!-- A single, concise sentence describing the user's high-level objective. -->
        <!-- Example: "Refactor the authentication service to use a new JWT library." -->
    </overall_goal>

    <key_knowledge>
        <!-- Crucial facts, conventions, and constraints the agent must remember based on the conversation history and interaction with the user. Use bullet points. -->
        <!-- Example:
         - Build Command: \`npm run build\`
         - Testing: Tests are run with \`npm test\`. Test files must end in \`.test.ts\`.
         - API Endpoint: The primary API endpoint is \`https://api.example.com/v2\`.
         
        -->
    </key_knowledge>

    <file_system_state>
        <!-- List files that have been created, read, modified, or deleted. Note their status and critical learnings. -->
        <!-- Example:
         - CWD: \`/home/user/project/src\`
         - READ: \`package.json\` - Confirmed 'axios' is a dependency.
         - MODIFIED: \`services/auth.ts\` - Replaced 'jsonwebtoken' with 'jose'.
         - CREATED: \`tests/new-feature.test.ts\` - Initial test structure for the new feature.
        -->
    </file_system_state>

    <recent_actions>
        <!-- A summary of the last few significant agent actions and their outcomes. Focus on facts. -->
        <!-- Example:
         - Ran \`grep 'old_function'\` which returned 3 results in 2 files.
         - Ran \`npm run test\`, which failed due to a snapshot mismatch in \`UserProfile.test.ts\`.
         - Ran \`ls -F static/\` and discovered image assets are stored as \`.webp\`.
        -->
    </recent_actions>

    <current_plan>
        <!-- The agent's step-by-step plan. Mark completed steps. -->
        <!-- Example:
         1. [DONE] Identify all files using the deprecated 'UserAPI'.
         2. [IN PROGRESS] Refactor \`src/components/UserProfile.tsx\` to use the new 'ProfileAPI'.
         3. [TODO] Refactor the remaining files.
         4. [TODO] Update tests to reflect the API change.
        -->
    </current_plan>
</state_snapshot>
`.trim();
}
```

它最终的返回结构是这样：

```xml
<state_snapshot>
    <overall_goal>
        <!-- 用户的高级目标 -->
    </overall_goal>
    
    <key_knowledge>
        <!-- 关键事实和约束 -->
    </key_knowledge>
    
    <file_system_state>
        <!-- 文件系统状态 -->
    </file_system_state>
    
    <recent_actions>
        <!-- 最近的行动 -->
    </recent_actions>
    
    <current_plan>
        <!-- 当前计划 -->
    </current_plan>
</state_snapshot>
```

看起来，Gemini CLI 为了尽大努力做到无损压缩，尝试了：

1. 通过结构化摘要保留最关键的信息
2. 保留最近历史记录的连续性、完整性
3. 使用专门的压缩 prompt 确保信息熵

我觉得 Gemini CLI 的上下文压缩实现是一种高效且实用的方案，实现成本比 Suna 稍高，至于孰好孰坏还拿不准。

# 最后

看的出来，目前业界在上下文压缩的实现上尚无统一标准，各大框架和产品仍处于持续探索和快速演进阶段，Suna、Gemini CLI 这样的 “最佳实践”在摘要的准确性和信息保真度仍需持续关注，尤其是在复杂任务或长任务推理场景下，既要压缩，又不遗漏关键指令和细节，是当前研发中的难点。希望未来能看到更多开源框架和实际案例的积累，共同推动这一能力在 Agent、长对话等领域内的落地。
