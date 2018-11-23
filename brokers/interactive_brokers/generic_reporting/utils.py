IB_ADDRESS_FIELD_MAPPING = {
    'Street': 'address1',
    'Street2': 'address2',
    'City': 'city',
    'State': 'state_code',
    'Zip': 'post_code',
    'Country': 'country'
}

IB_ACCOUNT_FEEDS_MAPPING = {
    'Type': 'type',
    'AccountID': 'account_id',
    'AccountTitle': 'account_title',
    'AccountType': 'account_type',
    'CustomerType': 'customer_type',
    'BaseCurrency': 'base_currency',
    'MasterAccountID': 'master_account_id',
    'Van': 'van',
    'Capabilities': 'capabilities',
    'TradingPermissions': 'trading_permissions',
    'Alias': 'alias',
    'PrimaryEmail': 'primary_email',
    'DateOpened': 'date_opened',
    'DateClosed': 'date_closed',
}

def map_keys_object(key_mapping, obj):
    new_obj = {}
    for key in list(key_mapping.keys()):
        new_obj[key_mapping[key]] = obj[key] if key in obj else None
    return new_obj
