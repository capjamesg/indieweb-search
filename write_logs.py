# Imports the Cloud Logging client library
import datetime

from influxdb import InfluxDBClient

client = InfluxDBClient(host="localhost", port=8086)


def write_log(text: str, domain: str = "ADMIN") -> None:
    split_domain = domain.split("/")[0]

    data = [
        {
            "measurement": "crawl",
            "time": datetime.datetime.utcnow().isoformat(),
            "fields": {"text": f"[*{split_domain}*]   " + text},
        }
    ]
    
    print(text)

    try:
        client.write_points(data, database="search_logs")
    except:
        pass
