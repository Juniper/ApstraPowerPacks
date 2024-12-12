from config.config_manager import load_config, get_redis_config, get_apstra_api_config, get_output_config

def main():
    try:
        # Load and validate all configs at once
        config = load_config()
        
        # Get Redis configuration
        redis_config = get_redis_config(config)
        print("Redis Config:", redis_config)
        
        # Get API configuration
        api_config = get_apstra_api_config(config)
        print("API Config:", api_config)
        
        # Get Syslog configuration
        syslog_config = get_output_config('syslog', config)
        print("Syslog Config:", syslog_config)
        
    except ValueError as e:
        print("Configuration error:", e)
        return
    
def main():
    # Load and validate all configs at once
    config = load_config()
    
    # Get Redis configuration
    redis_config = get_redis_config(config)
    print("Redis Config:", redis_config)
    
    # Get API configuration
    api_config = get_apstra_api_config(config)
    print("API Config:", api_config)
    
    # Get Syslog configuration
    syslog_config = get_output_config('syslog', config)
    print("Syslog Config:", syslog_config)

if __name__ == "__main__":
    main()