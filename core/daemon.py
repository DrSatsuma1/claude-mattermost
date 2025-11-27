"""Main daemon for Claude-Mattermost integration."""

import os
import sys
import time
import json
import logging
import signal
from pathlib import Path
from typing import Optional, Dict, Any
from dotenv import load_dotenv

from core.mattermost_client import MattermostClient
from core.session_manager import SessionManager

# Configure logging
LOG_DIR = Path.home() / ".claude" / "claude-mattermost" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "daemon.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ClaudeMattermostDaemon:
    """Main daemon that manages Claude-Mattermost integration."""

    def __init__(self):
        """Initialize daemon."""
        self.running = False
        self.client: Optional[MattermostClient] = None
        self.session_manager: Optional[SessionManager] = None
        self.config: Dict[str, Any] = {}
        self.pending_approvals: Dict[str, Dict[str, Any]] = {}

        # Load environment
        load_dotenv()
        self._load_config()

    def _load_config(self):
        """Load configuration from environment."""
        self.config = {
            'mattermost_url': os.getenv('MATTERMOST_URL', ''),
            'mattermost_token': os.getenv('MATTERMOST_BOT_TOKEN', ''),
            'team_name': os.getenv('MATTERMOST_TEAM_NAME', ''),
            'channel_name': os.getenv('MATTERMOST_CHANNEL_NAME', ''),
            'session_timeout': int(os.getenv('SESSION_TIMEOUT_HOURS', '24')),
            'log_level': os.getenv('LOG_LEVEL', 'INFO')
        }

        # Validate required config
        required = ['mattermost_url', 'mattermost_token', 'team_name', 'channel_name']
        missing = [k for k in required if not self.config[k]]
        if missing:
            raise ValueError(f"Missing required config: {', '.join(missing)}")

        # Set log level
        logging.getLogger().setLevel(self.config['log_level'])

    def start(self):
        """Start the daemon."""
        logger.info("Starting Claude-Mattermost daemon...")

        # Initialize Mattermost client
        url = self.config['mattermost_url']
        token = self.config['mattermost_token']

        # Parse URL
        if url.startswith('https://'):
            scheme = 'https'
            port = 443
        elif url.startswith('http://'):
            scheme = 'http'
            port = 80
        else:
            scheme = 'https'
            port = 443

        self.client = MattermostClient(url, token, scheme, port)

        if not self.client.login():
            logger.error("Failed to login to Mattermost")
            return False

        if not self.client.set_team(self.config['team_name']):
            logger.error(f"Failed to set team: {self.config['team_name']}")
            return False

        if not self.client.set_channel(self.config['channel_name']):
            logger.error(f"Failed to set channel: {self.config['channel_name']}")
            return False

        # Initialize session manager
        db_path = Path.home() / ".claude" / "claude-mattermost" / "sessions.db"
        self.session_manager = SessionManager(str(db_path))

        # Register signal handlers
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

        self.running = True
        logger.info("Daemon started successfully")

        # Main loop
        self._run_loop()

        return True

    def _run_loop(self):
        """Main daemon loop."""
        cleanup_interval = 3600  # 1 hour
        last_cleanup = time.time()

        while self.running:
            try:
                # Check for new messages
                self._process_messages()

                # Periodic cleanup
                if time.time() - last_cleanup > cleanup_interval:
                    self._cleanup_sessions()
                    last_cleanup = time.time()

                # Sleep to avoid tight loop
                time.sleep(2)

            except Exception as e:
                logger.error(f"Error in main loop: {e}", exc_info=True)
                time.sleep(5)

    def _process_messages(self):
        """Process new messages from Mattermost."""
        # Get active sessions
        sessions = self.session_manager.get_active_sessions()

        for session in sessions:
            thread_id = session['thread_id']

            # Check for new replies
            latest_reply = self.client.get_latest_reply(thread_id)
            if not latest_reply:
                continue

            message = latest_reply['message'].strip()

            # Check if this is an approval response
            if thread_id in self.pending_approvals:
                self._handle_approval_response(session, message)
            else:
                # Regular message - forward to Claude
                self._handle_user_message(session, message)

    def _handle_approval_response(self, session: Dict[str, Any], message: str):
        """Handle approval/denial of tool execution.

        Args:
            session: Session dict
            message: User's response message
        """
        thread_id = session['thread_id']
        approval_data = self.pending_approvals.get(thread_id)

        if not approval_data:
            return

        # Parse response
        message_lower = message.lower()
        approved = any(word in message_lower for word in ['approve', 'yes', '✅', 'ok'])
        denied = any(word in message_lower for word in ['deny', 'no', '❌', 'cancel'])

        if not (approved or denied):
            # Not a clear response, prompt again
            self.client.post_to_thread(
                thread_id,
                "Please reply with:\n✅ **approve** to proceed\n❌ **deny** to cancel"
            )
            return

        # Write response to approval file
        response_file = approval_data['response_file']
        with open(response_file, 'w') as f:
            f.write('approved' if approved else 'denied')

        # Notify in thread
        if approved:
            self.client.post_to_thread(thread_id, "✅ Approved - executing...")
        else:
            self.client.post_to_thread(thread_id, "❌ Denied - skipping")

        # Clear pending approval
        del self.pending_approvals[thread_id]

        # Update session activity
        self.session_manager.update_activity(session['id'])

    def _handle_user_message(self, session: Dict[str, Any], message: str):
        """Handle regular user message.

        Args:
            session: Session dict
            message: User's message
        """
        # Write message to input file for Claude to read
        input_file = Path.home() / ".claude" / "claude-mattermost" / "input" / f"{session['id']}.txt"
        input_file.parent.mkdir(parents=True, exist_ok=True)

        with open(input_file, 'w') as f:
            f.write(message)

        logger.info(f"Received message for session {session['id']}: {message[:50]}...")

        # Update session activity
        self.session_manager.update_activity(session['id'])

    def _cleanup_sessions(self):
        """Clean up old sessions."""
        timeout = self.config['session_timeout']
        count = self.session_manager.cleanup_old_sessions(timeout)
        if count > 0:
            logger.info(f"Cleaned up {count} timed-out sessions")

    def _handle_shutdown(self, signum, frame):
        """Handle shutdown signal.

        Args:
            signum: Signal number
            frame: Current stack frame
        """
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False

    def handle_tool_request(
        self,
        session_id: str,
        tool_name: str,
        command: str,
        description: str
    ) -> str:
        """Handle tool execution request from Claude.

        Args:
            session_id: Session identifier
            tool_name: Name of the tool
            command: Command to execute
            description: Description of what the command does

        Returns:
            Path to response file
        """
        session = self.session_manager.get_session(session_id)
        if not session:
            logger.error(f"Session not found: {session_id}")
            return ""

        thread_id = session['thread_id']

        # Format approval request
        message = f"""🔧 **Tool Request: {tool_name}**

**Command:** `{command}`

**Description:** {description}

Reply with:
✅ **approve** to execute
❌ **deny** to skip"""

        # Post to thread
        self.client.post_to_thread(thread_id, message)

        # Create response file
        response_dir = Path.home() / ".claude" / "claude-mattermost" / "responses"
        response_dir.mkdir(parents=True, exist_ok=True)
        response_file = response_dir / f"{session_id}.txt"

        # Track pending approval
        self.pending_approvals[thread_id] = {
            'session_id': session_id,
            'tool_name': tool_name,
            'command': command,
            'response_file': str(response_file)
        }

        # Update activity
        self.session_manager.update_activity(session_id)

        return str(response_file)

    def handle_notification(self, session_id: str, message: str):
        """Handle notification from Claude.

        Args:
            session_id: Session identifier
            message: Notification message
        """
        session = self.session_manager.get_session(session_id)
        if not session:
            logger.error(f"Session not found: {session_id}")
            return

        thread_id = session['thread_id']
        self.client.post_to_thread(thread_id, message)

        # Update activity
        self.session_manager.update_activity(session_id)

    def handle_session_end(self, session_id: str):
        """Handle session end notification.

        Args:
            session_id: Session identifier
        """
        session = self.session_manager.get_session(session_id)
        if not session:
            return

        thread_id = session['thread_id']
        self.client.post_to_thread(thread_id, "✓ **Session ended**")

        # Mark session as ended
        self.session_manager.end_session(session_id)


def main():
    """Main entry point."""
    try:
        daemon = ClaudeMattermostDaemon()
        daemon.start()
    except KeyboardInterrupt:
        logger.info("Daemon stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
