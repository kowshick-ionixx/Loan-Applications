-- Runs once, when the postgres volume is first created.
-- pytest uses app_db_test (see tests/conftest.py); app_db is never touched by tests.
CREATE DATABASE app_db_test;
