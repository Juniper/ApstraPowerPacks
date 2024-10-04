FROM python:3.10.15

WORKDIR /SnowApp

COPY ./snow_tickets.py .
COPY ./requirements.txt .

RUN pip install -r requirements.txt

CMD ["python", "snow_tickets.py"]

