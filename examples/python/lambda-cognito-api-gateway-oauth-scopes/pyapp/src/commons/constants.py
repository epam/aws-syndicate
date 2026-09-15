CORS_HEADERS = {
    'Access-Control-Allow-Headers': (
        'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'
    ),
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': '*',
    'Accept-Version': '*',
    'Content-Type': 'application/json'
}

SAMPLE_OBJECTS = {
    'items': [
        {
            'id': '00000000-0000-0000-0000-000000000001',
            'name': 'sample-object-1',
            'attributes': {'category': 'demo', 'weight': 10},
            'createdAt': '2024-01-01T00:00:00Z',
        },
        {
            'id': '00000000-0000-0000-0000-000000000002',
            'name': 'sample-object-2',
            'attributes': {'category': 'demo', 'weight': 20},
            'createdAt': '2024-01-02T00:00:00Z',
        },
    ],
    'count': 2
}
