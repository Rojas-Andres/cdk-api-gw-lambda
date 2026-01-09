#!/bin/bash
set -e

# 1. Instalar utilidades básicas
dnf install -y curl coreutils

# 2. Agregar el repositorio oficial de ClickHouse (RPM)
# Usamos sudo tee para asegurar que el archivo se escriba correctamente
curl -s https://packages.clickhouse.com/rpm/clickhouse.repo | tee /etc/yum.repos.d/clickhouse.repo

# 3. Limpiar caché de DNF y refrescar metadatos
# Esto soluciona el error "No match for argument"
dnf clean all
dnf makecache

# 4. Instalar ClickHouse Server y Client
dnf install -y clickhouse-server clickhouse-client

# 5. Configurar para permitir conexiones externas (Listen host)
# Necesario para que tu Lambda y Grafana se conecten vía IP
sed -i 's//<listen_host>::<\/listen_host>/g' /etc/clickhouse-server/config.xml

# 6. Habilitar e Iniciar el servicio
systemctl enable clickhouse-server
systemctl start clickhouse-server

# 7. Esperar a que el servicio esté totalmente arriba
sleep 15

# 8. Crear la base de datos y la tabla de logs inicial
clickhouse-client -q "CREATE DATABASE IF NOT EXISTS sistema_logs;"
clickhouse-client -q "
CREATE TABLE IF NOT EXISTS sistema_logs.logs_lambda (
    fecha_hora DateTime DEFAULT now(),
    nivel String,
    mensaje String,
    request_id String,
    lambda_nombre String
) 
ENGINE = MergeTree() 
ORDER BY (fecha_hora, nivel);"

echo "ClickHouse se ha instalado y configurado correctamente."