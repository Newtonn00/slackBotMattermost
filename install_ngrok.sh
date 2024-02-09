#!/bin/bash

REMOTE_SERVER="45.9.40.179"
REMOTE_USER="root"

#переход на удаленный сервер
ssh "$REMOTE_USER@$REMOTE_SERVER" << EOF

# Установка ngrok через snap
sudo snap install ngrok

# Создание файла ngrok.service
sudo tee /etc/systemd/system/ngrok.service <<EOF
[Unit]
Description=ngrok Tunneling Service
After=network.target

[Service]
ExecStart=/snap/bin/ngrok http --config=/etc/ngrok.yml 8082
Restart=always
User=root
Group=root

[Install]
WantedBy=multi-user.target
EOF

# Создание файла с настройками ngrok.yml
sudo tee /etc/ngrok.yml <<EOF
authtoken: token_ngrok
EOF

# Запуск сервиса ngrok
sudo systemctl daemon-reload
sudo systemctl start ngrok
sudo systemctl enable ngrok
sudo systemctl status ngrok
