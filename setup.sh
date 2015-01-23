#! /bin/bash

PKG="yeast"

if [ "$UID" != "0" ]; then
    echo
    echo "Error, exit !! Please run as root!"
    echo
    exit 1
fi

BASEDIR="/usr/share/yeast"

dst=$(python -c "import os; print os.path.dirname(os.__file__)")
dst="$dst/site-packages"

function removeold ()  {
    # clean old version
    if [ ! -z "$dst" ]; then
        rm -fr $dst/$PKG
    fi
}

function installnew () {
    echo install to $dst
    
    mkdir -p $dst/$PKG/
    cp -a ./src/* $dst/$PKG/
}


case "$1" in 
    install)
        installnew
        ;;
    remove)
        removeold
        ;;
    *)
        echo "Usage: $0 {install|remove}"
        exit 1
esac
exit 0
