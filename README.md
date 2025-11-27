# Claude-Mattermost Integration

Control Claude Code CLI sessions from your mobile device using Mattermost.

## What This Does

- Start Claude Code sessions in your terminal
- Continue conversations from Mattermost (desktop or mobile)
- Approve tool executions remotely
- See command outputs and responses in Mattermost threads
- Maintain session context across devices

## Architecture

```
Terminal (Claude Code)  ←→  Bot Daemon  ←→  Mattermost Server
                              ↓
                          SQLite DB
                        (session registry)
```

**Components:**
- **Claude Code Hooks**: Intercept tool executions and send to Mattermost
- **Bot Daemon**: Listens for Mattermost messages, manages sessions
- **Session Registry**: Maps Claude sessions to Mattermost threads
- **Mattermost Bot**: Posts updates and receives user input

## Requirements

- Python 3.9+
- Claude Code CLI installed
- Mattermost server (self-hosted or cloud)
- Mattermost bot account with API token

## Quick Start

### 1. Create Mattermost Bot

1. Log into Mattermost as admin
2. Go to **System Console** → **Integrations** → **Bot Accounts**
3. Click **Add Bot Account**
   - Username: `claude-bot`
   - Display Name: `Claude Code`
   - Description: `Claude Code CLI integration`
   - Role: `Member`
4. Click **Create Bot Account**
5. Copy the **Access Token** (you'll need this)

### 2. Install Claude-Mattermost

```bash
# Clone repository
git clone https://github.com/DrSatsuma/claude-mattermost.git
cd claude-mattermost

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.template .env
# Edit .env with your settings:
# - MATTERMOST_URL
# - MATTERMOST_BOT_TOKEN
# - MATTERMOST_TEAM_NAME
# - MATTERMOST_CHANNEL_NAME

# Install hooks and start daemon
./install.sh
```

### 3. Initialize in a Project

```bash
cd ~/your-project
claude-mattermost init
```

This creates a Mattermost thread for this project and links your Claude session.

### 4. Start Using

**In Terminal:**
```bash
claude
```

**In Mattermost:**
- Go to the channel you configured
- Find the thread for your project
- Continue the conversation
- Approve tool executions when prompted

## Usage

### Starting a Session

```bash
# In your project directory
claude
```

A new thread appears in your Mattermost channel with session info.

### Continuing from Mobile

1. Open Mattermost app
2. Navigate to your configured channel
3. Find the thread for your project
4. Type messages to Claude
5. Approve/deny tool executions

### Approving Tools

When Claude wants to execute a command, you'll see:

```
🔧 Tool Request: Bash

Command: npm install axios
Description: Install axios package

Reply with:
✅ approve
❌ deny
```

### Ending a Session

In terminal: Exit Claude normally (`/exit` or Ctrl+D)

The Mattermost thread will show:
```
✓ Session ended
```

## Configuration

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `MATTERMOST_URL` | Your Mattermost server URL | `https://mattermost.example.com` |
| `MATTERMOST_BOT_TOKEN` | Bot access token | `abc123...` |
| `MATTERMOST_TEAM_NAME` | Team name for bot | `engineering` |
| `MATTERMOST_CHANNEL_NAME` | Channel for threads | `claude-sessions` |
| `SESSION_TIMEOUT_HOURS` | Session timeout (default: 24) | `48` |

### Advanced Options

Edit `~/.claude/claude-mattermost/config.json`:

```json
{
  "thread_prefix": "🤖",
  "permission_required": true,
  "notify_on_completion": true,
  "show_tool_output": true
}
```

## Commands

```bash
# Initialize project
claude-mattermost init

# List active sessions
claude-mattermost sessions

# End a session
claude-mattermost end <session_id>

# Test connection
claude-mattermost test

# View logs
claude-mattermost logs

# Cleanup old sessions
claude-mattermost cleanup
```

## Troubleshooting

### Bot not responding

```bash
# Check daemon status
claude-mattermost status

# Restart daemon
claude-mattermost restart

# Check logs
tail -f ~/.claude/claude-mattermost/logs/daemon.log
```

### Messages not appearing

1. Verify bot is in the channel: `/invite @claude-bot`
2. Check bot permissions in System Console
3. Verify token hasn't expired

### Session not found

```bash
# Reinitialize project
cd ~/your-project
claude-mattermost init --force
```

## How It Works

### Session Lifecycle

1. **Start**: `claude` command triggers `on_notification` hook
2. **Register**: Session ID + project path → Mattermost thread
3. **Execute**: Tool requests → Mattermost for approval
4. **Response**: User replies in Mattermost → CLI continues
5. **End**: Session closes → Thread marked complete

### Hook Integration

Claude Code hooks are installed at:
- `~/.claude/hooks/on_notification.sh` - Session events
- `~/.claude/hooks/on_stop.sh` - Response completion
- `~/.claude/hooks/pre_tool_use.sh` - Tool execution requests

### Data Storage

SQLite database at `~/.claude/claude-mattermost/sessions.db`:

```sql
sessions (
  id TEXT PRIMARY KEY,
  project_path TEXT,
  thread_id TEXT,
  channel_id TEXT,
  created_at TIMESTAMP,
  last_active TIMESTAMP,
  status TEXT
)
```

## Security Considerations

- Bot token grants full API access - keep `.env` secure
- Tool execution approval prevents unauthorized commands
- Sessions timeout after inactivity (default: 24 hours)
- All communication over HTTPS (configure your Mattermost server)

## Development

### Running Tests

```bash
pytest tests/
```

### Project Structure

```
claude-mattermost/
├── core/
│   ├── daemon.py          # Main bot daemon
│   ├── session_manager.py # Session registry
│   ├── mattermost_client.py # API wrapper
│   └── hooks.py           # Hook handlers
├── hooks/
│   ├── on_notification.sh
│   ├── on_stop.sh
│   └── pre_tool_use.sh
├── bin/
│   └── claude-mattermost  # CLI executable
├── tests/
├── install.sh
├── requirements.txt
├── .env.template
└── README.md
```

## License

MIT

## Contributing

Issues and PRs welcome at https://github.com/DrSatsuma/claude-mattermost

## Credits

Inspired by [claude-slack](https://github.com/dbenn8/claude-slack)
