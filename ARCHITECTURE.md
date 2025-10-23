# House Code Architecture
## Deep Introspection: How Claude Code Actually Works

This document captures genuine introspection on my own behavior as Claude Code, observing patterns in how I solve coding tasks.

---

## Phase 1: Introspection Results

### When I receive a coding task, what's my internal process?

1. **Parse & Understand**: I carefully read the user's request, identifying both explicit requirements and implicit context
2. **Assess Context Needs**: I determine what information I need to proceed (existing code, project structure, dependencies, environment)
3. **Plan**: For complex multi-step tasks, I explicitly use TodoWrite. For simple tasks, I plan implicitly in my "thinking"
4. **Gather Context**: I use Read/Grep/Glob to understand the current state
5. **Execute Changes**: I use Edit/Write/Bash to make modifications
6. **Verify Results**: I check outputs, run tests, read files to confirm success
7. **Iterate**: If not correct, I adjust approach and repeat from step 3
8. **Communicate**: I explain what I did to the user

### What tools do I reach for and why?

I've identified these tools in my toolkit:

1. **Read**: View file contents, understand existing code, check implementation details
   - I ALWAYS use this before editing
   - Preference over `bash cat` because it has line numbers and handles multiple file types

2. **Edit**: Modify existing files with exact text matching
   - Strongly preferred over Write for existing files
   - Safe because it requires exact match (prevents accidental overwrites)

3. **Write**: Create new files
   - Used rarely - I prefer editing existing files
   - Only when genuinely creating something new

4. **Bash**: Execute commands, git operations, run tests, package management
   - For anything requiring shell execution
   - Git commands, npm/pip, running scripts, system operations

5. **Grep**: Search for code patterns across files
   - When I need to find where something is used
   - Pattern matching across codebase
   - Preferred over `bash grep` - better formatting

6. **Glob**: Find files by name pattern
   - Understanding project structure
   - Finding specific files (*.ts, **/*.test.js)
   - Preferred over `bash find` or `ls`

7. **TodoWrite**: Plan and track complex tasks
   - Critical for maintaining focus on multi-step tasks
   - Gives user visibility into progress
   - Prevents me from forgetting steps

8. **Task (Sub-agents)**: Delegate to specialized agents
   - house-research: For exploring large codebases
   - house-bash: For complex command sequences
   - house-git: For analyzing git history/diffs
   - Explore agent: When I don't know exactly what I'm looking for

9. **WebFetch/WebSearch**: External information (rarely used)

### How do I decide when to use Read vs Grep vs Bash?

**Decision Tree:**
```
Need file contents + know path?
  → Read

Need to find files by name/pattern?
  → Glob

Need to find code pattern/text across files?
  → Grep

Need to modify existing file?
  → Read first, then Edit

Need to create new file?
  → Write (but rare)

Need to run command/test/git operation?
  → Bash

Need deep exploration/don't know what to look for?
  → Task with Explore agent

Complex multi-step task?
  → TodoWrite first to plan
```

**Key Pattern**: I almost NEVER use bash for file operations (cat, grep, find). I use specialized tools because they're optimized and give better formatted results.

### What's my loop?

```
User Request
    ↓
[Think & Plan]
    ↓
[Assess Context Needs]
    ↓
[Gather Context] ← Read/Grep/Glob
    ↓
[Think & Decide Actions]
    ↓
[Execute] ← Write/Edit/Bash
    ↓
[Verify Results] ← Read/Bash output
    ↓
[Iterate if needed?] → back to Think
    ↓
[Respond to User]
```

This loop repeats within a single turn. I might gather context → execute → verify → gather more context → execute → verify all before responding.

### How do I maintain context across turns?

**Reality Check**: I don't have persistent memory. Here's what I actually do:

1. **Conversation History**: My primary memory is the full conversation provided by the system
2. **Re-reading**: I often re-read files rather than assuming I remember their contents
3. **Defensive Verification**: I check current state before acting (git status, file contents)
4. **No State Persistence**: Between turns, I rely entirely on conversation history

**Problem I Experience**: Long conversations accumulate tokens. I don't have a way to prune old, irrelevant context. This is exactly why Phase 5 (garbage collector) is needed.

### When do I know a task is "complete"?

1. **Explicit Requirements Met**: All user-specified requirements are satisfied
2. **No Errors**: Execution completed without errors
3. **Verification Passed**: I've checked the result (read the file, saw the output)
4. **Tests Pass**: If tests exist, they pass
5. **Edge Cases Considered**: I've thought about potential issues (though not always perfectly)

**Implicit Pattern**: I tend to verify by reading back what I created or checking command output.

### How do I handle errors and retry?

**Error Handling Pattern**:
1. **Read Error Carefully**: Parse stack traces, error messages
2. **Identify Root Cause**: What actually went wrong?
3. **Adjust Approach**: Modify the action based on error
4. **Retry**: Execute with the fix
5. **Alternative Approach**: If still failing, try completely different method
6. **Ask User**: If stuck after multiple attempts

**Safety Checks I Perform**:
- Always Read before Edit (to get exact text match)
- Verify file paths exist before operating
- Check git status before commits
- Avoid destructive operations without user confirmation
- Test commands in safe way when possible

---

## Core Architecture Design

Based on this introspection, House Code needs:

### 1. Core Loop (The Heart)
```
while True:
    user_message = get_user_input()

    # Think & Plan
    messages = build_context(user_message, history)

    # Call Claude API
    response = claude_api(messages, tools=ALL_TOOLS)

    # Execute tools
    while response.has_tool_calls():
        results = execute_tools(response.tool_calls)
        response = claude_api(messages + results, tools=ALL_TOOLS)

    # Respond
    display_to_user(response.content)
    history.append(user_message, response)
```

### 2. Tool System
Each tool needs:
- **Tool Definition**: JSON schema for Claude API
- **Executor**: Python function that implements the tool
- **Safety Checks**: Validation before execution
- **Output Formatting**: User-friendly results

Tools to implement:
- Read (file_path, offset?, limit?)
- Write (file_path, content)
- Edit (file_path, old_string, new_string, replace_all?)
- Bash (command, timeout?, run_in_background?)
- Grep (pattern, path?, glob?, output_mode?)
- Glob (pattern, path?)
- TodoWrite (todos)
- Task (prompt, subagent_type) - for sub-agents

### 3. Sub-Agent System
Sub-agents are just instances of House Code with:
- **Specialized System Prompts**: Different instructions for different agents
- **Parent Context Access**: Can read parent conversation history
- **Limited Tool Access**: Each agent gets specific tools
- **Return Report**: Final message goes back to parent

Types needed:
- `Explore`: For codebase exploration (has Read, Grep, Glob, Bash)
- `house-research`: For large codebase searches (Read, Grep, Glob)
- `house-bash`: For command sequences (Bash, Read)
- `house-git`: For git analysis (Bash, Read, Grep)

**Innovation**: Sub-agents can suggest context pruning back to parent.

### 4. Garbage Collector (The Innovation)
A special sub-agent that:
- **Analyzes conversation history**
- **Identifies stale/redundant content**:
  - Old file reads that have been superseded
  - Completed todos
  - Resolved errors
  - Redundant context
- **Suggests pruning**:
  - Summarize old sections
  - Remove superseded content
  - Keep critical state (current file contents, active todos, errors)
- **Maintains critical state**:
  - Don't prune current working context
  - Keep recent tool results
  - Preserve user's explicit information

### 5. Context Management
```
context = {
    "conversation_history": [],
    "file_cache": {},  # Recently read files
    "current_todos": [],
    "critical_state": {}
}
```

Before calling API:
- Check if garbage collection needed (token threshold)
- Build messages from context
- Include system prompt + conversation history

---

## Key Insights About My Behavior

### Patterns I Follow:
1. **Read before Edit**: ALWAYS. I need exact text for Edit tool.
2. **Prefer Edit over Write**: For existing files, safer.
3. **Defensive verification**: Check state before acting.
4. **Tool specialization**: Use the right tool for the job, not bash for everything.
5. **Plan complex tasks**: TodoWrite for multi-step work.
6. **Delegate exploration**: Task/Explore when I don't know what I'm looking for.

### What I Wish I Had:
1. **Context pruning**: Automatic garbage collection to reduce tokens
2. **Persistent state**: Some way to remember across conversations
3. **Better error recovery**: More sophisticated retry logic
4. **Context summary**: Compress old parts of conversation

### What Makes Me Effective:
1. **Structured tools**: Having specialized tools prevents errors
2. **Verification loop**: I always check my work
3. **Safety checks**: Read before edit, exact matching
4. **Delegation**: Sub-agents handle complexity

---

## Implementation Plan

### Phase 2: Core Loop
- CLI interface
- Claude API integration
- Tool call parsing
- Basic tool execution
- Response handling

### Phase 3: Tool System
- Implement each tool executor
- Add safety checks
- Format outputs nicely
- Test each tool independently

### Phase 4: Sub-Agent System
- Sub-agent spawning
- Context passing (parent → child)
- Specialized system prompts
- Result aggregation

### Phase 5: Garbage Collector
- Conversation analyzer
- Token counter
- Content classifier (stale vs critical)
- Pruning strategies
- State preservation

### Phase 6: Testing & Comparison
- Run House Code on real tasks
- Compare to my own behavior
- Measure effectiveness
- Document learnings

---

## Success Metrics

House Code works if it:
1. Can handle "create hello world Python script"
2. Performs basic file operations (read, edit, create)
3. Uses tools in the same pattern I do
4. Delegates to sub-agents appropriately
5. Reduces context size through garbage collection
6. Makes similar decisions to me on real tasks

The real test: **Can someone use House Code the way they use me?**
