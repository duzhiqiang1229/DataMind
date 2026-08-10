# ============================================================
# DataX 执行容器镜像
# 构建: docker compose -f docker-compose.prod.yml build datax
# 使用: 后端通过 docker CLI 挂载 /jobs 卷执行
#   docker run --rm -v datax_jobs:/jobs datamind-datax:latest /jobs/xxx.json
# 说明: 构建时需要联网下载 DataX 发行包；若下载失败，
#       可手动把 datax.tar.gz 放到本目录，改用 COPY 方式。
# ============================================================
FROM python:3.9-slim

RUN rm -f /etc/apt/sources.list.d/debian.sources /etc/apt/sources.list \
    && . /etc/os-release \
    && printf 'deb http://mirrors.aliyun.com/debian/ %s main\ndeb http://mirrors.aliyun.com/debian/ %s-updates main\ndeb http://mirrors.aliyun.com/debian-security/ %s-security main\n' "$VERSION_CODENAME" "$VERSION_CODENAME" "$VERSION_CODENAME" > /etc/apt/sources.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends openjdk-11-jre-headless curl unzip \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fL -o /tmp/datax.tar.gz \
      https://datax-opensource.oss-cn-hangzhou.aliyuncs.com/202308/datax.tar.gz \
    && mkdir -p /opt/datax \
    && tar -xzf /tmp/datax.tar.gz -C /opt --strip-components=1 \
    && rm -f /tmp/datax.tar.gz

WORKDIR /opt/datax

ENTRYPOINT ["python", "/opt/datax/bin/datax.py"]
