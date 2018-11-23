export PGUSER=postgres
psql <<- EOSQL
    CREATE USER betasmartz_oreana;
    CREATE DATABASE betasmartz_oreana;
    GRANT ALL PRIVILEGES ON DATABASE betasmartz_oreana TO betasmartz_oreana;
EOSQL