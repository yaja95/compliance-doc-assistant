-- Creates a separate database for the test suite so tests never touch dev data.
-- Runs automatically on first container startup (docker-entrypoint-initdb.d convention).
CREATE DATABASE compliance_doc_assistant_test;
\connect compliance_doc_assistant_test
CREATE EXTENSION IF NOT EXISTS vector;
