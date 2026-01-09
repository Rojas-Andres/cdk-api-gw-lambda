#!/bin/bash

# 1. Instalar y activar el SSM Agent
snap install amazon-ssm-agent --classic
snap start amazon-ssm-agent

# 2. Preparar el repositorio de ClickHouse
apt-get update -y
apt-get install -y apt-transport-https ca-certificates dirmngr gnupg curl
mkdir -p /usr/share/keyrings
curl -fsSL 'https://packages.clickhouse.com/repo-public-key.gpg' | gpg --dearmor -o /usr/share/keyrings/clickhouse-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/clickhouse-keyring.gpg] https://packages.clickhouse.com/deb stable main" | tee /etc/apt/sources.list.d/clickhouse.list

# 3. Instalar ClickHouse
apt-get update -y
DEBIAN_FRONTEND=noninteractive apt-get install -y clickhouse-server clickhouse-client

# 4. CREAR CONFIGURACIÓN DESDE CERO (Sobreescribir config.xml)
# Esto garantiza que escuche en todas las interfaces y define los directorios base
cat <<EOF | tee /etc/clickhouse-server/config.xml
<clickhouse>
    <logger>
        <level>trace</level>
        <log>/var/log/clickhouse-server/clickhouse-server.log</log>
        <errorlog>/var/log/clickhouse-server/clickhouse-server.err.log</errorlog>
        <size>1000M</size>
        <count>10</count>
    </logger>
    
    <http_port>8123</http_port>
    <tcp_port>9000</tcp_port>
    <listen_host>::</listen_host>
    <listen_host>0.0.0.0</listen_host>

    <path>/var/lib/clickhouse/</path>
    <tmp_path>/var/lib/clickhouse/tmp/</tmp_path>
    <user_directories>
        <users_xml>
            <path>users.xml</path>
        </users_xml>
    </user_directories>
    
    <default_profile>default</default_profile>
    <default_database>default</default_database>
    <timezone>UTC</timezone>

    <mlock_executable>true</mlock_executable>
</clickhouse>
EOF

# Asegurar permisos correctos en el nuevo archivo
chown clickhouse:clickhouse /etc/clickhouse-server/config.xml

# 5. Iniciar el servicio
systemctl restart clickhouse-server

# 6. Esperar a que el motor esté listo
for i in {1..15}; do
    clickhouse-client --query "SELECT 1" && break || sleep 5
done

# 7. Crear Base de Datos y Tabla de Logs
clickhouse-client -q "CREATE DATABASE IF NOT EXISTS sistema_logs;"

clickhouse-client -q "
CREATE TABLE IF NOT EXISTS sistema_logs.api_logs (
    requestTime DateTime64(3, 'UTC'), 
    requestId String, 
    httpMethod LowCardinality(String), 
    path String, 
    routeKey String, 
    status UInt16, 
    bytes UInt32, 
    responseLatency UInt32, 
    integrationLatency UInt32, 
    functionResponseStatus UInt16, 
    email String, 
    userId String, 
    orgId String, 
    idCompany String, 
    ip String, 
    host String, 
    userAgent String, 
    dataSource LowCardinality(String), 
    applicationVersion LowCardinality(String), 
    referer String
) ENGINE = MergeTree() 
PARTITION BY toYYYYMM(requestTime) 
ORDER BY (idCompany, requestTime, status);"