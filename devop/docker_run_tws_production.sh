#!/usr/bin/env bash
# docker build ./ib-docker -t tws

docker run --link ip_betasmartz_app:ip \
		   -e "TZ=America/New York" \
		   -e "VNC_PASSWORD="${TWSVNCPASSWORD} \
		   -e "TWS_MAJOR_VRSN=964" \
	       -e "IBC_INI=/root/IBController/IBController.ini" \
	       -e "TRADING_MODE=trade" \
	       -e "IBC_PATH=/opt/IBController" \
	       -e "TWS_PATH=/root/Jts" \
	       -e "TWS_CONFIG_PATH=/root/Jts" \
	       -e "LOG_PATH=/opt/IBController/Logs" \
	       -e "TWSUSERID="${TWSUSERID} \
	       -e "TWSPASSWORD="${TWSPASSWORD} \
	       -e "APP=GATEWAY" \
		   -p 4003 \
		   --net=betasmartz-local -d --name=tws tws