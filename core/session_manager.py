"""Session registry for managing Claude-Mattermost sessions."""

import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages Claude Code sessions and their Mattermost thread mappings."""

    def __init__(self, db_path: str):
        """Initialize session manager.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                project_path TEXT NOT NULL,
                thread_id TEXT NOT NULL,
                channel_id TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL,
                last_active TIMESTAMP NOT NULL,
                status TEXT NOT NULL DEFAULT 'active'
            )
        """)

        conn.commit()
        conn.close()
        logger.info(f"Database initialized at {self.db_path}")

    def create_session(
        self,
        session_id: str,
        project_path: str,
        thread_id: str,
        channel_id: str
    ) -> bool:
        """Create a new session.

        Args:
            session_id: Unique session identifier
            project_path: Absolute path to project directory
            thread_id: Mattermost thread ID
            channel_id: Mattermost channel ID

        Returns:
            True if created successfully
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            now = datetime.now()
            cursor.execute("""
                INSERT INTO sessions (
                    id, project_path, thread_id, channel_id,
                    created_at, last_active, status
                ) VALUES (?, ?, ?, ?, ?, ?, 'active')
            """, (session_id, project_path, thread_id, channel_id, now, now))

            conn.commit()
            conn.close()

            logger.info(f"Created session {session_id} for {project_path}")
            return True
        except sqlite3.IntegrityError:
            logger.error(f"Session {session_id} already exists")
            return False
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            return False

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session by ID.

        Args:
            session_id: Session identifier

        Returns:
            Session dict or None if not found
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                "SELECT * FROM sessions WHERE id = ?",
                (session_id,)
            )
            row = cursor.fetchone()
            conn.close()

            if row:
                return dict(row)
            return None
        except Exception as e:
            logger.error(f"Failed to get session: {e}")
            return None

    def get_session_by_thread(self, thread_id: str) -> Optional[Dict[str, Any]]:
        """Get session by thread ID.

        Args:
            thread_id: Mattermost thread ID

        Returns:
            Session dict or None if not found
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                "SELECT * FROM sessions WHERE thread_id = ? AND status = 'active'",
                (thread_id,)
            )
            row = cursor.fetchone()
            conn.close()

            if row:
                return dict(row)
            return None
        except Exception as e:
            logger.error(f"Failed to get session by thread: {e}")
            return None

    def get_active_sessions(self) -> List[Dict[str, Any]]:
        """Get all active sessions.

        Returns:
            List of session dicts
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                "SELECT * FROM sessions WHERE status = 'active' ORDER BY last_active DESC"
            )
            rows = cursor.fetchall()
            conn.close()

            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get active sessions: {e}")
            return []

    def update_activity(self, session_id: str) -> bool:
        """Update last activity timestamp for a session.

        Args:
            session_id: Session identifier

        Returns:
            True if updated successfully
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE sessions
                SET last_active = ?
                WHERE id = ?
            """, (datetime.now(), session_id))

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Failed to update activity: {e}")
            return False

    def end_session(self, session_id: str) -> bool:
        """Mark a session as ended.

        Args:
            session_id: Session identifier

        Returns:
            True if updated successfully
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE sessions
                SET status = 'ended'
                WHERE id = ?
            """, (session_id,))

            conn.commit()
            conn.close()

            logger.info(f"Ended session {session_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to end session: {e}")
            return False

    def cleanup_old_sessions(self, timeout_hours: int = 24) -> int:
        """Clean up sessions that haven't been active recently.

        Args:
            timeout_hours: Hours of inactivity before cleanup

        Returns:
            Number of sessions cleaned up
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cutoff = datetime.now() - timedelta(hours=timeout_hours)

            cursor.execute("""
                UPDATE sessions
                SET status = 'timeout'
                WHERE status = 'active'
                AND last_active < ?
            """, (cutoff,))

            count = cursor.rowcount
            conn.commit()
            conn.close()

            logger.info(f"Cleaned up {count} old sessions")
            return count
        except Exception as e:
            logger.error(f"Failed to cleanup sessions: {e}")
            return 0

    def delete_session(self, session_id: str) -> bool:
        """Permanently delete a session.

        Args:
            session_id: Session identifier

        Returns:
            True if deleted successfully
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))

            conn.commit()
            conn.close()

            logger.info(f"Deleted session {session_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete session: {e}")
            return False
