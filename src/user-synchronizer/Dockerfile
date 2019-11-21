FROM python:3.5

RUN apt-get install --yes default-libmysqlclient-dev
RUN pip install pipenv

RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

COPY Pipfile Pipfile.lock ./
RUN pipenv install --system --deploy

COPY . .

CMD python .
