def update_stat(event: dict , stats: dict) -> dict:
    data = event['timestamp']
    if stats['first_timestamp'] is None or data < stats['first_timestamp']:
        stats['first_timestamp'] = data
    if stats['last_timestamp'] is None or data > stats['last_timestamp']:
        stats['last_timestamp'] = data

    stats['total'] += 1
    stats['by_level'][f'{event['level']}'] += 1
    source = event['source']
    if source not in stats['by_source']:
        stats['by_source'][f'{source}'] = {
            'total': 0,
            'errors': 0
        }
    stats['by_source'][f'{source}']['total'] += 1

    if event['level'] == 'ERROR' or event['level'] == 'CRITICAL':
        stats['by_source'][f'{source}']['errors'] += 1

    return stats
