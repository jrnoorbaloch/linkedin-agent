FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY linkedin_agent ./linkedin_agent
RUN pip install --no-cache-dir .
ENV LA_HOST=0.0.0.0 LA_PORT=8787 LA_DATA_DIR=/data
VOLUME ["/data"]
EXPOSE 8787
CMD ["linkedin-agent", "serve"]
