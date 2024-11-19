FROM python:3.10.15

WORKDIR /SnowApp

COPY ./snow_tickets.py .
COPY ./requirements.txt .

RUN pip install -r requirements.txt
#RUN pip install pip-system-certs --use-feature=truststore
CMD ["python3", "snow_tickets.py"]

