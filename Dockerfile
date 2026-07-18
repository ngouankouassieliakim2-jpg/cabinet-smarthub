FROM python:3.14-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Dépendances système :
# - libpango/libharfbuzz : WeasyPrint (confirmé sur la doc officielle de la 69.0)
# - libcairo2(-dev) + pkg-config : pycairo, rlPyCairo, svglib
# - libxml2-dev/libxslt1-dev : lxml
# - libffi-dev/libssl-dev : cryptography, pyHanko
# - build-essential/python3-dev : filet de sécurité si un paquet n'a pas de
#   wheel prête pour Python 3.14 sur cette architecture précise
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libharfbuzz-subset0 \
    libcairo2 \
    libcairo2-dev \
    pkg-config \
    build-essential \
    python3-dev \
    libffi-dev \
    libssl-dev \
    libxml2-dev \
    libxslt1-dev \
    shared-mime-info \
    fonts-liberation \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# Les dépendances Python d'abord (Docker met ce calque en cache -- il ne se
# réinstalle pas à chaque fois que tu modifies juste du code)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir gunicorn

COPY . .

RUN python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]