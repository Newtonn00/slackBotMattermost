FROM python:3.9.18-slim
RUN mkdir /var/app
RUN mkdir /var/app/slackbot_mattermost
WORKDIR /var/app/slackbot_mattermost
ARG WORKDIR=/var/app/slackbot_mattermost
ENV WORKDIR="${WORKDIR}"
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
#RUN pip install gunicorn
EXPOSE 3005
ENV PYTHONPATH "/var/app/slackbot_mattermost"
CMD ["gunicorn", "--bind", "0.0.0.0:3006","--threads","3","--timeout","0","--worker-tmp-dir","/dev/shm","src.controller.main:app"]
#CMD ["python3","/var/app/slackbot_mattermost/src/controller/main.py"]
