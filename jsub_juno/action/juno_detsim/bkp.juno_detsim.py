#!/usr/bin/env python

import os
import glob

def main():
	seed=os.environ.get('JSUB_detsim_seed_jobvar')
	max_event=os.environ.get('JSUB_max_event')
	output=os.environ.get('JSUB_detsim_output_jobvar')
	user_output=os.environ.get('JSUB_detsim_user_output_jobvar')
	additional_args=os.environ.get('JSUB_detsim_additional_args_jobvar','')

	juno_top=os.environ.get('JSUB_JUNO_top')

	os.system('source ~/misc/setup.sh')

#	os.system('cp %s %s'%(os.path.join(juno_top,'setup.sh'),'./juno_env.sh'))
#	os.system("sed -i 's/source /source `pwd`\//g' ./juno_env.sh")

#	os.system('cat ./juno_env.sh')

#	os.system('source %s'%'./juno_env.sh')

#	os.system('echo JUNOTOP = $JUNOTOP')

	detsim_cmd='python $JUNOTOP/offline/Examples/Tutorial/share/tut_detsim.py'
	detsim_cmd+=' --evtmax %s'%max_event
	detsim_cmd+=' --seed %s'%seed
	detsim_cmd+=' --output %s'%output
	detsim_cmd+=' --user-output %s'%user_output
	detsim_cmd+=additional_args

	#create dir for output/user-output
	output_dir=os.path.dirname(output)
	if not os.path.exists(output_dir):
		os.system('mkdir -p %s'%output_dir)

	user_output_dir=os.path.dirname(user_output)
	if not os.path.exists(user_output_dir):
		os.system('mkdir -p %s'%user_output_dir)

	#run detsim
	print(detsim_cmd)
	os.system(detsim_cmd)
	

if __name__ == '__main__':
	exit(main())
