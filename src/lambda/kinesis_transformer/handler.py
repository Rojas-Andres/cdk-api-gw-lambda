import base64
import json
import time
import gzip


def handler(event, context):
    output = []

    for record in event["records"]:
        # 1. Decodificar el dato que viene de Kinesis (Base64)
        data_bytes = base64.b64decode(record["data"])

        # 2. Intentar descomprimir si está en gzip (byte 0x8b indica gzip)
        try:
            # Si los datos están comprimidos con gzip, descomprimirlos
            payload_decoded = gzip.decompress(data_bytes).decode("utf-8")
        except (gzip.BadGzipFile, OSError):
            # Si no están comprimidos, decodificar directamente
            payload_decoded = data_bytes.decode("utf-8")

        # 3. Preparar el formato que Loki exige
        # Timestamp en nanosegundos como string
        ts_nano = str(int(time.time() * 1000000000))

        loki_payload = {
            "streams": [
                {
                    "stream": {
                        "job": "kinesis-firehose",
                        "source": "data-stream",
                        "env": "production",
                    },
                    "values": [[ts_nano, payload_decoded]],
                }
            ]
        }

        # 4. Re-codificar para devolverlo a Firehose
        processed_data = base64.b64encode(
            json.dumps(loki_payload).encode("utf-8")
        ).decode("utf-8")

        output_record = {
            "recordId": record["recordId"],
            "result": "Ok",
            "data": processed_data,
        }
        output.append(output_record)

    print(f"Procesados {len(output)} registros.")
    return {"records": output}
