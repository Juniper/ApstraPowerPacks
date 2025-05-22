FROM python:3.10.15

WORKDIR /SnowApp
COPY apstra/apstra_client.py .
COPY power_pack/power_pack.py .
COPY SnowTickets/snow_tickets.py .
COPY SnowTickets/app_server.py .
COPY SnowTickets/requirements.txt .

RUN pip install -r requirements.txt
EXPOSE 5000
CMD ["python3", "app_server.py"]

