import csv

def load_country_coordinates():
    country_coordinates = {}

    with open("country-coord.csv", "r", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        for row in reader:
            country_coordinates[row["Alpha-2 code"]] = {
                "country_name": row["Country"],
                "latitude": float(row["Latitude (average)"]),
                "longitude": float(row["Longitude (average)"])
            }

    return country_coordinates


def get_attack_coordinates(source_country, target_country):
    country_coordinates = load_country_coordinates()

    source = country_coordinates.get(source_country)
    target = country_coordinates.get(target_country)

    if source is None or target is None:
        return None

    return {
        "source": source,
        "target": target
    }