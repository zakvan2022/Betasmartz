export PGUSER=postgres
psql <<- EOSQL
	CREATE USER betasmartz_manudemo;
	CREATE DATABASE betasmartz_manudemo;
	GRANT ALL PRIVILEGES ON DATABASE betasmartz_manudemo TO betasmartz_manudemo;
EOSQL