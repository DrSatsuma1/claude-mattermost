#!/bin/bash
# Claude Code hook: Called before tool execution
# Sends tool request to Mattermost for approval

# Get hook data from environment
TOOL_NAME="${CLAUDE_TOOL_NAME}"
COMMAND="${CLAUDE_TOOL_COMMAND}"
DESCRIPTION="${CLAUDE_TOOL_DESCRIPTION}"
SESSION_ID="${CLAUDE_SESSION_ID}"

# Path to daemon communication script
DAEMON_DIR="$HOME/.claude/claude-mattermost"
PYTHON_SCRIPT="$DAEMON_DIR/hooks/request_approval.py"

# Call Python script to request approval
if [ -f "$PYTHON_SCRIPT" ]; then
    RESPONSE_FILE=$(python3 "$PYTHON_SCRIPT" \
        --session-id "$SESSION_ID" \
        --tool-name "$TOOL_NAME" \
        --command "$COMMAND" \
        --description "$DESCRIPTION")

    # Wait for response (with timeout)
    TIMEOUT=300  # 5 minutes
    ELAPSED=0

    while [ $ELAPSED -lt $TIMEOUT ]; do
        if [ -f "$RESPONSE_FILE" ]; then
            RESPONSE=$(cat "$RESPONSE_FILE")
            rm -f "$RESPONSE_FILE"

            if [ "$RESPONSE" = "approved" ]; then
                exit 0  # Allow execution
            else
                exit 1  # Block execution
            fi
        fi

        sleep 1
        ELAPSED=$((ELAPSED + 1))
    done

    # Timeout - deny by default
    echo "Approval timeout - denying tool execution" >&2
    exit 1
else
    # No daemon - allow by default
    exit 0
fi
