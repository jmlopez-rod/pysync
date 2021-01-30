FROM python:3-alpine

RUN apk add --no-cache bash

WORKDIR /opt

RUN pip install pycodestyle pylint

COPY pysync.py ./python/
COPY .pylintrc ./

# pylint source code
RUN pylint python --rcfile=.pylintrc

# pylint tests
COPY packages/python/tests ./python/tests
COPY packages/.tests_pylintrc ./
RUN pylint python/tests --rcfile=.tests_pylintrc

# check overall style
# --show-pep8 --show-source
RUN pycodestyle --format=pylint python
