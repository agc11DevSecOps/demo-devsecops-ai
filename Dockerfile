FROM python:3.12-slim@sha256:47ae396f09c1303b8653019811a8498470603d7ffefc29cb07c88f1f8cb3d19f AS runtime

WORKDIR /app
COPY vendor/python /tmp/wheels
COPY vendor/requirements.lock /tmp/requirements.lock
RUN python -m pip install --no-index --no-cache-dir --require-hashes \
        --find-links /tmp/wheels -r /tmp/requirements.lock \
    && rm -rf /tmp/wheels /tmp/requirements.lock
COPY vendor/opa /usr/local/bin/opa
RUN test "$(sha256sum /usr/local/bin/opa | cut -d ' ' -f1)" = "830ab11f61ffec760b5e19db0d7ad02bf037e13f5ef4d665faeaf17632177527" \
    && chmod 0755 /usr/local/bin/opa
COPY vendor/cosign /usr/local/bin/cosign
RUN test "$(sha256sum /usr/local/bin/cosign | cut -d ' ' -f1)" = "4629c757b7618056f8ddd7e2625ae9fdd94c0372a65049520bc7d9df9efc7f71" \
    && chmod 0755 /usr/local/bin/cosign
COPY policies /app/policies
COPY app /app/app
ENV PYTHONDONTWRITEBYTECODE=1
USER 10001:10001
ENTRYPOINT ["python", "-m", "app.cli"]

FROM runtime AS garak
USER root
COPY vendor/garak /tmp/garak-wheels
COPY vendor/garak-requirements.lock /tmp/garak-requirements.lock
RUN python -m pip install --no-index --no-cache-dir --no-deps --require-hashes \
        --find-links /tmp/garak-wheels -r /tmp/garak-requirements.lock \
    && rm -rf /tmp/garak-wheels /tmp/garak-requirements.lock
USER 10001:10001
