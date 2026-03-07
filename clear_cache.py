
# Run this in your invoiceiq directory:
# python clear_cache.py

import os
import sys

# Delete all .pyc files in the invoices app
app_dir = os.path.join(os.path.dirname(__file__), 'apps', 'invoices')

deleted = 0
for root, dirs, files in os.walk(app_dir):
    # Remove __pycache__ dirs
    for d in dirs:
        if d == '__pycache__':
            cache_dir = os.path.join(root, d)
            for f in os.listdir(cache_dir):
                if f.endswith('.pyc'):
                    os.remove(os.path.join(cache_dir, f))
                    deleted += 1
                    print(f'Deleted: {os.path.join(cache_dir, f)}')

print(f'\nDeleted {deleted} .pyc files')
print('Now restart your Django server with: python manage.py runserver')
