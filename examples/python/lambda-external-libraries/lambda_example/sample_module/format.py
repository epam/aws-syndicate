def format_response(response):
    return {
        'url': response.url,
        "status_code": response.status_code,
        "response_time": f"{response.elapsed.total_seconds()}s."
    }
