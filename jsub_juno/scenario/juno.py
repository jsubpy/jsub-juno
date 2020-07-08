import os
import ast
from jsub.error import JsubError
from copy import copy
import glob
from random import randint

class JunoScenarioError(JsubError):
	pass

class Juno(object):
	def __init__(self, param):
		self.scenario_input = param
		self.scenario_param = {}
	
	def build(self, backend):
		# validate that all required attributes exist in the setting
		def check_step(step, setting, attributes):
			for attr in attributes:
				if attr not in setting:
					raise JunoScenarioError('Attribute %s is not specified for step %s'%(attr,step))
			return None


		# JUNO environment
		if 'softVersion' not in self.scenario_input:
			# use default JUNO environment
			junoTop = '/cvmfs/juno.ihep.ac.cn/sl6_amd64_gcc494/Pre-Release/J19v1r0-Pre3'
		else:
			softVersion = self.scenario_input.get('softVersion')
			junoTop_list = glob.glob('/cvmfs/juno.ihep.ac.cn/*/*/%s/'%softVersion)
			if not junoTop_list:
				raise JunoScenarioError('No suitable environment on /cvmfs/ for JUNO version:%s'%softVersion)
			else:
				junoTop = junoTop_list[0]
		

		# build input sandbox
		input_sandbox={'common':{}}

		# deal with splitter
		splitter=self.scenario_input.get('splitter')

		# general setting
		outputSubDir= self.scenario_input.get('outputSubDir','')
		# users may define evtmax in splitter for their conveniences, or in general setting
		evtMax=splitter.get('evtMax',10)
		evtMax=splitter.get('evtMaxPerJob',evtMax)
		evtMax=self.scenario_input.get('evtMax',evtMax)
		evtMax=self.scenario_input.get('evtMaxPerJob',evtMax)

		workflow_input=self.scenario_input.get('workflow',{})
		job_steps=workflow_input.get('steps',[])
		job_steps=workflow_input.get('step',job_steps)
		job_steps=workflow_input.get('jobSteps',job_steps)
		# translate job_steps to standard list
		if type(job_steps)==str:
			job_steps.replace('[','')
			job_steps.replace(']','')
			job_steps=job_steps.split(',')
		elif type(job_steps)==list:
			pass
		

		splitterMode=splitter.get('mode','splitByEvent')
		if splitterMode in ['splitByEvent']:
			jobvarsToSeq={}
			jobvars={}
		elif splitterMode in ['splitByJobvars']:
			jobvar_lists=splitter.get('jobvar_lists',{})
		else:
			raise JunoScenarioError('Invalid splitter mode: %s'%splitterMode)


		# build workflow
		workflow={}
		previous_steps=[]
		for step in job_steps:
			step=step.lower()
			p_steps=copy(previous_steps)	#copy to avoid further modification on the same object

			workflow[step]={'type':'juno_prod','actvar':{'step_type':step},'depend_on':p_steps}
			previous_steps+=[step]

			# apply default settings:
			step_setting=workflow_input.get(step,{})

			
			#	1. soft version should come from general setting
			workflow[step]['actvar']['JUNO_top'] = junoTop
			#	2. evtmax should come from general setting; or overwrited by step setting
			s_evtMax = step_setting.get('evtMax',evtMax)
			s_evtMax = step_setting.get('evtMaxPerJob',s_evtMax)
			workflow[step]['actvar']['evtmax'] = s_evtMax
	
			#redirect output in step to ./ on WN
			if backend['name']=='dirac':
				workflow[step]['actvar']['dirac_output']='True'			

				

			# resolve input from previous steps
			input_map={'elecsim':'detsim','calib':'elecsim','rec':'calib','rec_woelec':'calib','calib_woelec':'detsim'}
			rand = randint(0,200000000)	#use rand to assure unique seed

			if splitterMode in ['splitByEvent']:
				if step in input_map:
					jobvarsToSeq.update({step+'_input_jobvar':input_map[step]})
				jobvarsToSeq.update({step+'_output_jobvar':step})
				jobvarsToSeq.update({step+'_user_output_jobvar':step+'_user'})
				for attribute in ['additional_args','positions','particles','momentums','material','volume']:
					if attribute in step_setting:
						workflow[step]['actvar'][step+'_'+attribute+'_jobvar']=step_setting.get(attribute)
				
				# seed
				seed = step_setting.get('seed',rand)
				jobvarsToSeq.update({step+'_seed_jobvar':seed})

			elif splitterMode in ['splitByJobvars']:
				jobvar_lists=splitter.get('jobvar_lists',{})
		
				# seed setting
				if 'seed' not in step_setting:
					splitter['jobvar_lists'][step+'_seed_jobvar']={'type':'range','param':{'first':rand,'step':1}}
				else:
					splitter['jobvar_lists'][step+'_seed_jobvar']={'type':'composite_string','param':{'value': step_setting.get('seed')}}

				# use seed for output/user-output names if not specified
				if 'output' not in step_setting:
					step_setting['output']='%s_$(%s_seed_jobvar)'%(step,step)
				if 'user_output' not in step_setting:
					step_setting['user_output']='%s_user_$(%s_seed_jobvar)'%(step,step)
				# get input from previous steps
				if (step in input_map) and (input_map[step] in previous_steps):	
					step_setting['input']=workflow_input.get(input_map[step])['output']
				

				# validate step setting;
				if step=='detsim':
					check_step(step,step_setting,['output','user_output'])
				elif step=='elecsim':
					check_step(step,step_setting,['input','output','user_output'])
				elif step=='calib':
					check_step(step,step_setting,['input','output','user_output'])
				elif step=='rec':
					check_step(step,step_setting,['input','output'])
				elif step=='calib_woelec':
					check_step(step,step_setting,['input','output'])
				elif step=='rec_woelec':
					check_step(step,step_setting,['input','output'])
				else:
					# step is none of the legit ones above
					raise JunoScenarioError('%s is not a legit job step.'%step)
		
				# if with jobvar splitter, translate some settings to composite_string jobvars
				for attribute in ['input','output','user_output','additional_args','positions','particles','momentums','volume','material']:
					if attribute in step_setting:
						splitter['jobvar_lists'][step+'_'+attribute+'_jobvar']={'type':'composite_string','param':{'value':step_setting.get(attribute)}}

			
			# other necessary args for certain steps
			if  step == 'elecsim':
				workflow[step]['actvar']['rate'] = step_setting.get('rate',1)
			if 'gdml-file' in step_setting:
				workflow[step]['actvar']['gdml-file'] = step_setting.get('gdml-file')


		if splitterMode in ['splitByEvent']:
			splitter['jobvars']=jobvars
			splitter['jobvarsToSeq']=jobvarsToSeq

	
		# Dirac backend
		if backend['name']=='dirac':
			dirac_setting=self.scenario_input.get('backend',{})
			taskName=self.scenario_input.get('taskName','')
			if not isinstance(dirac_setting,dict):
				dirac_setting={}
			# a dirac-upload action in the end, to upload everything:
			workflow['dirac_upload']={'type':'dirac_upload','actvar':{},'depend_on':job_steps}
			workflow['dirac_upload']['actvar']['overwrite']=dirac_setting.get('overwrite','True')
			workflow['dirac_upload']['actvar']['user_home']=dirac_setting.get('userHome','True')
			dirac_outputSubDir=dirac_setting.get('outputSubDir',outputSubDir)
			workflow['dirac_upload']['actvar']['destination_dir']=os.path.join(dirac_outputSubDir,taskName)
			workflow['dirac_upload']['actvar']['files_to_upload']=os.path.join('*root,*user*,*xml')
			#todo: a dirac-download action to get input




		#build scenario				
		self.scenario_param['input']=input_sandbox
		self.scenario_param['splitter']=splitter
		self.scenario_param['workflow']=workflow
		

		return self.scenario_param

			
