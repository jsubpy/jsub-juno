import os
import ast
from jsub.error import JsubError
from copy import copy,deepcopy
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
			junoTop = '/cvmfs/juno.ihep.ac.cn/centos7_amd64_gcc830/Pre-Release/J20v2r0-Pre1'
		else:
			softVersion = self.scenario_input.get('softVersion')
			junoTop_list = []
			if type(softVersion)==str:
				junoTop_list.extend(glob.glob('/%s/'%softVersion))
				junoTop_list.extend(glob.glob('/cvmfs/%s/'%softVersion))
				junoTop_list.extend(glob.glob('/cvmfs/juno.ihep.ac.cn/%s/'%softVersion))
				junoTop_list.extend(glob.glob('/cvmfs/juno.ihep.ac.cn/*/%s/'%softVersion))
				junoTop_list.extend(glob.glob('/cvmfs/juno.ihep.ac.cn/*/*/%s/'%softVersion))
			elif type(softVersion)==dict:
				arch=softVersion.get('arch','*')
				release=softVersion.get('release','*')
				JUNOpath=os.path.join('/cvmfs/juno.ihep.ac.cn/',arch,'*/',release)	
				junoTop_list.extend(glob.glob(JUNOpath))		

			if not junoTop_list:
				raise JunoScenarioError('No suitable environment on /cvmfs/ for JUNO version setting.')
			else:
				junoTop = junoTop_list[0]


		# build input sandbox
		yaml_input=self.scenario_input.get('input')
		input_sandbox={'common':{}}
		if type(yaml_input) is dict:
			input_sandbox['common'].update(yaml_input)

		# deal with splitter
		splitter=self.scenario_input.get('splitter')
		splitterMode=splitter.get('mode','splitByEvent')
		if splitterMode in ['splitByEvent','spliteByEvent','spliteByEvents','spliteByEvent']:
			splitterMode='splitByEvent'
			jobvarsToSeq={}
			jobvars={}
			index0=0
		elif splitterMode in ['splitByJobvars','splitByJobvar','spliteByJobvar','spliteByJobvars']:
			splitterMode='splitByJobvars'
			if 'jobvarLists' in splitter:
				splitter['jobvar_lists']=splitter['jobvarLists']
			jobvar_lists=splitter.get('jobvar_lists')
			if not jobvar_lists:
				raise JunoScenarioError('Jobvar lists not defined in the splitter.')
		else:
			raise JunoScenarioError('Invalid splitter mode: %s'%splitterMode)


		# general setting
		outputSubDir= self.scenario_input.get('outputSubDir','')
		outputDir= self.scenario_input.get('outputDir','')
		# users may define evtmax in splitter for their conveniences, or in general setting
		evtMax=splitter.get('evtMax',10)
		evtMax=splitter.get('evtMaxPerJob',evtMax)
		evtMax=self.scenario_input.get('evtMax',evtMax)
		evtMax=self.scenario_input.get('evtMaxPerJob',evtMax)


		# build workflow
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
	
		workflow={}
		previous_steps=[]
		input_map={'elecsim':'detsim','calib':'elecsim','rec':'calib','rec_woelec':'calib_woelec','calib_woelec':'detsim'}
		dirac_upload_dict={}	# {files_to_upload:dir, files_to_upload can be wildcard}
		alg_counter=0	# idx of jobvar in algs

		for step in job_steps:
#			step=step.lower()
			p_steps=copy(previous_steps)	#copy to avoid further modification on the same object
			previous_steps+=[step]

			# apply default settings:
			step_desc=workflow_input.get(step,{})
			if step in ['detsim','elecsim','calib','rec','calib_woelec','rec_woelec']:

				workflow[step]={'type':'juno_prod','actvar':{'step_type':step},'depend_on':p_steps}
				step_type = step


				
				#	1. soft version should come from general setting
				workflow[step]['actvar']['JUNO_top'] = junoTop
				#	2. evtmax should come from general setting; or overwritten by step setting
				s_evtMax = step_desc.get('evtMax',evtMax)
				s_evtMax = step_desc.get('evtMaxPerJob',s_evtMax)
				workflow[step]['actvar']['evtmax'] = s_evtMax
	
				#redirect output in step to ./ on WN
				if backend['name']=='dirac':
					workflow[step]['actvar']['dirac_output']='True'			

						
				# deal with different case conventions
				if 'userOutput' in step_desc:	
					step_desc['user_output']=step_desc['userOutput']
				if 'additionalArgs' in step_desc:	
					step_desc['additional_args']=step_desc['additionalArgs']
				if 'fullArgs' in step_desc:	
					step_desc['full_args']=step_desc['fullArgs']

				# resolve input from previous steps
				rand = randint(0,20000000)	#use rand to assure unique seed

				if splitterMode in ['splitByEvent']:
					# seed
					seed = step_desc.get('seed',rand)
					jobvarsToSeq.update({step+'_seed_jobvar':seed})
					if step in input_map:
						jobvarsToSeq.update({step+'_input_jobvar':input_map[step]})
					else:	# use the seed of first step, if detsim involved
						index0=seed
					jobvarsToSeq.update({step+'_output_jobvar':step})
					jobvarsToSeq.update({step+'_user_output_jobvar':step+'_user'})
					for attribute in ['additional_args','full_args','positions','particles','momentums','material','volume']:
						if attribute in step_desc:
							workflow[step]['actvar'][step+'_'+attribute+'_jobvar']=step_desc.get(attribute)
					dirac_upload_dict.update({'*'+step+'_*':'DIRACTOPDIR/'+step})

				elif splitterMode in ['splitByJobvars']:
					# seed setting
					if 'seed' not in step_desc:
						splitter['jobvar_lists'][step+'_seed_jobvar']={'type':'range','param':{'first':rand,'step':1}}
					else:
						splitter['jobvar_lists'][step+'_seed_jobvar']={'type':'composite_string','param':{'value': step_desc.get('seed')},'priority':0}


					

					splitter['jobvar_lists']['univ_index']={'type':'range','param':{'first':0}}

					# Input and Output ----------------------------------
					# get input from previous steps
					if (step in input_map) and (input_map[step] in previous_steps):	
						step_desc['input']=workflow_input.get(input_map[step])['output']

					output_name_from_input=False
					# zhangxm file name scheme: detsim-$(seed).root, detsim_user-$(seed).root ...
					if 'input' in step_desc:
						input_step=input_map[step]
						if input_step in step_desc['input']:	#keyword replacement if step name in filenames
							step_desc['output']=step_desc['input'].replace(input_step,step)
							step_desc['user_output']=step_desc['input'].replace(input_step,step+'_user')
						else:	# add suffixes to indicate step name
							step_desc['output']=step_desc['input']+'.'+step
							step_desc['user_output']=step_desc['input']+'.'+step+'_user'

						output_name_from_input=True

					# handling outputLFN/userOutputLFN
					LFN_count=0
					if 'outputLFN' in step_desc:
						LFN_count+=1
						splitter['jobvar_lists'][step+'_outputLFN_jobvar']={'type':'composite_string','param':{'value':step_desc.get('outputLFN')},'priority':0}
						dirac_upload_dict.update({step+'_outputLFN_jobvar':'COMPSTR'})	# comp str handled by DIRAC_UPLOAD module
						# should override output
						step_desc['output']=step_desc['outputLFN']
					else:
						dirac_upload_dict.update({'*'+step_desc['output']+'*':'DIRACTOPDIR/'+step})

					if 'userOutputLFN' in step_desc:
						LFN_count+=1
						splitter['jobvar_lists'][step+'_userOutputLFN_jobvar']={'type':'composite_string','param':{'value':step_desc.get('userOutputLFN')},'priority':0}
						dirac_upload_dict.update({step+'_userOutputLFN_jobvar':'COMPSTR'})	# comp str handled by DIRAC_UPLOAD module
						# should override user_output
						step_desc['user_output']=step_desc['userOutputLFN']
					else:
						dirac_upload_dict.update({'*'+step_desc['user_output']+'*':'DIRACTOPDIR/'+step})
					
					if LFN_count==0:
						dirac_upload_dict.update({'*'+step_type+'*':'DIRACTOPDIR/'+step})


					# use seed for output/user-output names if not specified
					if not output_name_from_input:
						index_jobvar='univ_index'
						if step+'_seed_jobvar' in splitter['jobvar_lists']:
							index_jobvar=step+'_seed_jobvar'
						if 'output' not in step_desc:
							step_desc['output']='%s-$(%s)'%(step,index_jobvar) 	# use seed instead of univ-index
						if 'user_output' not in step_desc:
							step_desc['user_output']='%s_user-$(%s)'%(step,index_jobvar)



					# validate step setting;
#					if step=='detsim':
#						check_step(step,step_desc,['output','user_output'])
#					elif step=='elecsim':
#						check_step(step,step_desc,['input','output','user_output'])
#					elif step=='calib':
#						check_step(step,step_desc,['input','output','user_output'])
#					elif step=='rec':
#						check_step(step,step_desc,['input','output','user_output'])
#					elif step=='calib_woelec':
#						check_step(step,step_desc,['input','output','user_output'])
#					elif step=='rec_woelec':
#						check_step(step,step_desc,['input','output','user_output'])
		
					# if with jobvar splitter, translate some settings to composite_string jobvars
					for attribute in ['input','output','user_output','additional_args','full_args','positions','particles','momentums','volume','material']:
						if attribute in step_desc:
							splitter['jobvar_lists'][step+'_'+attribute+'_jobvar']={'type':'composite_string','param':{'value':step_desc.get(attribute)},'priority':0}

				
				# other necessary args for certain steps
				if  step == 'elecsim':
					workflow[step]['actvar']['rate'] = step_desc.get('rate',1)
				if 'gdml-file' in step_desc:
					workflow[step]['actvar']['gdml-file'] = step_desc.get('gdml-file')


			else:	# step not in juno_prod
				step_type = step_desc.get('type','')
				if not step_type:
					raise JunoScenarioError('Type not specified for step %s in workflow'%(step))
				# running user script
				if step_type.lower() in ['userscript','script','user_script','exe','execute_script']:	#step type = run user script
					script_file = step_desc.get('file','')
					script_args = step_desc.get('argument','')
					script_args = step_desc.get('arguments',script_args)
					script_code = step_desc.get('code','')	

					if script_file:
						input_sandbox['common'].update({os.path.basename(script_file):os.path.abspath(script_file)})
						if splitterMode in ['splitByJobvars']:
							splitter['jobvar_lists'][step+'_argument_jobvar']={'type':'composite_string','param':{'value':script_args},'priority':0}
							workflow[step]={'type':'exe','actvar':{'exe':os.path.basename(script_file),'argument_jobvar':step+'_argument_jobvar','location':'common'},'depend_on':p_steps}
						else:
							workflow[step]={'type':'exe','actvar':{'exe':os.path.basename(script_file),'argument':script_args,'location':'common'},'depend_on':p_steps}
						
					elif script_code:
						if splitterMode in ['splitByJobvars']:
							splitter['jobvar_lists'][step+'_code_jobvar']={'type':'composite_string','param':{'value':script_args},'priority':0}
							workflow[step]={'type':'run_code','actvar':{'code_jobvar':step+'_code_jobvar'},'depend_on':p_steps}
						else:
							workflow[step]={'type':'run_code','actvar':{'code':script_code},'depend_on':p_steps}
					else:
						raise JunoScenarioError('Invalid setting for step %s: missing file or code for user script.'%(step))
			
				# juno_alg
				elif step_type.lower() in ['juno_alg','juno_algorithm','algorithm']:
					soFile=step_desc.get('soFile')
					jobConfig=step_desc.get('jobConfig')
					textReplace=step_desc.get('textReplace',{})
					outputUpload=step_desc.get('outputUpload',[])
					outputUpload=step_desc.get('uploadOutput',outputUpload)

					if not jobConfig:
						raise JunoScenarioError('Missing jobConfig in step %s.'%step)
					if type(textReplace) is not dict:
						raise JunoScenarioError('The value of textReplace should be a dict. (in step %s)'%step)
					if type(soFile) is str:
						soFile=[soFile]
					elif type(soFile) is not list:
						raise JunoScenarioError('The value of soFile should be a string or a list. (in step %s)'%step)
					if type(outputUpload) is str:
						outputUpload=[outputUpload]
					elif type(outputUpload) is not list:
						raise JunoScenarioError('The value of outputUpload should be a string or a list. (in step %s)'%step)
					
					for upload_item in outputUpload:
						dirac_upload_dict.update({upload_item:'DIRACTOPDIR/'+step})
					if splitterMode in ['splitByJobvars']:		# mapping rtext -> textr in alg action module
						for k,v in textReplace.items():
							splitter['jobvar_lists']['alg_rtext_'+str(alg_counter)]={'type':'composite_string','param':{'value':k},'priority':0}
							splitter['jobvar_lists']['alg_textr_'+str(alg_counter)]={'type':'composite_string','param':{'value':v},'priority':0}
							alg_counter+=1										

					for f in soFile:
						input_sandbox['common'].update({os.path.basename(f):os.path.abspath(f)})
					input_sandbox['common'].update({os.path.basename(jobConfig):os.path.abspath(jobConfig)})
					
					workflow[step]={'type':'juno_alg','actvar':{'soFile':','.join(soFile),'jobConfig':jobConfig},'depend_on':p_steps}
					workflow[step]['actvar']['JUNO_top'] = junoTop
					
					

				# juno software
				elif step_type.lower() in ['juno_soft','juno_software','junosoft','junosoftware','junoscript','juno_script']:
					software=step_desc.get('software')
					software_args=step_desc.get('argument')
					software_args=step_desc.get('arguments',software_args)
					software_args=step_desc.get('arg',software_args)
					software_args=step_desc.get('args',software_args)
					if not software:
						raise JunoScenarioError('Invalid setting for step %s: software not specified.'%(step))
					

					if splitterMode in ['splitByJobvars']:
						splitter['jobvar_lists'][step+'_argument_jobvar']={'type':'composite_string','param':{'value':software_args},'priority':0}
						workflow[step]={'type':'juno_soft','actvar':{'JUNO_top':junoTop,'software':software,'argument_jobvar':step+'_argument_jobvar'},'depend_on':p_steps}
					else:
						workflow[step]={'type':'juno_soft','actvar':{'JUNO_top':junoTop,'software':software,'argument':software_args},'depend_on':p_steps}
					
				# executing cmd
				elif step_type.lower() in ['cmd']:
					cmd=step_desc.get('cmd')
					workflow[step]={'type':'cmd','actvar':{'cmd':cmd},'depend_on':p_steps}
						
				elif step_type.lower() in ['dirac_upload']:
					workflow[step]={'type':'dirac_upload','actvar':step_desc,'depend_on':p_steps}

				else:	# invalid step type
					raise JunoScenarioError('Invalid step type (%s) for step %s in workflow'%(step_type,step))
				
			workflow_input[step]=deepcopy(step_desc)

		#ends iterating step


		if splitterMode in ['splitByEvent']:
			splitter['jobvars']=jobvars
			splitter['jobvarsToSeq']=jobvarsToSeq
			if 'index0' not in splitter:	# top priority if index0 specified by user
				splitter['index0']=index0

	
		# Condor backend
		if backend['name'] in ['IHEPCondor','Condor']:
			condor_setting = self.scenario_input.get('backend',{})
			taskName=self.scenario_input.get('taskName','')
			if not isinstance(condor_setting,dict):
				condor_setting={}

			data_folder=condor_setting.get('dataFolder','./')
			data_folder=condor_setting.get('outputDir',data_folder)
			
			# shall use full path for output
			for step in workflow:
				workflow[step]['actvar'].update({'data_folder':data_folder})

		# Dirac backend
		if backend['name']=='dirac':
			dirac_setting=self.scenario_input.get('backend',{})
			taskName=self.scenario_input.get('taskName','')
			if isinstance(dirac_setting, str):
				dirac_setting={'type':dirac_setting}
			elif not isinstance(dirac_setting,dict):
				dirac_setting={}

			do_upload=dirac_setting.get('upload','TRUE')
			if do_upload.upper()=='TRUE':
				# a dirac-upload action in the end, to upload everything:
				workflow['dirac_upload']={'type':'dirac_upload','actvar':{},'depend_on':job_steps}
				workflow['dirac_upload']['actvar']['overwrite']=dirac_setting.get('overwrite','True')
				workflow['dirac_upload']['actvar']['SE']=dirac_setting.get('SE')
	
				# outputDir for dir of full path; outputSubDir for subdir in user home.
				dirac_outputSubDir=dirac_setting.get('outputSubDir',outputSubDir)
				dirac_outputDir=dirac_setting.get('outputDir',outputDir)
				dirac_upload_dict.update({'*xml':'DIRACTOPDIR/'})
				dirac_topdir=''
				if dirac_outputDir:
	#				workflow['dirac_upload']['actvar']['user_home']='False'
	#				if splitterMode in ['splitByJobvars']:
	#					splitter['jobvar_lists']['dirac_upload_destination_dir_jobvar']={'type':'composite_string','param':{'value':dirac_outputDir},'priority':0}
	#				else:
	#					workflow['dirac_upload']['actvar']['destination_dir']=dirac_outputDir
					dirac_topdir=dirac_outputDir
				elif dirac_outputSubDir:
	#				workflow['dirac_upload']['actvar']['user_home']='True'
	#				if splitterMode in ['splitByJobvars']:
	#					splitter['jobvar_lists']['dirac_upload_destination_dir_jobvar']={'type':'composite_string','param':{'value':os.path.join(dirac_outputSubDir,taskName)},'priority':0}
	#				else:
	#					workflow['dirac_upload']['actvar']['destination_dir']=os.path.join(dirac_outputSubDir,taskName)
					dirac_topdir=os.path.join(dirac_outputSubDir,taskName)
				
				keys=dirac_upload_dict.keys()
				for key in keys:
					if 'DIRACTOPDIR' in dirac_upload_dict[key]:
						dirac_upload_dict[key]=dirac_upload_dict[key].replace('DIRACTOPDIR',dirac_topdir)
						
				workflow['dirac_upload']['actvar']['upload_dict']=dirac_upload_dict
			# finish uploading



			#when input is not from previous steps, use a dirac-download action to get input
			for step in job_steps:
				if (step in input_map) and (input_map[step] not in previous_steps):	
					# in this case, the input shall be the full LFN 
					workflow[step+'_download_input']={'type':'dirac_download','actvar':{},'depend_on':[]}
					workflow[step+'_download_input']['actvar']['input_lfn_jobvar_name']=step+'_input_jobvar'
					workflow[step]['actvar']['dirac_input']='True'
					workflow[step]['depend_on'].append(step+'_download_input')
			
			


		#build scenario				
		self.scenario_param['input']=input_sandbox
		self.scenario_param['splitter']=splitter
		self.scenario_param['workflow']=workflow
		

		return self.scenario_param

			
