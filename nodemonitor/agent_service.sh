#!/bin/bash
#
# chkconfig: 2345  80 50
# description: node monitor agent service
#
# processname: agent.py
#
PATH=${PATH}:/usr/local/bin:/usr/local/sbin
nmhome=~/node-monitor
pname=agent.py
ret=0


start() {
    pid=`ps -ef | grep ${pname} | grep -v grep | awk '{print $2}'`
    if [ -n "${pid}" ] ; then
        echo "${pname} is running with ${pid}..."
        return 127
    fi
    echo -n "starting ${pname}"
    python ${nmhome}/agent.py master_addr> ${nmhome}/agent.log 2>&1 &
    ret=$?
    if [ $ret -eq 0 ] ; then
        echo "[success]"
    else
        echo "[failed]"
    fi
    return $ret
}

status() {
    pid=`ps -ef | grep ${pname} | grep -v grep | awk '{print $2}'`
    if [ -n "${pid}" ] ; then
        echo "${pname} is running with pid ${pid}..."
        ret=0
    else
        echo "${pname} stopped"
        ret=1
    fi
}

stop() {
    pid=`ps -ef | grep ${pname} | grep -v grep | awk '{print $2}' | xargs`
    if [ -n "${pid}" ] ; then
        echo -n "stopping ${pname}"
        kill -9 ${pid}
        ret=$?
        if [ $ret -eq 0 ] ; then
            echo "[success]"
        else
            echo "[failed]"
        fi
    else
        echo "${pname} is not running."
    fi
}

restart() {
    echo "restarting ${pname}..."
    stop
    sleep 3
    start
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