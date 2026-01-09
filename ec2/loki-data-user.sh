#!/bin/bash
set -e

############################
# 1. Instalar SSM Agent
############################
sudo dnf install -y https://s3.amazonaws.com/ec2-downloads-windows/SSMAgent/latest/linux_arm64/amazon-ssm-agent.rpm
sudo systemctl enable amazon-ssm-agent
sudo systemctl start amazon-ssm-agent

############################
# 2. Repositorio Grafana Labs
############################
sudo tee /etc/yum.repos.d/grafana.repo <<'EOL'
[grafana]
name=grafana
baseurl=https://rpm.grafana.com
repo_gpgcheck=1
enabled=1
gpgcheck=1
gpgkey=https://rpm.grafana.com/gpg.key
sslverify=1
sslcacert=/etc/pki/tls/certs/ca-bundle.crt
EOL

############################
# 3. Instalar Loki y Promtail
############################
sudo dnf update -y
sudo dnf install -y loki promtail wget

############################
# 4. Crear directorios requeridos por TSDB
############################
sudo mkdir -p /var/lib/loki/{index,index_cache,compactor,wal,chunks}
sudo chown -R loki:loki /var/lib/loki

############################
# 5. Configuración de Loki (TSDB + S3)
############################
sudo tee /etc/loki/config.yml <<'EOL'
auth_enabled: true

server:
  http_listen_address: 0.0.0.0
  http_listen_port: 3100
  grpc_listen_port: 9095
  log_level: info

common:
  instance_addr: 127.0.0.1
  path_prefix: /var/lib/loki
  replication_factor: 1
  ring:
    kvstore:
      store: inmemory
  storage:
    s3:
      endpoint: s3.us-east-1.amazonaws.com
      bucketnames: test-loki-bucket-2025
      region: us-east-1

schema_config:
  configs:
    - from: 2024-01-01
      store: tsdb
      object_store: s3
      schema: v13
      index:
        prefix: index_
        period: 24h

storage_config:
  tsdb_shipper:
    active_index_directory: /var/lib/loki/index
    cache_location: /var/lib/loki/index_cache
  filesystem:
    directory: /var/lib/loki/chunks

ingester:
  max_chunk_age: 1m
  chunk_idle_period: 30s

compactor:
  working_directory: /var/lib/loki/compactor
  shared_store: s3
  retention_enabled: true
  retention_delete_delay: 2h
  retention_delete_worker_count: 150

limits_config:
  retention_period: 744h
  ingestion_rate_mb: 10
  ingestion_burst_size_mb: 20
EOL

############################
# 6. Validar configuración
############################
sudo loki -config.file=/etc/loki/config.yml -verify-config

############################
# 7. Habilitar y reiniciar Loki
############################
sudo systemctl daemon-reload
sudo systemctl enable loki
sudo systemctl restart loki

############################
# 8. Mensaje final
############################
echo "Loki instalado y configurado correctamente (TSDB + S3)."
echo "Endpoint: http://<EC2-IP>:3100"
echo "Auth habilitado (X-Scope-OrgID requerido)"