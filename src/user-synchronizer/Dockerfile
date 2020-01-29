FROM python:3.5

RUN pip install pipenv

RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

COPY Pipfile Pipfile.lock ./
RUN pipenv install --system --deploy

COPY . .

CMD python .
