para click house se usa ubuntu

validar instalacion 

sudo systemctl status clickhouse-server

conectarme a clickhouse

clickhouse-client


sudo cat /etc/clickhouse-server/config.xml

## Mostrar bases de datos

SHOW DATABASES;
SHOW TABLES FROM sistema_logs;

## Activar para que cualquiera se pueda conectar

sudo sed -i '/<clickhouse>/a \    <listen_host>::<\/listen_host>' /etc/clickhouse-server/config.xml
sudo systemctl restart clickhouse-server