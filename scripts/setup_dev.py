"""Create ignored local configuration without overwriting existing credentials."""

import secrets
from pathlib import Path

root = Path(__file__).resolve().parents[1]
config = root / '.env'
if not config.exists():
    content = (root / '.env.example').read_text(encoding='utf-8')
    content = content.replace('JWT_SECRET=\n', f'JWT_SECRET={secrets.token_urlsafe(48)}\n')
    content = content.replace('POSTGRES_PASSWORD=\n', f'POSTGRES_PASSWORD={secrets.token_urlsafe(36)}\n')
    config.write_text(content, encoding='utf-8')
    print('Created .env with generated development credentials.')
else:
    print('Kept existing .env.')

mobile = root / 'apps/mobile/.env'
if not mobile.exists():
    mobile.write_text((root / 'apps/mobile/.env.example').read_text(encoding='utf-8'), encoding='utf-8')
    print('Created mobile public configuration.')
else:
    print('Kept existing mobile configuration.')
