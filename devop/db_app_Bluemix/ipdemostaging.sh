export PGUSER=postgres
psql <<- EOSQL
    CREATE USER betasmartz_ipdemostaging;
    CREATE DATABASE betasmartz_ipdemostaging;
    GRANT ALL PRIVILEGES ON DATABASE betasmartz_ipdemostaging TO betasmartz_ipdemostaging;
EOSQL