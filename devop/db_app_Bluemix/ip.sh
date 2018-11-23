export PGUSER=postgres
psql <<- EOSQL
    CREATE USER betasmartz_ip;
    CREATE DATABASE betasmartz_ip;
    GRANT ALL PRIVILEGES ON DATABASE betasmartz_ip TO betasmartz_ip;
EOSQL