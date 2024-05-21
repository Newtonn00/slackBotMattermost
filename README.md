# slackBotMattermost

This repository contains the code for a Slack bot designed to work with Mattermost, providing integration and automation functionalities.

## Features

- Integration with Slack and Mattermost (transfer all events from Slack to Mattermost):
    Users
    Channels
    Messages (include private)
    Threads
    Attachments
    Emojis
    Pins
    Bookmarks
  
- Multiplayer mode
- Dockerized setup for easy deployment

## Technologies Used

- Python
    Flask
    dependency_injector
    dataclasses
- Mattermost API
- Slack API
- OAuth 2.0
- Docker
- Gunicorn

## Getting Started

### Prerequisites

- Docker and Docker Compose installed
- Python 3.8+ installed
- Slack-bolt 3.23+ installed
- Gunicorn 21.2 installed

### Installation

1. Clone the repository:
   git clone https://github.com/Newtonn00/slackBotMattermost.git
   cd slackBotMattermost
2. Configure the bot settings in config.json and settings.ini
3. Copy docker-compose.yml to your remote server
4. Edit slack_mm_script.sh and change information about server and directory
5. Run slack_mm_script.sh from your local terminal:
   ./slack_mm_script.sh 
6. Build and run the Docker containers:
     docker-compose up --build
   
### Running the Bot Locally   

1. Clone the repository:
   git clone https://github.com/Newtonn00/slackBotMattermost.git
   cd slackBotMattermost
2. Configure the bot settings in config.json and settings.ini
3. Run docker-compose.yml:
     docker-compose pull
     docker-compose up -d

## Contributing

Contributions are welcome! Please fork the repository and create a pull request with your changes.
