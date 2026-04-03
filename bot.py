import csv
import io
import requests

CSV_URL = "http://publication.pravo.gov.ru/opendata/7710349494-legalacts-30/data-legalacts-30.csv"

resp = requests.get(CSV_URL, timeout=10)
content = resp.content.decode('utf-8-sig', errors='ignore')
reader = csv.DictReader(io.StringIO(content), delimiter=';')

print("Названия полей в CSV:")
print(reader.fieldnames)

print("\nПервая запись:")
for row in reader:
    for key, value in row.items():
        print(f"{key}: {value}")
    break
