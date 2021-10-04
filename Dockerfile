FROM python:latest

WORKDIR /app

COPY *.py .
COPY requirements.txt .

RUN pip install -r requirements.txt

VOLUME /app/config

CMD [ "main.py" ]

ENTRYPOINT ["python3"]