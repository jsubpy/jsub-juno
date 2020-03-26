#!/bin/sh

seed=$JSUB_detsim_seed_jobvar
max_event=$JSUB_max_event
output=$JSUB_detsim_output_jobvar
user_output=$JSUB_detsim_user_output_jobvar
additional_args=$JSUB_detsim_additional_args_jobvar


#output is handled by dirac_upload action instead.
if [ "$JSUB_dirac_output" == "True" ]; then
	#redirect output to ../
	output="../"${output##*/}
	user_output="../"${user_output##*/}
fi


juno_top=$JSUB_JUNO_top

#source $juno_top/setup.sh

#make jsub version of juno_env script
cp $juno_top/setup.sh `pwd`/juno_env.sh
sed -i 's/source /source `pwd`\//g' `pwd`/juno_env.sh

export CMTCONFIG='amd64_linux26'
source `pwd`/juno_env.sh


#setup command
detsim_cmd="python $JUNOTOP/offline/Examples/Tutorial/share/tut_detsim.py"
detsim_cmd=$detsim_cmd' --evtmax '$max_event
detsim_cmd=$detsim_cmd' --seed '$seed
detsim_cmd=$detsim_cmd' --output '$output 
detsim_cmd=$detsim_cmd' --user-output '$user_output 
detsim_cmd=$detsim_cmd' '$additional_args



#create output dir
output_dir=$(dirname $output)
mkdir -p output_dir
user_output_dir=$(dirname $user_output)
mkdir -p user_output_dir

#PYTHONPATH=echo $PYTHONPATH | sed 's/Linux-x86_64/amd64_linux26/g'

#run detsim cmd
echo 'Running Command:' $detsim_cmd
$detsim_cmd
