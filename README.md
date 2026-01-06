# Amplifier Notifications Hook

Push notifications for Amplifier events via shell script integration.

## What It Does

Automatically sends push notifications when:
- ✅ Amplifier asks a question (needs user input)
- ✅ A tool encounters an error
- ✅ A session completes
- ✅ Other configurable events

## Quick Start

### 1. Create Notification Script

Create `~/bin/notify` (or use existing script):

```bash
#!/bin/bash
# Push notification via ntfy.sh
MESSAGE="${1:-Notification}"
TITLE="${2:-Amplifier}"
PRIORITY="${3:-default}"
TOPIC="${NTFY_TOPIC:-amplifier-$(whoami)}"

curl -s -H "Title: $TITLE" \
     -H "Priority: $PRIORITY" \
     -d "$MESSAGE" \
     "https://ntfy.sh/$TOPIC"
```

Make it executable:
```bash
chmod +x ~/bin/notify
```

Set your notification topic:
```bash
echo 'export NTFY_TOPIC="your-unique-topic"' >> ~/.bashrc
export NTFY_TOPIC="your-unique-topic"
```

### 2. Install Hook Module

**Local Development:**
```bash
cd hooks-notifications
pip install -e .
```

**Or from GitHub (after publishing):**
```bash
pip install git+https://github.com/yourusername/amplifier-hooks-notifications
```

### 3. Configure in Settings

**After pip install, add to `~/.amplifier/settings.yaml`:**

```yaml
modules:
  hooks:
    - module: hooks-notifications  # No source field needed after pip install
      config:
        notify_script: "notify"  # Or full path: "/Users/you/bin/notify"
        enabled_events:
          - "tool:error"
          - "session:end"
        notify_on_ask_user: true
```

**That's it!** Every Amplifier session will now send notifications, regardless of bundle.

**Alternative: Include source for auto-install** (useful when sharing config):
```yaml
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
```

The `source:` field triggers auto-installation if the module isn't already available. For local development, omit it after pip install.

### 4. Install ntfy App

Subscribe to notifications on your phone:
- **iOS**: https://apps.apple.com/app/ntfy/id1625396347
- **Android**: https://play.google.com/store/apps/details?id=io.heckel.ntfy

Open app, tap **+**, enter your topic name.

## Configuration Options

```yaml
config:
  # Path or command name for notification script
  notify_script: "notify"  # Default: "notify" (must be in PATH)
  
  # Events that trigger notifications
  enabled_events:
    - "tool:error"      # Tool execution fails
    - "session:end"     # Session completes
    - "session:start"   # Session begins (optional)
    - "prompt:submit"   # User submits prompt (optional)
  
  # Notify when Amplifier asks for user input
  notify_on_ask_user: true  # Default: true
```

### Available Events

| Event | When It Fires |
|-------|---------------|
| `tool:error` | Tool execution fails |
| `session:end` | Session completes |
| `session:start` | Session begins |
| `tool:post` | Tool finishes (any tool) |
| `prompt:submit` | User submits prompt |
| `provider:request` | Before LLM call |
| `provider:response` | After LLM response |

**Special**: `notify_on_ask_user: true` automatically detects when Amplifier calls the AskUserQuestion tool.

## Notification Script Contract

Your notification script should accept 3 arguments:

```bash
notify <message> <title> <priority>
```

**Example implementations:**

### ntfy.sh (Internet push notifications)
```bash
#!/bin/bash
curl -H "Title: $2" -H "Priority: $3" -d "$1" "https://ntfy.sh/$NTFY_TOPIC"
```

### macOS (local notifications)
```bash
#!/bin/bash
osascript -e "display notification \"$1\" with title \"$2\""
```

### Linux (notify-send)
```bash
#!/bin/bash
notify-send "$2" "$1" -u "$3"
```

### Windows (PowerShell)
```bash
#!/bin/bash
powershell -Command "New-BurntToastNotification -Text '$2', '$1'"
```

## Examples

### Minimal Config (Errors + Completions Only)

```yaml
modules:
  hooks:
    - module: hooks-notifications
```

Uses defaults:
- Notifies on tool errors
- Notifies when session ends
- Notifies when Amplifier needs user input

### Verbose Config (All Events)

```yaml
modules:
  hooks:
    - module: hooks-notifications
      config:
        notify_script: "/usr/local/bin/notify"
        enabled_events:
          - "tool:error"
          - "session:start"
          - "session:end"
          - "prompt:submit"
        notify_on_ask_user: true
```

### Custom Script Path

```yaml
modules:
  hooks:
    - module: hooks-notifications
      config:
        notify_script: "/Users/robotdad/bin/my-custom-notify"
```

**Note:** These examples assume the module is already pip-installed. Add `source: git+https://github.com/...` if you want auto-installation behavior.

## Testing

Test your notification setup:

```bash
# Test the notify script directly
notify "Test message" "Test Title" "high"

# Start Amplifier with the hook configured
amplifier

# Trigger a notification by causing an error or completing a session
```

## Remote Development with Tailscale

This hook is perfect for remote `amplifier-dev` sessions:

```bash
# On Linux box via Tailscale
ssh youruser@linux-dev
amplifier-dev ~/work/my-task

# Detach from tmux
Ctrl+b d

# Get notifications on your phone when:
# - Amplifier needs your input
# - Task completes
# - Errors occur

# Reattach from anywhere
ssh youruser@linux-dev
tmux attach -t my-task
```

See `REMOTE_AMPLIFIER_DEV.md` for full remote development guide.

## How It Works

1. Hook module registers event listeners with Amplifier kernel
2. When events fire (tool:error, session:end, etc.), handlers are called
3. Handler builds appropriate notification message
4. Calls your shell script asynchronously (non-blocking)
5. Your script sends push notification (ntfy.sh, macOS, Linux, etc.)

The hook runs at priority 90 (low), so it doesn't interfere with other hooks or affect session performance.

## Troubleshooting

### Notifications not appearing

```bash
# Test script directly
notify "test" "test" "high"

# Check if script is in PATH
which notify

# Check topic matches in ntfy app
echo $NTFY_TOPIC

# Verify hook is loaded
amplifier --debug
# Look for "Loading hook: hooks-notifications"
```

### Hook not loading

```bash
# Verify installation
pip show amplifier-module-hooks-notifications

# Check settings.yaml syntax
cat ~/.amplifier/settings.yaml

# Ensure source path is correct
ls -la /path/to/hooks-notifications
```

### Script not executable

```bash
chmod +x ~/bin/notify
```

## License

MIT
