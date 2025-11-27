#!/bin/bash
# Claude Code hook: Called when Claude stops responding
# Sends completion notification to Mattermost

SESSION_ID="${CLAUDE_SESSION_ID}"
RESPONSE="${CLAUDE_RESPONSE}"

# Path to daemon communication script
DAEMON_DIR="$HOME/.claude/claude-mattermost"
PYTHON_SCRIPT="$DAEMON_DIR/hooks/send_response.py"

# Call Python script to send response
if [ -f "$PYTHON_SCRIPT" ]; then
    python3 "$PYTHON_SCRIPT" \
        --session-id "$SESSION_ID" \
        --response "$RESPONSE"
fi

exit 0
