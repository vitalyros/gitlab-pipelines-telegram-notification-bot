# Simple telegram bot that send notifications whenever a pipeline fails 

## Features

- Deployed as a systemd service
- Connects to gitlab using tokens
- Polls pipeline information via gitlab api
- Configurable selection of which gitab pipelines to poll
- Uses a configurable telegram bot token to connect to telegram
- Spams to all chats whenever a piplefine fails or is restored
