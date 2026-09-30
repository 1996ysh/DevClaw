# Dockerfile —— DevMate 应用镜像（web / worker / 飞书接收端共用，启动命令不同）
# 国内服务器用 pip + 国内镜像，避开 uv 在国内源上的卡死问题
FROM python:3.14-slim

WORKDIR /app

ENV PIP_DEFAULT_TIMEOUT=120

# 先拷依赖清单装依赖（利用 Docker 层缓存：依赖不变就不重装）
COPY requirements.txt ./

# 索引写在 install 命令上，构建日志里能直接看到实际用的源；
# --no-require-hashes：requirements.txt 含 uv export 的 hash，国内镜像常缺部分文件导致误报 none
RUN python -c "import sys; assert sys.version_info[:2] == (3, 14), sys.version; print(sys.version)" \
 && pip install --no-cache-dir --no-require-hashes \
      -i https://mirrors.aliyun.com/pypi/simple \
      --extra-index-url https://pypi.org/simple \
      --trusted-host mirrors.aliyun.com \
      --trusted-host pypi.org \
      --trusted-host files.pythonhosted.org \
      -r requirements.txt

# 再拷代码
COPY . .

# 默认启动 web（worker/飞书容器用 command 覆盖）。
# 注意：Linux 容器里不需要 Windows 那套事件循环处理；
# start_web.sh 里设了 Prometheus 多进程目录
CMD ["bash", "scripts/start_web.sh"]
