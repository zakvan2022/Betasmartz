export PGUSER=postgres
psql <<- EOSQL
    CREATE USER betasmartz_ipdev;
    CREATE DATABASE betasmartz_ipdev;
    GRANT ALL PRIVILEGES ON DATABASE betasmartz_ipdev TO betasmartz_ipdev;
EOSQL