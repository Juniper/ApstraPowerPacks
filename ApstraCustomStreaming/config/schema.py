CONFIG_SCHEMA = {
    'redis': {
        'required': {
            'host': str,
            'port': int,
        },
        'optional': {
            'channel': ('new_event_channel', str),
            'database': (0, int),
            'password': (None, str),
            'ssl': (False, bool),
            'max_entries': (1500, int)
        }
    },
    'apstra_api': {
        'required': {
            'base_url': str,
            'username': str,
            'password': str,
            'blueprint_id': str,
        },
        'optional': {
            'verify_ssl': (False, bool),
            'poll_interval': (60, int),
            'timeout': (30, int),
            'endpoints': ({
            }, dict)
        }
    },
    'outputs': {
        'syslog': {
            'required': {
                'server': str,
                'port': int,
                'protocol': str  # udp or tcp
            },
            'optional': {
                'enabled': (False, bool),
                'facility': ('local0', str),
                'severity': ('info', str)
            }
        },
        'webhook': {
            'required': {
                'webhook_url': str
            },
            'optional': {
                'enabled': (False, bool),
                'timeout': (30, int),
                'retry_count': (3, int),
                'headers': ({
                    'Content-Type': 'application/json'
                }, dict)
            }
        }
    }
}
