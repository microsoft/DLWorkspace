FROM python:3.5

RUN pip install pipenv uwsgi

RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

COPY Pipfile Pipfile.lock ./
RUN pipenv install --system --deploy

COPY . .

ENV UWSGI_MODULE azure_blob_adapter.wsgi:application
ENV UWSGI_MASTER 1
ENV UWSGI_ENABLE_THREADS 1
ENV UWSGI_THUNDER_LOCK 1
ENV UWSGI_UID nobody
ENV UWSGI_GID nogroup

CMD uwsgi
