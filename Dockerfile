FROM python:3.12-slim
RUN pip install poetry

WORKDIR /app
COPY pyproject.toml poetry.lock ./
RUN poetry install --no-root --without=dev

COPY main.py ./
CMD ["poetry", "run", "python", "main.py"]
