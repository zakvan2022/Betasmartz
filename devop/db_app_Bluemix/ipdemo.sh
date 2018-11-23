export PGUSER=postgres
psql <<- EOSQL
    CREATE USER betasmartz_ipdemo;
    CREATE DATABASE betasmartz_ipdemo;
    GRANT ALL PRIVILEGES ON DATABASE betasmartz_ipdemo TO betasmartz_ipdemo;
EOSQL