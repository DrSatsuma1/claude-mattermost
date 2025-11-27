"""Hook handler scripts for Claude Code integration."""

import sys
import argparse
import requests
from pathlib import Path


def request_approval(session_id: str, tool_name: str, command: str, description: str) -> str:
    """Request approval for tool execution.

    Args:
        session_id: Session identifier
        tool_name: Name of the tool
        command: Command to execute
        description: Description of the command

    Returns:
        Path to response file
    """
    daemon_url = "http://localhost:9876"

    try:
        response = requests.post(
            f"{daemon_url}/request_approval",
            json={
                'session_id': session_id,
                'tool_name': tool_name,
                'command': command,
                'description': description
            },
            timeout=5
        )

        if response.status_code == 200:
            data = response.json()
            return data.get('response_file', '')
        else:
            print(f"Error: {response.status_code}", file=sys.stderr)
            return ''

    except requests.exceptions.ConnectionError:
        print("Warning: Daemon not running, allowing tool execution", file=sys.stderr)
        return ''
    except Exception as e:
        print(f"Error requesting approval: {e}", file=sys.stderr)
        return ''


def send_notification(session_id: str, message: str):
    """Send notification to Mattermost.

    Args:
        session_id: Session identifier
        message: Notification message
    """
    daemon_url = "http://localhost:9876"

    try:
        requests.post(
            f"{daemon_url}/notification",
            json={
                'session_id': session_id,
                'message': message
            },
            timeout=5
        )
    except Exception as e:
        print(f"Error sending notification: {e}", file=sys.stderr)


def send_response(session_id: str, response: str):
    """Send Claude's response to Mattermost.

    Args:
        session_id: Session identifier
        response: Response text
    """
    daemon_url = "http://localhost:9876"

    try:
        requests.post(
            f"{daemon_url}/response",
            json={
                'session_id': session_id,
                'response': response
            },
            timeout=5
        )
    except Exception as e:
        print(f"Error sending response: {e}", file=sys.stderr)


def main_request_approval():
    """CLI entry point for requesting approval."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--session-id', required=True)
    parser.add_argument('--tool-name', required=True)
    parser.add_argument('--command', required=True)
    parser.add_argument('--description', required=True)
    args = parser.parse_args()

    response_file = request_approval(
        args.session_id,
        args.tool_name,
        args.command,
        args.description
    )

    print(response_file)


def main_send_notification():
    """CLI entry point for sending notification."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--session-id', required=True)
    parser.add_argument('--message', required=True)
    args = parser.parse_args()

    send_notification(args.session_id, args.message)


def main_send_response():
    """CLI entry point for sending response."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--session-id', required=True)
    parser.add_argument('--response', required=True)
    args = parser.parse_args()

    send_response(args.session_id, args.response)


if __name__ == '__main__':
    if 'request_approval' in sys.argv[0]:
        main_request_approval()
    elif 'send_notification' in sys.argv[0]:
        main_send_notification()
    elif 'send_response' in sys.argv[0]:
        main_send_response()
