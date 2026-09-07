# DeepSeek Harness (DSH) Integration Guide

## Overview
DeepSeek Harness (DSH) provides specialized harness environments for DeepSeek-Coder models. `agent-bus-mcp` connects DSH to Antigravity and Claude Code.

## Configuration

1. Install the doorbell listener:
```bash
dsh-doorbell deepseek-coder &
```

2. Send messages to DSH from any agent:
```bash
agent-bus send --to deepseek-coder --topic code_gen "Please implement the order book matching module."
```

3. DSH replies back:
```bash
agent-bus send --to coordinator --from deepseek-coder --topic code_gen "Implementation ready in workbench/execution/matcher.py"
```
