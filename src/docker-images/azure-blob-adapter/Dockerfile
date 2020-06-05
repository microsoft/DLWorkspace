FROM python:3.6

RUN pip install pipenv uwsgi

RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

COPY Pipfile Pipfile.lock ./
RUN pipenv install --system --deploy

COPY . .

ENV UWSGI_WSGI_FILE wsgi.py
ENV UWSGI_MASTER 1
ENV UWSGI_ENABLE_THREADS 1
ENV UWSGI_THUNDER_LOCK 1
ENV UWSGI_UID nobody
ENV UWSGI_GID nogroup

CMD uwsgi
