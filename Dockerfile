FROM python:3.11-slim
LABEL org.opencontainers.image.authors="adream74@gmail.com"

WORKDIR /code
COPY ./requirements.txt /code/requirements.txt
COPY app/main.py /code/main.py
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY ./app /code/app

CMD ["python", "-m", "app.main"]