def includeme(config):
    config.add_route('company', '/companies/{company_guid}')
    config.add_route('company_list', '/companies/')
