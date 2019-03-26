#!/usr/bin/env bash -e

VENV=venv

if [ ! -d "${VENV}" ]
then
    PYTHON=`which python3`

    if [ -z ${PYTHON} ]
    then
	echo "Could not find python!"
    fi
    virtualenv -p ${PYTHON} ${VENV}
fi

. ${VENV}/bin/activate

pip install -r requirements.txt

if [ ! -e config.ini ]
then
    cp config.ini.default config.ini
fi
