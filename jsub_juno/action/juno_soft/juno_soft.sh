#!/bin/sh

#setup JUNO environment
junoTop=$JSUB_JUNO_top
export CMTCONFIG='amd64_linux26'

#workaround of source $juno_top/setup.sh
cp $junoTop/setup.sh .
org_dir=`pwd`
sed -i 's/popd.*/cd $JUNOTOP/' ./setup.sh
sed -i 's/>& .*//' ./setup.sh
sed -i 's/pushd/cd/' ./setup.sh
sed -i 's/source /source .\//' ./setup.sh
#cat ./setup.sh
source ./setup.sh
cd $org_dir

software=$JSUB_JUNO_top/$JSUB_software

if [ -n "$JSUB_argument_jobvar" ]; then
	eval JSUB_argument='$JSUB_'$JSUB_argument_jobvar
fi

cmd="$software $JSUB_argument"

echo 'Running command:' "$cmd"
eval $cmd


