#!/bin/bash


evtmax=$JSUB_evtmax
rate=$JSUB_rate
gdml_file=$JSUB_gdml_file

eval seed='$JSUB_'$JSUB_step_type'_seed_jobvar'
eval output='$JSUB_'$JSUB_step_type'_output_jobvar'
eval user_output='$JSUB_'$JSUB_step_type'_user_output_jobvar'
eval additional_args='$JSUB_'$JSUB_step_type'_additional_args_jobvar'
eval full_args='$JSUB_'$JSUB_step_type'_full_args_jobvar'
eval input='$JSUB_'$JSUB_step_type'_input_jobvar'
eval momentums='$JSUB_'$JSUB_step_type'_momentums_jobvar'
eval particles='$JSUB_'$JSUB_step_type'_particles_jobvar'
eval positions='$JSUB_'$JSUB_step_type'_positions_jobvar'
eval volume='$JSUB_'$JSUB_step_type'_volume_jobvar'
eval material='$JSUB_'$JSUB_step_type'_material_jobvar'


# for condor backend, the output data should be under certain folder
data_folder=$JSUB_data_folder

# for dirac backend, redirec input/output folder to ./; so that the files can be uploaded/downloaded
if [ "$JSUB_dirac_input" == "True" ]; then
	#redirect input to ./
	input="./"${input##*/}
fi

if [ "$JSUB_dirac_output" == "True" ]; then
	#redirect output to ./
	output="./"${output##*/}
	user_output="./"${user_output##*/}
else
	#create output/user_output dir
	if [[ -n $output  ]]; then 
		if [[ -n $data_folder ]]; then
			output=$data_folder"/"$output
		fi
		output_dir=$(dirname $output)
		mkdir -p $output_dir
	fi
	if [[ -n $user_output  ]]; then 
		if [[ -n $data_folder ]]; then
			user_output=$data_folder"/"$user_output
		fi
		user_output_dir=$(dirname $user_output)
		mkdir -p $user_output_dir
	fi
fi


# setup JUNO environment
juno_top=$JSUB_JUNO_top
export CMTCONFIG='amd64_linux26'

source $juno_top/../../contrib/gcc/*/bashrc
source $juno_top/../../contrib/binutils/*/bashrc
source $juno_top/../../../*/contrib/compat/bashrc

#can't run pushd/popd cmds in the JUNO setup script
#source $juno_top/setup.sh
cp $juno_top/setup.sh .
org_dir=`pwd`
sed -i 's/popd.*/cd $JUNOTOP/' ./setup.sh
sed -i 's/>& .*//' ./setup.sh
sed -i 's/pushd/cd/' ./setup.sh
sed -i 's/source /source .\//' ./setup.sh
#cat ./setup.sh
source ./setup.sh
cd $org_dir

cmd="python $juno_top/offline/Examples/Tutorial/share/"

# add root file types
if [[ ! $input =~ .*root  ]]; then
	input=$input'.root'
fi
if [[ ! $output =~ .*root  ]]; then
	output=$output'.root'
fi
if [[ ! $user_output =~ .*root  ]]; then
	user_output=$user_output'.root'
fi

if [ "$JSUB_step_type" == "detsim" ]; then
	cmd=$cmd'tut_detsim.py'
	cmd_arg=$cmd_arg'  --evtmax '$evtmax
	cmd_arg=$cmd_arg'  --seed '$seed
	cmd_arg=$cmd_arg'  --output '$output
	cmd_arg=$cmd_arg'  --user-output '$user_output
elif [ "$JSUB_step_type" == "elecsim" ]; then
	cmd=$cmd'tut_det2elec.py'
	cmd_arg=$cmd_arg'  --evtmax '$evtmax
	cmd_arg=$cmd_arg'  --seed '$seed
	cmd_arg=$cmd_arg'  --input '$input
	cmd_arg=$cmd_arg'  --output '$output
	cmd_arg=$cmd_arg'  --user-output '$user_output
	cmd_arg=$cmd_arg'  --rate '$rate
elif [ "$JSUB_step_type" == "calib" ]; then
	cmd=$cmd'tut_elec2calib.py'
	cmd_arg=$cmd_arg'  --evtmax '$evtmax
	cmd_arg=$cmd_arg'  --input '$input
	cmd_arg=$cmd_arg'  --output '$output
	cmd_arg=$cmd_arg'  --user-output '$user_output
elif [ "$JSUB_step_type" == "rec" ]; then
	if [ -z "$gdml_file" ]; then
		gdml_file=`find |grep gdml`
	fi

	cmd=$cmd'tut_calib2rec.py'
	cmd_arg=$cmd_arg'  --evtmax '$evtmax
	cmd_arg=$cmd_arg'  --input '$input
	cmd_arg=$cmd_arg'  --output '$output
	cmd_arg=$cmd_arg'  --user-output '$user_output
	if [ -n "$gdml_file" ]; then
		cmd_arg=$cmd_arg'  --gdml-file '$gdml_file
	fi
elif [ "$JSUB_step_type" == "calib_woelec" ]; then
	cmd=$cmd'tut_det2calib.py'
	cmd_arg=$cmd_arg'  --evtmax '$evtmax
	cmd_arg=$cmd_arg'  --input '$input
	cmd_arg=$cmd_arg'  --output '$output
#	cmd_arg=$cmd_arg'  --user-output '$user_output
elif [ "$JSUB_step_type" == "rec_woelec" ]; then
	cmd=$cmd'tut_calib2rec.py'
	cmd_arg=$cmd_arg'  --evtmax '$evtmax
	cmd_arg=$cmd_arg'  --input '$input
	cmd_arg=$cmd_arg'  --output '$output
#	cmd_arg=$cmd_arg'  --user-output '$user_output
	if [ -n "$gdml_file" ]; then
		cmd_arg=$cmd_arg'  --gdml-file '$gdml_file
	fi
fi

cmd_arg=$cmd_arg'  '$additional_args
gun_param=''
if [ -n "$momentums" ]; then
	gun_param=$gun_param' --momentums '$momentums
fi
if [ -n "$particles" ]; then
    gun_param=$gun_param' --particles '$particles
fi
if [ -n "$positions" ]; then
    gun_param=$gun_param' --positions '$positions
fi
if [ -n "$material" ]; then
    gun_param=$gun_param' --material '$material
fi
if [ -n "$volume" ]; then
    gun_param=$gun_param' --volume '$volume
fi

if [ -n "$gun_param" ]; then
	cmd_arg=$cmd_arg' gun '$gun_param
fi

cmd_full=$cmd' '$cmd_arg
if [ -n "$full_args" ]; then
	cmd_full=$cmd' '$full_args
fi


echo 'Running command:' $cmd_full

$JUNOTOP/offline/Validation/JunoTest/production/libs/jobmom.sh $$ >& log-${JSUB_step_type}-${seed}.txt.mem.usage &

$cmd_full

exit $?
