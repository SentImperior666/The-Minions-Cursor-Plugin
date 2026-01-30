"""
Command-line interface for The Minions Cursor Plugin.

Usage:
    minions start              - Start monitoring Cursor chats
    minions status             - Show status of all minions
    minions spawn <chat_uid>   - Spawn a minion for a specific chat
    minions stop <minion_id>   - Stop a specific minion
    minions call <phone>       - Call a phone number with summary
"""

import argparse
import logging
import signal
import sys
from typing import Optional

from .core import Minion, MinionManager
from .cursor import CursorDatabase, ChatMessage
from .database import RedisDatabase

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger('minions')


class MinionsApp:
    """Main application class."""
    
    def __init__(self):
        self.manager: Optional[MinionManager] = None
        self._running = False
    
    def start(
        self,
        auto_spawn: bool = True,
        poll_interval: float = 2.0,
        redis_host: str = "localhost",
        redis_port: int = 6379,
    ) -> None:
        """Start the minions manager."""
        logger.info("Starting The Minions Cursor Plugin...")
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # Initialize Redis
        redis = RedisDatabase(host=redis_host, port=redis_port)
        
        # Initialize manager
        self.manager = MinionManager(
            redis_db=redis,
            auto_spawn=auto_spawn,
            poll_interval=poll_interval,
        )
        
        # Set up callbacks
        self.manager.set_callbacks(
            on_new_message=self._on_new_message,
            on_minion_created=self._on_minion_created,
        )
        
        self._running = True
        
        try:
            # Start monitoring (blocking)
            self.manager.start(blocking=True)
        except KeyboardInterrupt:
            logger.info("Received interrupt, shutting down...")
        finally:
            self.stop()
    
    def stop(self) -> None:
        """Stop the application."""
        self._running = False
        if self.manager:
            self.manager.stop()
        logger.info("The Minions Cursor Plugin stopped.")
    
    def _signal_handler(self, signum, frame) -> None:
        """Handle termination signals."""
        logger.info("Received signal %d, shutting down...", signum)
        self.stop()
        sys.exit(0)
    
    def _on_new_message(self, message: ChatMessage) -> None:
        """Callback for new messages."""
        logger.info("New message in %s: [%s] %s",
                   message.chat_uid[:8],
                   message.role,
                   message.content[:50] + "..." if len(message.content) > 50 else message.content)
    
    def _on_minion_created(self, minion: Minion) -> None:
        """Callback for minion creation."""
        logger.info("Minion created: %s (%s) for chat %s",
                   minion.minion_id, minion.name, minion.chat_uid[:8])
    
    def status(self) -> None:
        """Show status of all minions."""
        redis = RedisDatabase()
        redis.connect()
        
        # Get all minion IDs
        minion_keys = redis.keys("minion:*")
        minion_ids = set()
        for key in minion_keys:
            parts = key.split(":")
            if len(parts) >= 2 and parts[1] not in ('voice', 'summaries'):
                minion_ids.add(parts[1])
        
        if not minion_ids:
            print("No minions found.")
            return
        
        print(f"\nFound {len(minion_ids)} minion(s):\n")
        print("-" * 60)
        
        for mid in minion_ids:
            info = redis.read(f"minion:{mid}")
            if info:
                print(f"ID: {mid}")
                print(f"  Name: {info.get('minion_name', 'Unknown')}")
                print(f"  Chat: {info.get('chat_uid', 'Unknown')}")
                print(f"  Created: {info.get('created_at', 'Unknown')}")
                
                # Get summary count
                summaries = redis.list_get(f"minion:{mid}:summaries")
                print(f"  Summaries: {len(summaries)}")
                print("-" * 60)
        
        redis.disconnect()
    
    def spawn(self, chat_uid: str) -> None:
        """Spawn a minion for a specific chat."""
        redis = RedisDatabase()
        redis.connect()
        
        try:
            minion = Minion.spawn(chat_uid, redis_db=redis)
            print(f"Spawned minion: {minion.name} (ID: {minion.minion_id})")
            print(f"Monitoring chat: {chat_uid}")
        except Exception as e:
            print(f"Error spawning minion: {e}")
        finally:
            redis.disconnect()
    
    def list_chats(self) -> None:
        """List available Cursor chats."""
        try:
            db = CursorDatabase()
            chats = db.get_active_chats()
            
            if not chats:
                print("No Cursor chats found.")
                return
            
            print(f"\nFound {len(chats)} chat(s):\n")
            
            for uid in chats:
                chat = db.get_chat(uid)
                if chat:
                    title = chat.title or f"Chat {uid[:8]}"
                    print(f"  {uid[:16]}... - {title} ({chat.message_count} messages)")
                else:
                    print(f"  {uid[:16]}... - (unable to load)")
        
        except Exception as e:
            print(f"Error reading Cursor database: {e}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="The Minions Cursor Plugin - Monitor Cursor chats and get phone call summaries",
        prog="minions",
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Start command
    start_parser = subparsers.add_parser("start", help="Start monitoring Cursor chats")
    start_parser.add_argument(
        "--no-auto-spawn",
        action="store_true",
        help="Don't automatically spawn minions for new chats",
    )
    start_parser.add_argument(
        "--poll-interval",
        type=float,
        default=2.0,
        help="Seconds between database polls (default: 2.0)",
    )
    start_parser.add_argument(
        "--redis-host",
        default="localhost",
        help="Redis server host (default: localhost)",
    )
    start_parser.add_argument(
        "--redis-port",
        type=int,
        default=6379,
        help="Redis server port (default: 6379)",
    )
    
    # Status command
    subparsers.add_parser("status", help="Show status of all minions")
    
    # Spawn command
    spawn_parser = subparsers.add_parser("spawn", help="Spawn a minion for a specific chat")
    spawn_parser.add_argument("chat_uid", help="Chat UID to monitor")
    
    # List chats command
    subparsers.add_parser("chats", help="List available Cursor chats")
    
    # Version
    parser.add_argument(
        "--version",
        action="version",
        version="The Minions Cursor Plugin v0.1.0",
    )
    
    args = parser.parse_args()
    
    app = MinionsApp()
    
    if args.command == "start":
        app.start(
            auto_spawn=not args.no_auto_spawn,
            poll_interval=args.poll_interval,
            redis_host=args.redis_host,
            redis_port=args.redis_port,
        )
    elif args.command == "status":
        app.status()
    elif args.command == "spawn":
        app.spawn(args.chat_uid)
    elif args.command == "chats":
        app.list_chats()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
