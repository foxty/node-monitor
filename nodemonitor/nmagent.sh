#!/bin/sh
#
# chkconfig: 2345  80 50
# description: node monitor agent service
#
# processname: agent.py
#
PATH=${PATH}:/usr/local/bin:/usr/local/sbin
nmhome=/root/node-monitor
pname=agent.py
ret=0

start() {
    result=$( ps -ef | grep ${pname} | grep -v grep | wc -l )
    if [ $result -gt 0 ] ; then
        echo "${pname} is running, now stop it..."
        stop
    fi
    echo "starting ${pname}"
    python ${nmhome}/agent.py -c ${nmhome}/agent.json master_host > ${nmhome}/agent.log 2>&1 &
    ret=$?
    echo "[success]"
}

stop() {
    echo "stopping ${pname}"
    pids=$(ps -ef | grep ${pname} | grep -v grep | awk '{print $2}')
    kill -9 ${pids}
    ret=$?
    if [ $ret -eq 0 ] ; then
        echo "[success]"
    else
        echo "[failed]"
    fi
}

restart() {
    echo "restarting ${pname}..."
    stop
    sleep 3
    start
}

status() {
    local result
    result=$( ps -ef | grep ${pname} | grep -v grep | wc -l )
    if [ $result -gt 0 ] ; then
        echo "${pname} is running..."
        ret=0
    else
        echo "${pname} stopped"
        ret=1
    fi
}

# See how we were called.
case "$1" in
  start)
        start
        ;;
  stop)
        stop
        ;;
  status)
        status
        ;;
  restart)
        restart
        ;;
  *)
        echo $"Usage: $0 {start|stop|restart|status}"
        exit 1
esac

exit $ret