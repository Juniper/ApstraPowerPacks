FROM python:3.10.15

WORKDIR /SnowApp
COPY ./apstra_client.py .
COPY ./power_pack.py .
COPY ./snow_tickets.py .
COPY ./requirements.txt .

RUN pip install -r requirements.txt
CMD ["python3", "snow_tickets.py"]

