#!/bin/bash
# Claude Code hook: Called on notifications
# Sends notifications to Mattermost thread

# Get notification data
MESSAGE="${CLAUDE_NOTIFICATION_MESSAGE}"
SESSION_ID="${CLAUDE_SESSION_ID}"

# Path to daemon communication script
DAEMON_DIR="$HOME/.claude/claude-mattermost"
PYTHON_SCRIPT="$DAEMON_DIR/hooks/send_notification.py"

# Call Python script to send notification
if [ -f "$PYTHON_SCRIPT" ]; then
    python3 "$PYTHON_SCRIPT" \
        --session-id "$SESSION_ID" \
        --message "$MESSAGE"
fi

exit 0
