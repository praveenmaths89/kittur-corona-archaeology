# Container for the Kittur pipeline (release/code). Build from the release/code folder:
#   docker build -t kittur-pipeline .
# Run against a copy of the deposited data, writing outputs to a scratch folder (never into the deposit):
#   docker run --rm -v /path/to/kittur_map:/data:ro -v /path/to/out:/out kittur-pipeline \
#       python run.py --out /out validation
# The image contains code only; the input data (CORONA crops, SoI scans, OSM, Sentinel-2, GLO-30) come from
# the Zenodo deposit, mounted read-only at /data.
FROM python:3.13-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 libglib2.0-0 fonts-dejavu-core && rm -rf /var/lib/apt/lists/*
WORKDIR /code
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# config.yaml uses project_root: ../.. ; inside the container the project is mounted at /data
RUN sed -i 's#^project_root: ../..#project_root: /data#' config.yaml
ENV MPLBACKEND=Agg
CMD ["python", "run.py"]
