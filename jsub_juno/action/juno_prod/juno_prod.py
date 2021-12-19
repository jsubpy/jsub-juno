#!/usr/bin/env python

### Somehow not working. Use juno_prod.sh instead.

'''
This action module runs the production scripts in $TUTORIALROOT/share/
'''

import os


def safe_mkdir(directory):
	if directory == '':
		return 0
	if not os.path.exists(directory):
		os.makedirs(directory)


def main():
	step_type=os.environ.get('JSUB_step_type')
	
	seed=os.environ.get('JSUB_'+step_type+'_seed_jobvar')
	_input=os.environ.get('JSUB_'+step_type+'_input_jobvar')
	output=os.environ.get('JSUB_'+step_type+'_output_jobvar')
	user_output=os.environ.get('JSUB_'+step_type+'_user_output_jobvar')
	additional_args=os.environ.get('JSUB_'+step_type+'_additional_args_jobvar')
	
	juno_top=os.environ.get('JSUB_JUNO_top')
	evtmax=os.environ.get('JSUB_evtmax')
	rate=os.environ.get('JSUB_rate')

	do_dirac_output=os.environ.get('JSUB_dirac_output')
	if do_dirac_output == 'True':
		#redirect dir input/output to ./
		output = os.path.join('./',os.path.basename(output))
		user_output = os.path.join('./',os.path.basename(user_output))
	else:
		# create output dir
		output_dir = os.path.dirname(output)
		safe_mkdir(output_dir)
		user_output_dir = os.path.dirname(user_output)
		safe_mkdir(user_output_dir)


	# setup JUNO environment
	os.system('export CMTCONFIG=amd64_linux26')

	# can't run pushd/popd cmds in the script with subprocess
#	os.system('source %s'%os.path.join(juno_top,'setup.sh'))

	os.system('cp %s .'%os.path.join(juno_top,'setup.sh'))
	cwd=os.environ.get('PWD')
	os.system("sed -i 's/popd.*/cd $JUNOTOP/' setup.sh")
	os.system("sed -i 's/>& .*//' setup.sh")
	os.system("sed -i 's/pushd/cd/' setup.sh")
	os.system("sed -i 's/source /source .\//' setup.sh")
#	os.system('cat setup.sh')
	os.system('source ./setup.sh')
	os.system('cd %s'%cwd)

	# setup cmd
	cmd=''
	cmd_dir=os.path.join(juno_top,'offline/Examples/Tutorial/share/')
	if step_type == 'detsim':
		cmd_script='tut_detsim.py'
		cmd='python '+os.path.join(cmd_dir,cmd_script)
		cmd+=' --seed %s'%seed
		cmd+=' --evtmax %s'%evtmax
		cmd+=' --output %s'%output
		cmd+=' --user_output %s'%user_output
	elif step_type == 'elecsim':
		cmd_script='tut_det2elec.py'
		cmd='python '+os.path.join(cmd_dir,cmd_script)
		cmd+=' --seed %s'%seed
		cmd+=' --evtmax %s'%evtmax
		cmd+=' --input %s'%_input
		cmd+=' --output %s'%output
		cmd+=' --user_output %s'%user_output
		cmd+=' --rate %s'%rate
	elif step_type == 'calib':
		cmd_script='tut_elec2calib.py'
		cmd='python '+os.path.join(cmd_dir,cmd_script)
		cmd+=' --evtmax %s'%evtmax
		cmd+=' --input %s'%_input
		cmd+=' --output %s'%output
		cmd+=' --user_output %s'%user_output
	elif step_type == 'rec':
		cmd_script='tut_calib2rec.py'
		cmd='python '+os.path.join(cmd_dir,cmd_script)
		cmd+=' --evtmax %s'%evtmax
		cmd+=' --input %s'%_input
		cmd+=' --output %s'%output
	elif step_type == 'calib-woelec':
		cmd_script='tut_det2calib.py'
		cmd='python '+os.path.join(cmd_dir,cmd_script)
		cmd+=' --evtmax %s'%evtmax
		cmd+=' --input %s'%_input
		cmd+=' --output %s'%output
	elif step_type == 'rec-woelec':
		cmd_script='tut_calib2rec.py'
		cmd='python '+os.path.join(cmd_dir,cmd_script)
		cmd+=' --evtmax %s'%evtmax
		cmd+=' --input %s'%_input
		cmd+=' --output %s'%output
	cmd+=' %s'%additional_args


	#run cmd
	print('Running command: %s'%cmd)
	os.system(cmd)

if __name__ == '__main__':
	exit(main())


