
def process_attack_data(data):
    """
    Processes the attack data and returns a list of dictionaries containing
    source country, target country, and percentage of attacks.
    """
    attacks = data['result']['top_0']
    processed_data = []
    
    for attack in attacks:

        processed_data.append({
            'source': attack['originCountryAlpha2'],
            'source_country': attack['originCountryName'],
            'target': attack['targetCountryAlpha2'],
            'target_country': attack['targetCountryName'],
            'percentage': float(attack['value']),
            'rank': attack['rank']
        })
    
    return processed_data