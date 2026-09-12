from country_coordinates import load_country_coordinates

country_coordinates = load_country_coordinates()


def process_attack_data(data):
    """
    Processes the attack data and returns a list of dictionaries containing
    source country, target country, percentage of attacks, and coordinates.
    """

    attacks = data['result']['top_0']
    processed_data = []

    for attack in attacks:

        source_code = attack['originCountryAlpha2']
        target_code = attack['targetCountryAlpha2']

        source_coordinates = country_coordinates.get(source_code)
        target_coordinates = country_coordinates.get(target_code)

        processed_data.append({
            'source': source_code,
            'source_country': attack['originCountryName'],
            'source_latitude': source_coordinates['latitude'] if source_coordinates else None,
            'source_longitude': source_coordinates['longitude'] if source_coordinates else None,

            'target': target_code,
            'target_country': attack['targetCountryName'],
            'target_latitude': target_coordinates['latitude'] if target_coordinates else None,
            'target_longitude': target_coordinates['longitude'] if target_coordinates else None,

            'percentage': float(attack['value']),
            'rank': attack['rank']
        })

    return processed_data

