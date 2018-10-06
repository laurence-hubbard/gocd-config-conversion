import argparse
from xmljson import badgerfish as bf
from lxml import etree
from xml.etree.ElementTree import fromstring
import json
import xml.etree.ElementTree as ET
import subprocess
parser = etree.XMLParser(recover=True)

parser = argparse.ArgumentParser(description='gocd-config-conversion')
parser.add_argument('--xml-config',
                        metavar='xml_config',
                        help='xml config',
                        required=True)
args = parser.parse_args()

XML_FILE=args.xml_config
config = bf.data(ET.parse(XML_FILE).getroot())

subprocess.call("./init.sh", shell=True)

# Useful for debugging
#with open('config.json', 'w') as outfile:
#    json.dump(config, outfile)

# Defining environments
for env in config['cruise']['environments']['environment']:
    env_name = env['@name']
    list_of_pipelines = []
    for pipeline in config['cruise']['environments']['environment'][0]['pipelines']['pipeline']:
        list_of_pipelines.append(pipeline['@name'])
    env_vars = []
    for variable in config['cruise']['environments']['environment'][0]['environmentvariables']['variable']:
        var_name = variable['@name']
        var_value = variable['value'].get('$')
        kv_pair = {'name': var_name, 'value': var_value}
        env_vars.append(kv_pair)
    env_json = {'format_version': 1, 'name': env_name, 'environment_variables': env_vars, 'pipelines': list_of_pipelines}
    file_name = 'target/environments/' + env_name + '.goenvironment.json'
    with open(file_name, 'w') as outfile:
        json.dump(env_json, outfile)

# Defining pipelines
# TODO: Split groups by directory
# TODO: Double check encrypted variables are handled as expected during conversion
# TODO: Add support for mingle and tracking_tool at pipeline level
# TODO: Add support for timer only_on_changes boolean at pipeline level
# TODO: Add support for destination on git materials
# TODO: Add support for additional material types (only have git and dependency so far)
# TODO: Add support for run_instance_count, environment_variables, timeout, elastic_profile_id, tabs and properties at job level

for index,group_of_pipelines in enumerate(config['cruise']['pipelines']):
    group = group_of_pipelines['@group']
    list_of_pipelines = group_of_pipelines.get('pipeline', [])
    if not isinstance(list_of_pipelines,list):
        list_of_pipelines = [list_of_pipelines]
    for pipeline in list_of_pipelines:
        pipeline_json = {}
        pipeline_name = pipeline['@name']
        pipeline_json['format_version'] = 1
        pipeline_json['group'] = group
        pipeline_json['name'] = pipeline_name
 
        # Handling pipeline parameters
        parameters=[]
        if 'params' in pipeline:
            list_of_parameters = pipeline['params']['param']
            if not isinstance(list_of_parameters,list):
                list_of_parameters=[list_of_parameters]
            for parameter in list_of_parameters:
                param_name = parameter['@name']
                param_value = parameter.get('$','')
                kv_pair = {'name': param_name, 'value': param_value}
                parameters.append(kv_pair)
        pipeline_json['parameters'] = parameters
        
        # Handling pipeline environment variables
        env_vars=[]
        if 'environmentvariables' in pipeline:
            list_of_variables = pipeline['environmentvariables']['variable']
            if not isinstance(list_of_variables,list):
                list_of_variables=[list_of_variables]
            for variable in list_of_variables:
                var_name = variable['@name']
                if variable.get('@secure',False):
                    var_value = variable['encryptedValue'].get('$','')
                    kv_pair = {'name': var_name, 'secure': True, 'encryptedValue': var_value}
                else:
                    var_value = variable['value'].get('$','')
                    kv_pair = {'name': var_name, 'value': var_value}
                env_vars.append(kv_pair)
        pipeline_json['environment_variables'] = env_vars

        templated = False
        if '@template' in pipeline:
            pipeline_json['template'] = pipeline['@template']
            templated = True

        if '@labeltemplate' in pipeline:
            pipeline_json['label_template'] = pipeline['@labeltemplate']
        else:
            pipeline_json['label_template'] = '${COUNT}' #GoCD default value

        pipeline_json['enable_pipeline_locking'] = pipeline.get('@isLocked',True)
        
        if 'timer' in pipeline:
            pipeline_json['timer'] = { 'spec': pipeline['timer'].get('$','') }

        # Handling pipeline materials
        list_of_materials = []
        ## Handling git materials
        if 'git' in pipeline['materials']:
            list_of_git_materials = pipeline['materials']['git']
            if not isinstance(list_of_git_materials,list):
                list_of_git_materials=[list_of_git_materials]
            for git_material in list_of_git_materials:
                git_material_json = {'type': 'git'}
                if '@materialName' in git_material:
                    git_material_json['name'] = git_material['@materialName']
                if '@dest' in git_material:
                    git_material_json['destination'] = git_material['@dest']
                git_material_json['url'] = git_material['@url']
                if 'filter' in git_material:
                    git_material_json['invertFilter'] = git_material.get('@invertFilter',False)
                    list_of_filter_patterns = []
                    list_of_filters = git_material['filter']['ignore']
                    if not isinstance(list_of_filters,list):
                        list_of_filters = [list_of_filters]
                    for filter_ in list_of_filters:
                        list_of_filter_patterns.append(filter_['@pattern'])
                    git_material_json['filter'] = {'ignore': list_of_filter_patterns }
                if '@branch' in git_material:
                    git_material_json['branch'] = git_material['@branch']
                if '@shallowClone' in git_material:
                    git_material_json['shallowClone'] = git_material['@shallowClone']
                list_of_materials.append(git_material_json)
        ## Handling dependency materials
        if 'pipeline' in pipeline['materials']:
            list_of_pipeline_materials = pipeline['materials']['pipeline']
            if not isinstance(list_of_pipeline_materials,list):
                list_of_pipeline_materials=[list_of_pipeline_materials]
            for pipeline_material in list_of_pipeline_materials:
                pipeline_material_json = {'type': 'dependency'}
                if '@materialName' in pipeline_material:
                    pipeline_material_json['name'] = pipeline_material['@materialName']
                if '@dest' in pipeline_material:
                    pipeline_material_json['destination'] = pipeline_material['@dest']
                pipeline_material_json['pipeline'] = pipeline_material['@pipelineName']
                pipeline_material_json['stage'] = pipeline_material['@stageName']
                list_of_materials.append(pipeline_material_json)
        pipeline_json['materials'] = list_of_materials

        # Handling pipeline stages, jobs and tasks
        if not templated:
            list_of_json_stages = []
            list_of_stages = pipeline['stage']
            if not isinstance(list_of_stages,list):
                list_of_stages = [list_of_stages]
            for stage in list_of_stages:
                stage_json = { 'name': stage['@name'] }
                stage_json['cleanWorkingDir'] = stage.get('@cleanWorkingDir', False)
                stage_json['artifactCleanupProhibited'] = stage.get('@artifactCleanupProhibited', False)
                if 'approval' in stage:
                    stage_json['approval'] = {'type': stage['approval']['@type']}
                list_of_json_jobs = []
                list_of_jobs = stage['jobs']['job']
                if not isinstance(list_of_jobs,list):
                    list_of_jobs=[list_of_jobs]
                for job in list_of_jobs:
                    job_json = { 'name': job['@name'] }
                    
                    list_of_json_resources = []
                    list_of_resources = job.get('resources',{}).get('resource',[])
                    if not isinstance(list_of_resources,list):
                        list_of_resources=[list_of_resources]
                    for resource in list_of_resources:
                        list_of_json_resources.append(resource['$'])
                    job_json['resources'] = list_of_json_resources
                    
                    list_of_json_artifacts = []
                    list_of_build_artifacts = job.get('artifacts',{}).get('artifact',[])
                    if not isinstance(list_of_build_artifacts,list):
                        list_of_build_artifacts=[list_of_build_artifacts]
                    for build_artifact in list_of_build_artifacts:
                        artifact_json = {'type': 'build'}
                        if '@src' in build_artifact:
                            artifact_json['source'] = build_artifact['@src']
                        if '@dest' in build_artifact:
                            artifact_json['destination'] = build_artifact['@dest']
                        list_of_json_artifacts.append(artifact_json)        
                    list_of_test_artifacts = job.get('artifacts',{}).get('test',[])
                    if not isinstance(list_of_test_artifacts,list):
                        list_of_test_artifacts=[list_of_test_artifacts]
                    for test_artifact in list_of_test_artifacts:
                        artifact_json = {'type': 'test'}
                        if '@src' in test_artifact:
                            artifact_json['source'] = test_artifact['@src']
                        if '@dest' in test_artifact:
                            artifact_json['destination'] = test_artifact['@dest']
                        list_of_json_artifacts.append(artifact_json)
                    job_json['artifacts'] = list_of_json_artifacts

                    list_of_json_tasks = []
                    if 'tasks' in job:
                        list_of_tasks = job['tasks'].get('task',job['tasks'])
                        if not isinstance(list_of_tasks,list):
                            list_of_tasks=[list_of_tasks]
                        for task in list_of_tasks:
                            if 'pluginConfiguration' in task:
                                task_json = { 'type': 'plugin' }
                                if 'runif' in task:
                                    task_json['runif'] = task['runif']['@status']
                                task_json['plugin_configuration'] = { 'id': task['pluginConfiguration']['@id'],
                                                                     'version': str(task['pluginConfiguration']['@version'])}
                                list_of_json_configurations = []
                                list_of_configurations = task['configuration']['property']
                                if not isinstance(list_of_configurations,list):
                                    list_of_configurations=[list_of_configurations]
                                for configuration in list_of_configurations:
                                    configuration_json = { 'key': configuration['key'].get('$',None),
                                                         'value': configuration['value'].get('$',None)}
                                    
                                    list_of_json_configurations.append(configuration_json)
                                task_json['configuration'] = list_of_json_configurations
                                
                            elif 'exec' in task:
                                task_json = { 'type': 'exec', 'command': task['exec']['@command'] }
                                if 'runif' in task['exec']:
                                    task_json['runif'] = task['exec']['runif']['@status']
                                
                            list_of_json_tasks.append(task_json)
                        list_of_fetches = job['tasks'].get('fetchartifact',[])
                        if not isinstance(list_of_fetches,list):
                            list_of_fetches=[list_of_fetches]
                        for fetch in list_of_fetches:
                            task_json = { 'type': 'fetch', 'artifact_origin': 'gocd' }
                            if 'runif' in fetch:
                                task_json['runif'] = fetch['runif']['@status']
                            task_json['pipeline'] = fetch['@pipeline']
                            task_json['stage'] = fetch['@stage']
                            task_json['job'] = fetch['@job']
                            if '@dest' in fetch:
                                task_json['destination'] = fetch['@dest']
                            if '@srcfile' in fetch:
                                task_json['source'] = fetch['@srcfile']
                                task_json['is_source_a_file'] = True
                            else:
                                task_json['source'] = fetch['@srcdir']
                                task_json['is_source_a_file'] = False

                            list_of_json_tasks.append(task_json)
                    
                    job_json['tasks'] = list_of_json_tasks
                    
                    list_of_json_jobs.append(job_json)

                stage_json['jobs'] = list_of_json_jobs
                list_of_json_stages.append(stage_json)
            
            pipeline_json['stages'] = list_of_json_stages

        file_name = 'target/pipelines/' + pipeline_name + '.gopipeline.json'
        with open(file_name, 'w') as outfile:
            json.dump(pipeline_json, outfile)
