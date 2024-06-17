def get_bootstraped_percent(value, total):
    """
    Get percent and round to be 0, 25, 50 or 100

    Useful to set progress bar width using CSS classes (e.g. w-25)
    """
    try:
        percent = value / total
    except (TypeError, ZeroDivisionError):
        return 0

    bootstraped = round(percent * 4) * 100 // 4

    # handle min and max boundaries
    bootstraped = max(0, bootstraped)
    bootstraped = min(100, bootstraped)

    return bootstraped

def get_bootstraped_percent_exact(value, total):
    try:
        percent = 100 * float(value)/float(total)
    except (TypeError, ZeroDivisionError):
        return 0
    return percent