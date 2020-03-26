import os
import subprocess
from jsub.error import JsubError

class JunoScenarioError(JsubError):
	pass

class Juno(object):
	def __init__(self, param):
		self.scenario_input = param
		self.scenario_param = {}
	
	def build(self, backend):
		job_steps=self.scenario_input.get('job_steps')
		if type(job_steps)!=type([]):
			job_steps=[job_steps]

		#deal with splitter
		splitter=self.scenario_input.get('splitter')

	
		#JUNO environment
		if 'JUNO_top' not in self.scenario_input:
			juno_top = '/cvmfs/juno.ihep.ac.cn/sl6_amd64_gcc494/Pre-Release/J19v1r0-Pre3'
		else:
			juno_top = self.scenario_input.get('JUNO_top')
		
		#build workflow
		workflow={}

		#build input sandbox
		input_sandbox={'common':{}}


		#detsim
		if 'detsim' in job_steps:
			workflow['detsim']={'type':'juno_detsim','actvar':{},'depend_on':[]}
			detsim_input=self.scenario_input.get('detsim')
		
			#juno top
			workflow['detsim']['actvar']['JUNO_top'] = juno_top
			#max event
			workflow['detsim']['actvar']['max_event']=detsim_input.get('max_event',1)
			#output
			if 'output' not in detsim_input:
				raise JunoScenarioError('output not defined for detsim')
			splitter['jobvar_lists']['detsim_output_jobvar']={'type':'composite_string','param':{'value': detsim_input.get('output')}}
			#user output
			if 'user_output' not in detsim_input:
				raise JunoScenarioError('user_output not defined for detsim')
			splitter['jobvar_lists']['detsim_user_output_jobvar']={'type':'composite_string','param':{'value': detsim_input.get('user_output')}}
			#additional args
			if 'additional_args' in detsim_input:
				splitter['jobvar_lists']['detsim_additional_args_jobvar']={'type':'composite_string','param':{'value': detsim_input.get('additional_args')}}
			#seed
			if 'seed' not in detsim_input:
				splitter['jobvar_lists']['detsim_seed_jobvar']={'type':'range','param':{'first':1,'step':1}}
			else:
				splitter['jobvar_lists']['detsim_seed_jobvar']={'type':'composite_string','param':{'value': detsim_input.get('seed')}}



		if backend['name']=='dirac':
			#define dirac-upload job step
			if 'detsim' in job_steps:
				workflow['dirac_upload_detsim_output']={'type':'dirac_upload','actvar':{},'depend_on':['detsim']}
				workflow['dirac_upload_detsim_output']['actvar']['upload_file_jobvar']='detsim_output_jobvar'	
				workflow['dirac_upload_detsim_output']['actvar']['overwrite']='True'	
				#change behavior of 'detsim' action:	output to ../
				workflow['detsim']['actvar']['dirac_output']='True'


		#build scenario				
		self.scenario_param['input']=input_sandbox
		self.scenario_param['splitter']=splitter
		self.scenario_param['workflow']=workflow
		
		return self.scenario_param

			
