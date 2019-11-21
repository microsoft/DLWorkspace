FROM python:3.5

RUN pip install pipenv

RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

COPY user-synchronizer/Pipfile user-synchronizer/Pipfile.lock ./
RUN pipenv install --system --deploy

COPY user-synchronizer .

CMD python .
