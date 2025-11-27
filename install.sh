#!/bin/bash
# Installation script for Claude-Mattermost

set -e

echo "Installing Claude-Mattermost..."

# Directories
INSTALL_DIR="$HOME/.claude/claude-mattermost"
HOOKS_DIR="$HOME/.claude/hooks"
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"

# Create directories
mkdir -p "$INSTALL_DIR"
mkdir -p "$INSTALL_DIR/logs"
mkdir -p "$INSTALL_DIR/responses"
mkdir -p "$INSTALL_DIR/input"
mkdir -p "$HOOKS_DIR"

# Copy files
echo "Copying files to $INSTALL_DIR..."
cp -r "$REPO_DIR/core" "$INSTALL_DIR/"
cp -r "$REPO_DIR/hooks" "$INSTALL_DIR/"
cp "$REPO_DIR/requirements.txt" "$INSTALL_DIR/"

# Copy .env if doesn't exist
if [ ! -f "$INSTALL_DIR/.env" ]; then
    if [ -f "$REPO_DIR/.env" ]; then
        cp "$REPO_DIR/.env" "$INSTALL_DIR/"
    else
        cp "$REPO_DIR/.env.template" "$INSTALL_DIR/.env"
        echo "⚠️  Please edit $INSTALL_DIR/.env with your Mattermost settings"
    fi
fi

# Install Python dependencies
echo "Installing Python dependencies..."
pip3 install -r "$INSTALL_DIR/requirements.txt"

# Install hooks (backup existing if present)
echo "Installing Claude Code hooks..."

for hook in pre_tool_use on_notification on_stop; do
    HOOK_FILE="$HOOKS_DIR/${hook}.sh"

    if [ -f "$HOOK_FILE" ]; then
        BACKUP="$HOOK_FILE.backup.$(date +%s)"
        echo "  Backing up existing $hook hook to $BACKUP"
        mv "$HOOK_FILE" "$BACKUP"
    fi

    cp "$INSTALL_DIR/hooks/${hook}.sh" "$HOOK_FILE"
    chmod +x "$HOOK_FILE"
    echo "  Installed $hook hook"
done

# Add bin to PATH (if not already)
BIN_DIR="$REPO_DIR/bin"

if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    echo "Adding $BIN_DIR to PATH..."

    # Detect shell
    if [ -n "$ZSH_VERSION" ]; then
        SHELL_RC="$HOME/.zshrc"
    elif [ -n "$BASH_VERSION" ]; then
        SHELL_RC="$HOME/.bashrc"
    else
        SHELL_RC="$HOME/.profile"
    fi

    echo "" >> "$SHELL_RC"
    echo "# Claude-Mattermost" >> "$SHELL_RC"
    echo "export PATH=\"$BIN_DIR:\$PATH\"" >> "$SHELL_RC"

    echo "  Added to $SHELL_RC"
    echo "  Run: source $SHELL_RC"
fi

# Start daemon
echo "Starting daemon..."
cd "$INSTALL_DIR"
nohup python3 -m core.daemon > "$INSTALL_DIR/logs/daemon.log" 2>&1 &
DAEMON_PID=$!

echo "  Daemon started (PID: $DAEMON_PID)"

# Done
echo ""
echo "✓ Installation complete!"
echo ""
echo "Next steps:"
echo "1. Edit configuration: $INSTALL_DIR/.env"
echo "2. Restart daemon: claude-mattermost restart"
echo "3. Test connection: claude-mattermost test"
echo "4. Initialize a project: cd /path/to/project && claude-mattermost init"
echo ""
echo "View logs: claude-mattermost logs"
