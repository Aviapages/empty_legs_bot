FROM python:3.10.0
ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1

RUN apt update\
    && apt install tzdata cron -y

# TIMEZONE
ENV TZ="Europe/Chisinau"

WORKDIR /var/app

# INSTALL PYTHON PACKAGES
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY /app .

# CRONTAB AS ENTRYPOINT
COPY cronjob /etc/cron.d/cronjob
RUN chmod 0644 /etc/cron.d/cronjob \
    && crontab /etc/cron.d/cronjob \
    && touch /var/log/cron.log

CMD cron && tail -f /var/log/cron.log