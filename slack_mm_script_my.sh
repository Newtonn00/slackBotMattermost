#!/bin/bash

# Подставьте ваши данные для подключения к удаленному серверу
REMOTE_SERVER="45.9.40.179"
REMOTE_USER="root"
DIRECTORY="mm"

# Шаг 1: Заходить на удаленный сервер по SSH
ssh "$REMOTE_USER@$REMOTE_SERVER" << EOF
  # Шаг 2: Переход в директорию
  cd /home/"$DIRECTORY"

  # Шаг 3: Остановка контейнеров web и slack_bot_service
  docker stop web slack_mattermost_slack_bot_service_1

  # Шаг 4: Запуск команды docker-compose up
  docker-compose up -d
EOF