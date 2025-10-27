FROM python:3.10.15

WORKDIR /SnowApp
COPY apstra/apstra_client.py .
COPY power_pack/power_pack.py .
COPY SnowTickets/snow_tickets.py .
COPY SnowTickets/requirements.txt .

RUN pip install -r requirements.txt
CMD ["python3", "snow_tickets.py"]

