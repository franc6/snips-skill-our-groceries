#!/usr/bin/env bash

MSGFMT=/usr/local/Cellar/python/3.7.2_2/Frameworks/Python.framework/Versions/3.7/share/doc/python3.7/examples/Tools/i18n/msgfmt.py

for pofile in locales/*/LC_MESSAGES/messages.po
do
    dirname=`dirname "${pofile}"`
    filename=`basename -s .po "${pofile}"`
    mofile="${dirname}/${filename}.mo"
    needsUpdate=0
    if test -f "${mofile}" ; then
	# if ${mofile} exists, and ${pofile} is newer, we need to update
        if test "${pofile}" -nt "${mofile}" ; then
            needsUpdate=1
        fi
    else
        # if ${mofile} doesn't exist, then we need to update
        needsUpdate=1
    fi
    # Update only if needsUpdate is 1
    if test ${needsUpdate} -eq 1 ; then
        echo ${MSGFMT} -o "${mofile}" "${pofile}"
        ${MSGFMT} -o "${mofile}" "${pofile}"
    fi
done
