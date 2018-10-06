# gocd-config-conversion
_______________________
This tool is for converting a single GoCD config XML file into a set of JSON objects so that you can start using "configuration as code" within GoCD without having to re-write every pipeline. More information on GoCD's configuration as code can be found [here](https://docs.gocd.org/current/advanced_usage/pipelines_as_code.html).

Currently only XML --> JSON is supported.

Note that there are limitation with this conversion tool:
* This is not a full migration tool. If you are using this to migrate, you will still need to manually remove the environments and pipelines defined in XML and manually configure other aspects of your new GoCD system, including templates, agents and server settings.
* There is no concept of templates in "configuration as code" plugins (as of [28th June 2018](https://gitter.im/gocd/configrepo-plugins)). This tool will extract pipelines that reference templates, but not the templates or the stages defined by the template itself, although the latter could be a possible addition to this tool in the future.
* Conversion to YAML not yet available.

Work left to do in the JSON conversion tool:
* Split pipeline groups by directory
* Double check encrypted variables are handled as expected during conversion
* Add support for mingle and tracking_tool at pipeline level
* Add support for timer only_on_changes boolean at pipeline level
* Add support for destination on git materials
* Add support for additional material types (only have git and dependency so far)
* Add support for run_instance_count, environment_variables, timeout, elastic_profile_id, tabs and properties at job level

### Extracting the GoCD XML file
This conversion tool relies on the GoCD XML file being locally available. It is not recommended to apply the tool against the live XML location, but instead to make a copy of it.
It is generally found at `/etc/­go/cr­uise-­confi­g.xml` on the instance that your `go-server` service is running on.

### How To Convert
**To run the conversion:**
```shell
$ python convert-to-json.py --xml-config <your_xml_file>
```
**Where are my JSON files?**
The JSON files can found in the resulting `target` directory, with environment and pipeline definitions split by directory and then file name:
```shell
$ find target -type f
target/environments/my_first_environment.goenvironment.json
target/environments/my_second_environment.goenvironment.json
target/pipelines/my_first_pipeline.gopipeline.json
target/pipelines/my_second_pipeline.gopipeline.json
```

### Requirements
Python requirements are detailed in `requirements.txt` and are:
* xmljson
* lxml
* xml
* json
* subprocess
* argparse

### Authors
_______________________
* [Laurence Hubbard](https://www.linkedin.com/in/laurence-hubbard/)
