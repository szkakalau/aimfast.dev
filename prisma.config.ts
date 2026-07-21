import { config } from 'dotenv';
import { defineConfig } from 'prisma/config';

// Prisma 7 doesn't auto-load .env — load .env then .env.local (overrides)
config({ path: '.env' });
config({ path: '.env.local', override: true });

export default defineConfig({
  schema: './prisma/schema.prisma',
  migrations: {
    path: './prisma/migrations',
  },
  datasource: {
    url: process.env['DATABASE_URL']!,
  },
});
