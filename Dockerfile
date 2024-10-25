FROM python:3.12-alpine
LABEL org.opencontainers.image.authors="adream74@gmail.com"

WORKDIR /code
COPY ./requirements.txt /code/requirements.txt
COPY app/main.py /code/main.py
# curl is required to perform health checks
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt && apk upgrade --no-cache && apk --no-cache add curl

COPY ./app /code/app

CMD ["python", "-m", "app.main"]