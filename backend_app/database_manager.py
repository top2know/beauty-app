import pandas as pd
import numpy as np
from hashlib import sha256

PATH = 'storage/databases'
tables = {
    'codes': {
        'pk': 'Код',
        'force_str': False,
        'sep': '|',
        'path': 'codes.csv',
        'allow_append': False
    },
    'clinics': {
        'pk': 'Клиника',
        'force_str': False,
        'sep': ';',
        'path': 'clinics.csv',
        'allow_append': False
    },
    'medicines': {
        'pk': 'Продукт',
        'force_str': True,
        'sep': ';',
        'path': 'medicines.csv',
        'allow_append': False
    },
    'compliments': {
        'pk': 'compliment_id',
        'force_str': False,
        'sep': ';',
        'path': 'compliments.csv',
        'allow_append': True
    },
    'compliments_history': {
        'pk': None,
        'force_str': False,
        'sep': ';',
        'path': 'compliments_history.csv',
        'allow_append': True
    },
    'users': {
        'pk': 'uid',
        'force_str': True,
        'sep': ';',
        'path': 'users.csv',
        'allow_append': True
    },
    'requests': {
        'pk': None,
        'force_str': False,
        'sep': '|',
        'path': 'requests.csv',
        'allow_append': True
    },
    'tg_requests': {
        'pk': None,
        'force_str': False,
        'sep': '|',
        'path': 'tg_requests.csv',
        'allow_append': True
    },
    'regular_compliments': {
        'pk': 'uid',
        'force_str': True,
        'sep': ';',
        'path': 'regular_compliments.csv',
        'allow_append': True
    }
}


class DatabaseManager:

    def __init__(self):
        self.tables = tables

    def _get_table(self, table_name):
        if table_name not in self.tables:
            raise ModuleNotFoundError(f'Table {table_name} doesn\'t exist!')
        info = self.tables[table_name]
        table = pd.read_csv('/'.join([PATH, info['path']]), sep=info['sep'], index_col=info['pk'])
        if info['force_str']:
            table.index = table.index.map(str)
        return info, table

    def add_record(self, table_name, values):
        if table_name not in self.tables:
            raise ModuleNotFoundError(f'Table {table_name} doesn\'t exist!')
        info = self.tables[table_name]
        if not info['allow_append']:
            raise PermissionError(f'It is not allowed to append to table {table_name}!')
        new_index = sha256(str(values).encode('utf-8')).hexdigest()[:10]
        if info['pk'] is not None:
            table = pd.read_csv('/'.join([PATH, info['path']]), sep=info['sep'], index_col=info['pk'])
            new_index = np.max(table.index.values) + 1
        values = [new_index, *values]
        with open('/'.join([PATH, info['path']]), 'a') as f:
            f.write(info['sep'].join(list(map(str, values))) + '\n')

    def update_or_add_record(self, table_name, pk, values):
        info, table = self._get_table(table_name)
        if not info['allow_append']:
            raise PermissionError(f'It is not allowed to update table {table_name}!')
        table.loc[pk] = values
        table.to_csv('/'.join([PATH, info['path']]), sep=info['sep'])

    def find_record_by_pk(self, table_name, pk, fields):
        info, table = self._get_table(table_name)
        if pk not in table.index:
            raise KeyError(f'Index {pk} not found in table {table_name}')
        return table.loc[pk][fields]

    def get_table(self, table_name):
        _, table = self._get_table(table_name)
        return table

