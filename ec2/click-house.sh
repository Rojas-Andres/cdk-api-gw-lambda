#!/bin/bash

# 1. Instalar y activar el SSM Agent (Nativo en Ubuntu via Snap)
# El rol de IAM 'AmazonSSMManagedInstanceCore' debe estar asignado a la instancia
snap install amazon-ssm-agent --classic
snap start amazon-ssm-agent

# 2. Actualizar sistema e instalar dependencias iniciales
apt-get update -y
apt-get install -y apt-transport-https ca-certificates dirmngr gnupg curl

# 3. Configurar el repositorio oficial de ClickHouse
GNUPGHOME=$(mktemp -d)
GNUPGHOME="$GNUPGHOME" gpg --no-default-keyring --keyring /usr/share/keyrings/clickhouse-keyring.gpg --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys 8919F6BD2B48D754
chmod 644 /usr/share/keyrings/clickhouse-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/clickhouse-keyring.gpg] https://packages.clickhouse.com/deb stable main" | tee /etc/apt/sources.list.d/clickhouse.list

# 4. Instalar ClickHouse Server y Client
apt-get update -y
DEBIAN_FRONTEND=noninteractive apt-get install -y clickhouse-server clickhouse-client

# 5. Configurar ClickHouse para permitir conexiones externas (Listen en todas las interfaces)
sed -i 's//<listen_host>::<\/listen_host>/g' /etc/clickhouse-server/config.xml

# 6. Iniciar el servicio
systemctl enable clickhouse-server
systemctl start clickhouse-server

# 7. Esperar a que el motor esté listo y crear la estructura de datos
# Reintenta hasta que el cliente pueda conectar
for i in {1..10}; do
    clickhouse-client --query "SELECT 1" && break || sleep 5
done

# Crear Base de Datos
clickhouse-client -q "CREATE DATABASE IF NOT EXISTS sistema_logs;"

# Crear Tabla de Logs
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