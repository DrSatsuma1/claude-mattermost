"""Mattermost API client wrapper."""

import os
import logging
from typing import Optional, Dict, Any
from mattermostdriver import Driver
from mattermostdriver.exceptions import ResourceNotFound

logger = logging.getLogger(__name__)


class MattermostClient:
    """Wrapper for Mattermost API operations."""

    def __init__(self, url: str, token: str, scheme: str = "https", port: int = 443):
        """Initialize Mattermost client.

        Args:
            url: Mattermost server URL (without scheme)
            token: Bot access token
            scheme: URL scheme (http or https)
            port: Server port
        """
        # Remove scheme if present in URL
        url = url.replace("https://", "").replace("http://", "")

        self.driver = Driver({
            'url': url,
            'token': token,
            'scheme': scheme,
            'port': port,
            'verify': True
        })

        self.team_id: Optional[str] = None
        self.channel_id: Optional[str] = None
        self.bot_user_id: Optional[str] = None

    def login(self) -> bool:
        """Authenticate with Mattermost.

        Returns:
            True if login successful
        """
        try:
            self.driver.login()
            user = self.driver.users.get_user('me')
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
            team = self.driver.teams.get_team_by_name(team_name)
            self.team_id = team['id']
            logger.info(f"Using team: {team_name} (ID: {self.team_id})")
            return True
        except ResourceNotFound:
            logger.error(f"Team not found: {team_name}")
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
            channel = self.driver.channels.get_channel_by_name(
                self.team_id,
                channel_name
            )
            self.channel_id = channel['id']
            logger.info(f"Using channel: {channel_name} (ID: {self.channel_id})")
            return True
        except ResourceNotFound:
            logger.error(f"Channel not found: {channel_name}")
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
            post = self.driver.posts.create_post({
                'channel_id': self.channel_id,
                'message': message
            })
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
            self.driver.posts.create_post({
                'channel_id': self.channel_id,
                'message': message,
                'root_id': thread_id
            })
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
            response = self.driver.posts.get_thread(thread_id)
            posts = response['posts']
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
            self.driver.posts.patch_post(post_id, {'message': message})
            return True
        except Exception as e:
            logger.error(f"Failed to update post: {e}")
            return False
