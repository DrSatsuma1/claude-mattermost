"""Mattermost API client wrapper."""

import os
import logging
import requests
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class MattermostClient:
    """Wrapper for Mattermost API operations using REST API."""

    def __init__(self, url: str, token: str, scheme: str = "https", port: int = 443):
        """Initialize Mattermost client.

        Args:
            url: Mattermost server URL (can include scheme)
            token: Bot access token
            scheme: URL scheme (http or https) - ignored if URL has scheme
            port: Server port - ignored if URL has scheme
        """
        # Parse URL
        if url.startswith('http://') or url.startswith('https://'):
            self.base_url = url.rstrip('/')
        else:
            self.base_url = f"{scheme}://{url}"
            if (scheme == 'https' and port != 443) or (scheme == 'http' and port != 80):
                self.base_url += f":{port}"

        self.api_url = f"{self.base_url}/api/v4"
        self.token = token
        self.headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }

        self.team_id: Optional[str] = None
        self.channel_id: Optional[str] = None
        self.bot_user_id: Optional[str] = None

    def login(self) -> bool:
        """Authenticate with Mattermost.

        Returns:
            True if login successful
        """
        try:
            response = requests.get(
                f"{self.api_url}/users/me",
                headers=self.headers
            )
            response.raise_for_status()
            user = response.json()
            self.bot_user_id = user['id']
            logger.info(f"Logged in as {user['username']} (ID: {self.bot_user_id})")
            return True
        except Exception as e:
            logger.error(f"Login failed: {e}")
            return False

    def set_team(self, team_name: str) -> bool:
        """Set the team to use.

        Args:
            team_name: Name of the team

        Returns:
            True if team found
        """
        try:
            response = requests.get(
                f"{self.api_url}/teams/name/{team_name}",
                headers=self.headers
            )
            response.raise_for_status()
            team = response.json()
            self.team_id = team['id']
            logger.info(f"Using team: {team_name} (ID: {self.team_id})")
            return True
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.error(f"Team not found: {team_name}")
            else:
                logger.error(f"Failed to get team: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to get team: {e}")
            return False

    def set_channel(self, channel_name: str) -> bool:
        """Set the channel to use.

        Args:
            channel_name: Name of the channel

        Returns:
            True if channel found
        """
        if not self.team_id:
            logger.error("Team must be set before setting channel")
            return False

        try:
            response = requests.get(
                f"{self.api_url}/teams/{self.team_id}/channels/name/{channel_name}",
                headers=self.headers
            )
            response.raise_for_status()
            channel = response.json()
            self.channel_id = channel['id']
            logger.info(f"Using channel: {channel_name} (ID: {self.channel_id})")
            return True
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.error(f"Channel not found: {channel_name}")
            else:
                logger.error(f"Failed to get channel: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to get channel: {e}")
            return False

    def create_thread(self, message: str) -> Optional[str]:
        """Create a new thread in the configured channel.

        Args:
            message: Initial message to post

        Returns:
            Post ID of the created thread, or None if failed
        """
        if not self.channel_id:
            logger.error("Channel must be set before creating thread")
            return None

        try:
            response = requests.post(
                f"{self.api_url}/posts",
                headers=self.headers,
                json={
                    'channel_id': self.channel_id,
                    'message': message
                }
            )
            response.raise_for_status()
            post = response.json()
            logger.info(f"Created thread: {post['id']}")
            return post['id']
        except Exception as e:
            logger.error(f"Failed to create thread: {e}")
            return None

    def post_to_thread(self, thread_id: str, message: str) -> bool:
        """Post a message to an existing thread.

        Args:
            thread_id: ID of the thread (root post ID)
            message: Message to post

        Returns:
            True if successful
        """
        if not self.channel_id:
            logger.error("Channel must be set before posting")
            return False

        try:
            response = requests.post(
                f"{self.api_url}/posts",
                headers=self.headers,
                json={
                    'channel_id': self.channel_id,
                    'message': message,
                    'root_id': thread_id
                }
            )
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Failed to post to thread: {e}")
            return False

    def get_thread_posts(self, thread_id: str) -> list:
        """Get all posts in a thread.

        Args:
            thread_id: ID of the thread

        Returns:
            List of posts in the thread
        """
        try:
            response = requests.get(
                f"{self.api_url}/posts/{thread_id}/thread",
                headers=self.headers
            )
            response.raise_for_status()
            data = response.json()
            posts = data['posts']
            # Sort by create_at timestamp
            sorted_posts = sorted(
                posts.values(),
                key=lambda p: p['create_at']
            )
            return sorted_posts
        except Exception as e:
            logger.error(f"Failed to get thread posts: {e}")
            return []

    def get_latest_reply(self, thread_id: str) -> Optional[Dict[str, Any]]:
        """Get the latest reply in a thread (excluding bot's own posts).

        Args:
            thread_id: ID of the thread

        Returns:
            Latest post dict, or None if no replies
        """
        posts = self.get_thread_posts(thread_id)
        if not posts:
            return None

        # Filter out bot's own posts and get latest
        user_posts = [p for p in posts if p['user_id'] != self.bot_user_id]
        if not user_posts:
            return None

        return user_posts[-1]

    def update_post(self, post_id: str, message: str) -> bool:
        """Update an existing post.

        Args:
            post_id: ID of the post to update
            message: New message content

        Returns:
            True if successful
        """
        try:
            response = requests.put(
                f"{self.api_url}/posts/{post_id}/patch",
                headers=self.headers,
                json={'message': message}
            )
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Failed to update post: {e}")
            return False
