FROM python:3.10-slim
RUN pip install sneakpeek_py==0.1.4
WORKDIR /app
COPY main.py /app
COPY demo_scraper.py /app
ENTRYPOINT [ "python", "/app/main.py" ]
