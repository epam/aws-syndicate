from syndicate.core.conf.validator import ALL_REGIONS
from syndicate.core.resources.helper import check_region_available


def deploy_regions(resource_name, meta):
    from syndicate.core import CONFIG
    regions = []
    region = meta.get('region')
    if region is None:
        regions.append(CONFIG.region)
    elif isinstance(region, str):
        if region == 'all':
            for each in ALL_REGIONS:
                regions.append(each)
        else:
            if check_region_available(region, ALL_REGIONS, meta):
                regions.append(region)
    elif isinstance(region, list):
        for each in region:
            if check_region_available(each, ALL_REGIONS, meta):
                regions.append(each)
    else:
        raise AssertionError(
            'Invalid value region: {0}. Resource: {1}.'.format(region,
                                                               resource_name))
    return regions
