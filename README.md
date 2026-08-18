# WhatsApp MCP Server

This is a Model Context Protocol (MCP) server for WhatsApp.

With this you can search and read your personal Whatsapp messages (including images, videos, documents, and audio messages), search your contacts and send messages to either individuals or groups. You can also send media files including images, videos, documents, and audio messages.

It connects to your **personal WhatsApp account** directly via the Whatsapp web multidevice API (using the [whatsmeow](https://github.com/tulir/whatsmeow) library). All your messages are stored locally in a SQLite database and only sent to an LLM (such as Claude) when the agent accesses them through tools (which you control).

Here's an example of what you can do when it's connected to Claude.

![WhatsApp MCP](./example-use.png)

> To get updates on this and other projects I work on [enter your email here](https://docs.google.com/forms/d/1rTF9wMBTN0vPfzWuQa2BjfGKdKIpTbyeKxhPMcEzgyI/preview)

> *Caution:* as with many MCP servers, the WhatsApp MCP is subject to [the lethal trifecta](https://simonwillison.net/2025/Jun/16/the-lethal-trifecta/). This means that project injection could lead to private data exfiltration.

## Installation

### Prerequisites

- Go
- Python 3.6+
- Anthropic Claude Desktop app (or Cursor)
- UV (Python package manager), install with `curl -LsSf https://astral.sh/uv/install.sh | sh`
- FFmpeg (_optional_) - Only needed for audio messages. If you want to send audio files as playable WhatsApp voice messages, they must be in `.ogg` Opus format. With FFmpeg installed, the MCP server will automatically convert non-Opus audio files. Without FFmpeg, you can still send raw audio files using the `send_file` tool.

### Steps

1. **Clone this repository**

   ```bash
   git clone https://github.com/lharries/whatsapp-mcp.git
   cd whatsapp-mcp
   ```

2. **Run the WhatsApp bridge**

   Navigate to the whatsapp-bridge directory and run the Go application:

   ```bash
   cd whatsapp-bridge
   go run main.go
   ```

   The first time you run it, you will be prompted to scan a QR code. Scan the QR code with your WhatsApp mobile app to authenticate.

   After approximately 20 days, you will might need to re-authenticate.

3. **Connect to the MCP server**

   Copy the below json with the appropriate {{PATH}} values:

   ```json
   {
     "mcpServers": {
       "whatsapp": {
         "command": "{{PATH_TO_UV}}", // Run `which uv` and place the output here
         "args": [
           "--directory",
           "{{PATH_TO_SRC}}/whatsapp-mcp/whatsapp-mcp-server", // cd into the repo, run `pwd` and enter the output here + "/whatsapp-mcp-server"
           "run",
           "main.py"
         ]
       }
     }
   }
   ```

   For **Claude**, save this as `claude_desktop_config.json` in your Claude Desktop configuration directory at:

   ```
   ~/Library/Application Support/Claude/claude_desktop_config.json
   ```

   For **Cursor**, save this as `mcp.json` in your Cursor configuration directory at:

   ```
   ~/.cursor/mcp.json
   ```

4. **Restart Claude Desktop / Cursor**

   Open Claude Desktop and you should now see WhatsApp as an available integration.

   Or restart Cursor.

### Windows Compatibility

If you're running this project on Windows, be aware that `go-sqlite3` requires **CGO to be enabled** in order to compile and work properly. By default, **CGO is disabled on Windows**, so you need to explicitly enable it and have a C compiler installed.

#### Steps to get it working:

1. **Install a C compiler**
   We recommend using [MSYS2](https://www.msys2.org/) to install a C compiler for Windows. After installing MSYS2, make sure to add the `ucrt64\bin` folder to your `PATH`.
   → A step-by-step guide is available [here](https://code.visualstudio.com/docs/cpp/config-mingw).

   Alternatively, `winget install --id BrechtSanders.WinLibs.POSIX.UCRT` installs a standalone MinGW-w64 GCC toolchain without requiring the full MSYS2 environment.

2. **Enable CGO and run the app**

   ```bash
   cd whatsapp-bridge
   go env -w CGO_ENABLED=1
   go run main.go
   ```

Without this setup, you'll likely run into errors like:

> `Binary was compiled with 'CGO_ENABLED=0', go-sqlite3 requires cgo to work.`

#### "Client outdated (405) connect failure"

If the bridge connects to the websocket but immediately gets disconnected with `Client outdated (405) connect failure`, the pinned `whatsmeow` version in `go.mod` is too old for WhatsApp's current minimum client version. Update it and rebuild:

```bash
cd whatsapp-bridge
go get -u go.mau.fi/whatsmeow@latest
go mod tidy
```

Newer `whatsmeow` releases have changed several method signatures to take a `context.Context` as the first argument (e.g. `client.Download`, `sqlstore.New`, `container.GetFirstDevice`, `client.GetGroupInfo`, `client.Store.Contacts.GetContact`). If `go build` reports "not enough arguments" for these, add `context.Background()` as the first argument at each call site.

#### "An Application Control policy blocked this file" / binary won't run

On some Windows machines (Smart App Control, or a corporate EDR/Application Control policy), a freshly compiled, unsigned binary run via `go run` is blocked from executing, with an error like *"Uma política de Controle de Aplicativo bloqueou este arquivo"* (or the English equivalent). This isn't something the project can work around — it's a local security policy blocking unsigned executables. Either allow the binary/folder through your security policy, or ask your Windows/IT admin to do so.

#### Running the bridge as a background service

`go run main.go` needs a terminal open the whole time. For a setup that survives reboots without a visible console window:

1. Build a standalone binary: `cd whatsapp-bridge && go build -o whatsapp-bridge.exe main.go`
2. Register a Windows Scheduled Task that runs at logon:

   ```powershell
   $action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument '-WindowStyle Hidden -Command "Start-Process -FilePath ''C:\path\to\whatsapp-bridge\whatsapp-bridge.exe'' -WorkingDirectory ''C:\path\to\whatsapp-bridge'' -WindowStyle Hidden"'
   $trigger = New-ScheduledTaskTrigger -AtLogOn
   Register-ScheduledTask -TaskName "WhatsApp MCP Bridge" -Action $action -Trigger $trigger -Description "Starts the WhatsApp MCP bridge at logon"
   ```

   The working directory matters: the bridge reads/writes `store/` relative to where it runs.

## Architecture Overview

This application consists of two main components:

1. **Go WhatsApp Bridge** (`whatsapp-bridge/`): A Go application that connects to WhatsApp's web API, handles authentication via QR code, and stores message history in SQLite. It serves as the bridge between WhatsApp and the MCP server.

2. **Python MCP Server** (`whatsapp-mcp-server/`): A Python server implementing the Model Context Protocol (MCP), which provides standardized tools for Claude to interact with WhatsApp data and send/receive messages.

### Data Storage

- All message history is stored in a SQLite database within the `whatsapp-bridge/store/` directory
- The database maintains tables for chats and messages
- Messages are indexed for efficient searching and retrieval

## Usage

Once connected, you can interact with your WhatsApp contacts through Claude, leveraging Claude's AI capabilities in your WhatsApp conversations.

### MCP Tools

Claude can access the following tools to interact with WhatsApp:

- **search_contacts**: Search for contacts by name or phone number
- **list_messages**: Retrieve messages with optional filters and context
- **list_chats**: List available chats with metadata
- **get_chat**: Get information about a specific chat
- **get_direct_chat_by_contact**: Find a direct chat with a specific contact
- **get_contact_chats**: List all chats involving a specific contact
- **get_last_interaction**: Get the most recent message with a contact
- **get_message_context**: Retrieve context around a specific message
- **send_message**: Send a WhatsApp message to a specified phone number or group JID
- **send_file**: Send a file (image, video, raw audio, document) to a specified recipient
- **send_audio_message**: Send an audio file as a WhatsApp voice message (requires the file to be an .ogg opus file or ffmpeg must be installed)
- **download_media**: Download media from a WhatsApp message and get the local file path

### Chats Routed Through a LID (Linked ID)

WhatsApp is progressively moving chats from phone-number-based JIDs (`<number>@s.whatsapp.net`) to a privacy-preserving **LID** (`<lid>@lid`). A contact's incoming messages can end up filed under either identifier depending on when your account first synced them, which used to make `list_messages`, `get_direct_chat_by_contact`, `get_contact_chats`, and `get_last_interaction` silently return nothing when queried with the "wrong" one.

These tools now resolve both directions automatically using whatsmeow's own `whatsmeow_lid_map` table (stored in `whatsapp-bridge/store/whatsapp.db`), so a phone number and its LID are treated as equivalent no matter which one you pass in.

Separately, the Go bridge previously cached a chat's display name the first time it saw a message from it — if that first message arrived before the contact's name had synced, the chat was stuck showing the raw number/LID forever. The bridge now retries the name lookup on subsequent messages if the stored name is still just the raw identifier.

### Read / Unread Status

`list_chats`, `get_chat`, `get_contact_chats`, and `get_direct_chat_by_contact` include an `is_read` field (`true` / `false` / `null`). This mirrors WhatsApp's own read-state sync (`MarkChatAsRead` from whatsmeow), the same signal that keeps read status consistent across your phone and other linked devices — it isn't a heuristic. It updates live as: a new message arrives (marks the chat unread), you mark a chat as read/unread on another linked device, or you send a message through this MCP (marks the chat read). `null` means no read-state signal has been observed yet for that chat since the bridge started tracking it.

### Media Handling Features

The MCP server supports both sending and receiving various media types:

#### Media Sending

You can send various media types to your WhatsApp contacts:

- **Images, Videos, Documents**: Use the `send_file` tool to share any supported media type.
- **Voice Messages**: Use the `send_audio_message` tool to send audio files as playable WhatsApp voice messages.
  - For optimal compatibility, audio files should be in `.ogg` Opus format.
  - With FFmpeg installed, the system will automatically convert other audio formats (MP3, WAV, etc.) to the required format.
  - Without FFmpeg, you can still send raw audio files using the `send_file` tool, but they won't appear as playable voice messages.

#### Media Downloading

By default, just the metadata of the media is stored in the local database. The message will indicate that media was sent. To access this media you need to use the download_media tool which takes the `message_id` and `chat_jid` (which are shown when printing messages containing the meda), this downloads the media and then returns the file path which can be then opened or passed to another tool.

## Technical Details

1. Claude sends requests to the Python MCP server
2. The MCP server queries the Go bridge for WhatsApp data or directly to the SQLite database
3. The Go accesses the WhatsApp API and keeps the SQLite database up to date
4. Data flows back through the chain to Claude
5. When sending messages, the request flows from Claude through the MCP server to the Go bridge and to WhatsApp

## Troubleshooting

- If you encounter permission issues when running uv, you may need to add it to your PATH or use the full path to the executable.
- Make sure both the Go application and the Python server are running for the integration to work properly.

### Authentication Issues

- **QR Code Not Displaying**: If the QR code doesn't appear, try restarting the authentication script. If issues persist, check if your terminal supports displaying QR codes.
- **WhatsApp Already Logged In**: If your session is already active, the Go bridge will automatically reconnect without showing a QR code.
- **Device Limit Reached**: WhatsApp limits the number of linked devices. If you reach this limit, you'll need to remove an existing device from WhatsApp on your phone (Settings > Linked Devices).
- **No Messages Loading**: After initial authentication, it can take several minutes for your message history to load, especially if you have many chats.
- **WhatsApp Out of Sync**: If your WhatsApp messages get out of sync with the bridge, delete both database files (`whatsapp-bridge/store/messages.db` and `whatsapp-bridge/store/whatsapp.db`) and restart the bridge to re-authenticate.
- **Claude Code (CLI/agent sessions)**: register the server with `claude mcp add --scope user whatsapp -- <path-to-uv> --directory <path-to-whatsapp-mcp-server> run main.py` instead of editing a JSON file by hand. `--scope user` makes it available to every Claude Code session on the machine.
- **Newer unified Claude desktop apps (bundling "Cowork"/Claude Code)**: these may manage MCP connections through an in-app Connectors UI (Settings → Connectors) rather than reading `claude_desktop_config.json` directly. If adding the server via the config file doesn't make it show up in chat mode, check that settings screen for a "custom connector" / local command option instead.

For additional Claude Desktop integration troubleshooting, see the [MCP documentation](https://modelcontextprotocol.io/quickstart/server#claude-for-desktop-integration-issues). The documentation includes helpful tips for checking logs and resolving common issues.
