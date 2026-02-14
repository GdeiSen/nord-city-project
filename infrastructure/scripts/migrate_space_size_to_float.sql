-- Миграция: площадь помещений (size) — поддержка десятых (десятичные числа)
-- Запуск: psql -U bot_user -d bot_database -f migrate_space_size_to_float.sql

ALTER TABLE object_spaces
  ALTER COLUMN size TYPE DOUBLE PRECISION USING size::double precision;
