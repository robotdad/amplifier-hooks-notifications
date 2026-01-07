"""Notification Hook Module

Sends push notifications via shell script on key Amplifier events.
"""

import asyncio
import subprocess
from typing import Any, Callable
from amplifier_core.models import HookResult


class NotificationHooks:
    """Hook handlers for shell notifications."""
    
    def __init__(self, config: dict[str, Any]):
        self.notify_script = config.get("notify_script", "notify")
        self.enabled_events = config.get("enabled_events", [
            "tool:error",
            "session:end",
        ])
        self.notify_on_ask = config.get("notify_on_ask_user", True)
    
    async def handle_event(self, event: str, data: dict[str, Any]) -> HookResult:
        """Handle any event and decide if we should notify."""
        
        # Check if this event type is enabled
        if event not in self.enabled_events:
            # Special case: check for AskUserQuestion tool
            if event == "tool:post" and self.notify_on_ask:
                tool_name = data.get("tool_name", "")
                if tool_name.lower() in ["askuserquestion", "ask_user_question", "ask-user-question"]:
                    await self._send_notification(
                        "User Input Needed",
                        f"Amplifier is waiting for your input",
                        "high"
                    )
            return HookResult(action="continue")
        
        # Build notification based on event type
        title, message, priority = self._build_notification(event, data)
        
        if title and message:
            await self._send_notification(title, message, priority)
        
        return HookResult(action="continue")
    
    def _build_notification(self, event: str, data: dict[str, Any]) -> tuple[str, str, str]:
        """Build notification title, message, and priority for event."""
        
        if event == "tool:error":
            tool_name = data.get("tool_name", "Unknown")
            error = data.get("error", {})
            error_msg = error.get("message", "Unknown error") if isinstance(error, dict) else str(error)
            return ("Tool Error", f"{tool_name} failed: {error_msg}", "high")
        
        elif event == "session:end":
            session_id = data.get("session_id", "unknown")
            
            # Try to get the initial prompt to provide context
            prompt = data.get("prompt", "")
            if not prompt:
                # Fallback: try to get it from parent_prompt or initial_prompt
                prompt = data.get("parent_prompt", data.get("initial_prompt", ""))
            
            if prompt:
                # Truncate prompt to ~60 chars for notification
                preview = prompt[:60] + "..." if len(prompt) > 60 else prompt
                return ("Session Complete", f"Re: {preview}", "default")
            
            # Fallback if no prompt available
            return ("Session Complete", f"Session {session_id[:8]} ended", "default")
        
        elif event == "session:start":
            return ("Session Started", "New Amplifier session created", "default")
        
        elif event == "tool:post":
            tool_name = data.get("tool_name", "Unknown")
            return ("Tool Complete", f"{tool_name} executed successfully", "default")
        
        elif event == "prompt:submit":
            prompt = data.get("prompt", "")
            preview = prompt[:50] + "..." if len(prompt) > 50 else prompt
            return ("User Input", f"Prompt: {preview}", "default")
        
        return ("", "", "default")
    
    async def _send_notification(self, title: str, message: str, priority: str = "default") -> None:
        """Send notification via shell script."""
        try:
            # Run notification script asynchronously
            # Pass: message, title, priority
            process = await asyncio.create_subprocess_exec(
                self.notify_script,
                message,
                title,
                priority,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Don't wait for completion - fire and forget
            # This prevents blocking the agent loop
            asyncio.create_task(process.wait())
            
        except FileNotFoundError:
            # Script not found - silently continue (don't break session)
            pass
        except Exception:
            # Other errors - silently continue
            pass


async def mount(coordinator: Any, config: dict[str, Any] | None = None) -> Callable | None:
    """Mount the notification hooks module.
    
    Config options:
        notify_script: str (default: "notify") - Path to notification script
        enabled_events: list[str] - Events to notify on
            Defaults: ["tool:error", "session:end"]
            Available: ["session:start", "session:end", "tool:pre", "tool:post", 
                       "tool:error", "prompt:submit", "provider:request", "provider:response"]
        notify_on_ask_user: bool (default: True) - Notify when AskUserQuestion tool is used
    
    Example configuration in ~/.amplifier/settings.yaml:
        modules:
          hooks:
            - module: hooks-notifications
              source: git+https://github.com/yourusername/amplifier-hooks-notifications
              config:
                notify_script: "notify"
                enabled_events:
                  - "tool:error"
                  - "session:end"
                notify_on_ask_user: true
    """
    config = config or {}
    
    hooks = NotificationHooks(config)
    
    # Get enabled events from config
    enabled_events = config.get("enabled_events", ["tool:error", "session:end"])
    
    # Register handlers for each enabled event
    handlers = []
    for event in enabled_events:
        unregister = coordinator.hooks.register(
            event,
            hooks.handle_event,
            priority=90,  # Low priority - run after other hooks
            name=f"notify_{event.replace(':', '_')}"
        )
        handlers.append(unregister)
    
    # Always register tool:post handler if notify_on_ask_user is enabled
    if config.get("notify_on_ask_user", True):
        unregister = coordinator.hooks.register(
            "tool:post",
            hooks.handle_event,
            priority=90,
            name="notify_ask_user"
        )
        handlers.append(unregister)
    
    # Return cleanup function
    def cleanup():
        for unregister in handlers:
            unregister()
    
    return cleanup
