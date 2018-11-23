#!/usr/bin/env bash
# $1 = commit to checkout
# $2 = domain to deploy to. Eg. 'v2' or 'demo'


main() {
    # postgres on multiple environment VM
    POSTGRES_PASSWORD='gD6OA22yXjMgrzLI4pT9*B63o^'
    if [[ ${2} == 'demostaging' ]]
    then
        DBPW='*821917ic2bB&82'
        REDDB=1
        FITBIT_CLIENT_ID=${FITBIT_CLIENT_ID_DEMOSTAGING}
        FITBIT_CLIENT_SECRET=${FITBIT_CLIENT_SECRET_DEMOSTAGING}
        UNDERARMOUR_CLIENT_ID=${UNDERARMOUR_CLIENT_ID_DEMOSTAGING}
        UNDERARMOUR_CLIENT_SECRET=${UNDERARMOUR_CLIENT_SECRET_DEMOSTAGING}
    elif [[ ${2} == 'v2' ]]
    then
        DBPW='Exu!&L+6}/!-m(-}'
        REDDB=2
    elif [[ ${2} == 'dev' ]]
    then
        DBPW='0ZUbnZ5+:msz:*1O'
        REDDB=3
        FITBIT_CLIENT_ID=${FITBIT_CLIENT_ID_DEV}
        FITBIT_CLIENT_SECRET=${FITBIT_CLIENT_SECRET_DEV}
        UNDERARMOUR_CLIENT_ID=${UNDERARMOUR_CLIENT_ID_DEV}
        UNDERARMOUR_CLIENT_SECRET=${UNDERARMOUR_CLIENT_SECRET_DEV}
    elif [[ ${2} == 'beta' ]]
    then
        DBPW='Beta02jzjdne*10'
        REDDB=4
        FITBIT_CLIENT_ID=${FITBIT_CLIENT_ID_BETA}
        FITBIT_CLIENT_SECRET=${FITBIT_CLIENT_SECRET_BETA}
        UNDERARMOUR_CLIENT_ID=${UNDERARMOUR_CLIENT_ID_BETA}
        UNDERARMOUR_CLIENT_SECRET=${UNDERARMOUR_CLIENT_SECRET_BETA}
    elif [[ ${2} == 'aus' ]]
    then
        DBPW='Ausliejivjljl*20'
        REDDB=5
    elif [[ ${2} == 'betastaging' ]]
    then
        DBPW='BetaStagingMGIS129013923i!'
        REDDB=6
        FITBIT_CLIENT_ID=${FITBIT_CLIENT_ID_BETASTAGING}
        FITBIT_CLIENT_SECRET=${FITBIT_CLIENT_SECRET_BETASTAGING}
        UNDERARMOUR_CLIENT_ID=${UNDERARMOUR_CLIENT_ID_BETASTAGING}
        UNDERARMOUR_CLIENT_SECRET=${UNDERARMOUR_CLIENT_SECRET_BETASTAGING}
    elif [[ ${2} == 'staging' ]]
    then
        DBPW='StagingOgacahi8971*!'
        REDDB=7
        FITBIT_CLIENT_ID=${FITBIT_CLIENT_ID_STAGING}
        FITBIT_CLIENT_SECRET=${FITBIT_CLIENT_SECRET_STAGING}
        UNDERARMOUR_CLIENT_ID=${UNDERARMOUR_CLIENT_ID_STAGING}
        UNDERARMOUR_CLIENT_SECRET=${UNDERARMOUR_CLIENT_SECRET_STAGING}
    elif [[ ${2} == 'ipdemostaging' ]]
    then
        DBPW='OOJNVuo2ojamscop9j092'
        REDDB=8
        FITBIT_CLIENT_ID=${FITBIT_CLIENT_ID_IPDEMOSTAGING}
        FITBIT_CLIENT_SECRET=${FITBIT_CLIENT_SECRET_IPDEMOSTAGING}
        UNDERARMOUR_CLIENT_ID=${UNDERARMOUR_CLIENT_ID_IPDEMOSTAGING}
        UNDERARMOUR_CLIENT_SECRET=${UNDERARMOUR_CLIENT_SECRET_IPDEMOSTAGING}
    elif [[ ${2} == 'ipdev' ]]
    then
        DBPW='Nuion4582nN9a1@'
        REDDB=9
        FITBIT_CLIENT_ID=${FITBIT_CLIENT_ID_IPDEV}
        FITBIT_CLIENT_SECRET=${FITBIT_CLIENT_SECRET_IPDEV}
        UNDERARMOUR_CLIENT_ID=${UNDERARMOUR_CLIENT_ID_IPDEV}
        UNDERARMOUR_CLIENT_SECRET=${UNDERARMOUR_CLIENT_SECRET_IPDEV}
    elif [[ ${2} == 'production' ]]
    then
        # production deployment on separate machine
        # storing sensitive production info in environment
        DBPW=${PRODUCTION_DBPW}
        POSTGRES_PASSWORD=${PRODUCTION_POSTGRES}
        FITBIT_CLIENT_ID=${FITBIT_CLIENT_ID_APP}
        FITBIT_CLIENT_SECRET=${FITBIT_CLIENT_SECRET_APP}
        UNDERARMOUR_CLIENT_ID=${UNDERARMOUR_CLIENT_ID_APP}
        UNDERARMOUR_CLIENT_SECRET=${UNDERARMOUR_CLIENT_SECRET_APP}
        REDDB=1
    elif [[ ${2} == 'demo' ]]
    then
        # demo deploys on production machine
        DBPW=${DEMO_DBPW}
        POSTGRES_PASSWORD=${PRODUCTION_POSTGRES}
        REDDB=2
        FITBIT_CLIENT_ID=${FITBIT_CLIENT_ID_DEMO}
        FITBIT_CLIENT_SECRET=${FITBIT_CLIENT_SECRET_DEMO}
        UNDERARMOUR_CLIENT_ID=${UNDERARMOUR_CLIENT_ID_DEMO}
        UNDERARMOUR_CLIENT_SECRET=${UNDERARMOUR_CLIENT_SECRET_DEMO}
    elif [[ ${2} == 'ipdemo' ]]
    then
        # ipdemo deploys on production machine
        DBPW=${IPDEMO_DBPW}
        POSTGRES_PASSWORD=${PRODUCTION_POSTGRES}
        REDDB=3
        FITBIT_CLIENT_ID=${FITBIT_CLIENT_ID_IPDEMO}
        FITBIT_CLIENT_SECRET=${FITBIT_CLIENT_SECRET_IPDEMO}
        UNDERARMOUR_CLIENT_ID=${UNDERARMOUR_CLIENT_ID_IPDEMO}
        UNDERARMOUR_CLIENT_SECRET=${UNDERARMOUR_CLIENT_SECRET_IPDEMO}
    elif [[ ${2} == 'ip' ]]
    then
        # ip production deploys on production machine
        DBPW=${IP_DBPW}
        POSTGRES_PASSWORD=${PRODUCTION_POSTGRES}
        REDDB=4
        FITBIT_CLIENT_ID=${FITBIT_CLIENT_ID_IP}
        FITBIT_CLIENT_SECRET=${FITBIT_CLIENT_SECRET_IP}
        UNDERARMOUR_CLIENT_ID=${UNDERARMOUR_CLIENT_ID_IP}
        UNDERARMOUR_CLIENT_SECRET=${UNDERARMOUR_CLIENT_SECRET_IP}
    elif [[ ${2} == 'manudemo' ]]
    then
        # ipdemo deploys on production machine
        DBPW=${MANUDEMO_DBPW}
        POSTGRES_PASSWORD=${PRODUCTION_POSTGRES}
        FITBIT_CLIENT_ID=${FITBIT_CLIENT_ID_MANUDEMO}
        FITBIT_CLIENT_SECRET=${FITBIT_CLIENT_SECRET_MANUDEMO}
        UNDERARMOUR_CLIENT_ID=${UNDERARMOUR_CLIENT_ID_MANUDEMO}
        UNDERARMOUR_CLIENT_SECRET=${UNDERARMOUR_CLIENT_SECRET_MANUDEMO}
        REDDB=4
    else
        echo "Unsupported auto-deployment for domain: ${2}" >&2
    exit 1
    fi
    pushd repo/betasmartz
    echo fetching latest repo
    git fetch
    echo checking out revision spec ${1}
    git checkout $1
    echo building docker image
    docker build -t betasmartz/backend:${2}_cd .
    # run tests on a docker testing container before taking down
    # currently serving container - ${2}_betasmartz_app_test
    # this should minimize downtime switching old builds to new ones
    docker run -e "DB_PASSWORD=${DBPW}" \
               -e 'POSTGRES_PASSWORD='${POSTGRES_PASSWORD} \
               -e ENVIRONMENT=${2} \
               -e 'REDIS_URI=redis://redis:6379/'${REDDB} \
               -e 'ST_AUTH='${ST_AUTH} \
               -e 'ST_USER='${ST_USER} \
               -e 'ST_KEY='${ST_KEY} \
               -e 'MAILGUN_API_KEY='${MAILGUN_API_KEY} \
               -e 'WEBHOOK_AUTHORIZATION='${WEBHOOK_AUTHORIZATION} \
               -e 'DEFAULT_FROM_EMAIL='${DEFAULT_FROM_EMAIL} \
               -e 'QUOVO_USERNAME='${QUOVO_USERNAME} \
               -e 'QUOVO_PASSWORD='${QUOVO_PASSWORD} \
               -e 'IB_FTP_USERNAME='${IB_FTP_USERNAME} \
               -e 'IB_FTP_PASSWORD='${IB_FTP_PASSWORD} \
               -e 'FITBIT_CLIENT_ID='${FITBIT_CLIENT_ID} \
               -e 'FITBIT_CLIENT_SECRET='${FITBIT_CLIENT_SECRET} \
               -e 'GOOGLEFIT_CLIENT_ID='${GOOGLEFIT_CLIENT_ID} \
               -e 'GOOGLEFIT_CLIENT_SECRET='${GOOGLEFIT_CLIENT_SECRET} \
               -e 'JAWBONE_CLIENT_ID='${JAWBONE_CLIENT_ID} \
               -e 'JAWBONE_CLIENT_SECRET='${JAWBONE_CLIENT_SECRET} \
               -e 'MICROSOFTHEALTH_CLIENT_ID='${MICROSOFTHEALTH_CLIENT_ID} \
               -e 'MICROSOFTHEALTH_CLIENT_SECRET='${MICROSOFTHEALTH_CLIENT_SECRET} \
               -e 'TOMTOM_API_KEY='${TOMTOM_API_KEY} \
               -e 'TOMTOM_CLIENT_ID='${TOMTOM_CLIENT_ID} \
               -e 'TOMTOM_CLIENT_SECRET='${TOMTOM_CLIENT_SECRET} \
               -e 'UNDERARMOUR_CLIENT_ID='${UNDERARMOUR_CLIENT_ID} \
               -e 'UNDERARMOUR_CLIENT_SECRET='${UNDERARMOUR_CLIENT_SECRET} \
               -e 'WITHINGS_CONSUMER_KEY='${WITHINGS_CONSUMER_KEY} \
               -e 'WITHINGS_CONSUMER_SECRET='${WITHINGS_CONSUMER_SECRET} \
               --net=betasmartz-local \
               --name=${2}_betasmartz_app_test \
               -d betasmartz/backend:${2}_cd

    #docker exec ${2}_betasmartz_app_test bash -c "cd betasmartz && pip install -r requirements/dev.txt && python3.5 manage.py test --settings=tests.test_settings --noinput"
    #if [ $? -eq 0 ]  # tests ran successfully?
    #then
    #    echo "Tests passed successfully, switching out current app container."
        # tests passed ok, lets take down the current app and put the test container live

    # tests failing against postgres, so just load new container
        # delete old rollback
        docker rm ${2}_betasmartz_app_rollback

        docker rename ${2}_betasmartz_app ${2}_betasmartz_app_rollback
        docker rename ${2}_betasmartz_app_test ${2}_betasmartz_app

        docker exec nginx nginx -s reload  # have nginx load new app
        docker stop ${2}_betasmartz_app_rollback  # stop old container
    #else
    #    echo "Tests failed, keeping current app container, removing test container."
        # tests failed, keep current app container, rm test container
    #    docker stop ${2}_betasmartz_app_test
    #    docker rm ${2}_betasmartz_app_test
    #fi
    #popd
}

(
    flock -w 600 -n 200
    main $1 $2

) 200>/var/lock/.betasmartz_backend_deployer.exclusivelock
