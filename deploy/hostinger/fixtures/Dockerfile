FROM python:3.13-slim
ARG RELEASE=previous
ARG MUTATE_DATA=0
ENV RELEASE=$RELEASE MUTATE_DATA=$MUTATE_DATA
COPY dashboard.py /fixture/dashboard.py
ENTRYPOINT ["python", "/fixture/dashboard.py"]
