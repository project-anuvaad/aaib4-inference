import requests
import os
import json as js
from anuvaad_auditor.loghandler import log_info, log_exception
from utilities import MODULE_CONTEXT
from local_files import local_envn_variable

dhurva_url = os.environ.get('DHURVA_URL')
	
def dhruva_api_call(src_list, source_language_code, target_language_code):

	access_token = os.environ.get('DHRUVA_ACCESS_TOKEN')
	if source_language_code == "en":
		serviceid = os.environ.get('AAI4B_SERVICE_ID_EN_IN', 'ai4bharat/indictrans-fairseq-all-gpu--t4')
	elif target_language_code == "en":
		serviceid = os.environ.get('AAI4B_SERVICE_ID_IN_EN', 'ai4bharat/indictrans-fairseq-all-gpu--t4')
	elif source_language_code != "en" and target_language_code != "en":
		serviceid = os.environ.get('AAI4B_SERVICE_ID_IN_IN', 'ai4bharat/indictrans-fairseq-all-gpu--t4')
	else:
		serviceid = "ai4bharat/indictrans-fairseq-all-gpu--t4"
	data_json = {
    		"pipelineTasks": [
        		{
            			"taskType": "translation",
            			"config": {
                		"language": {
                			"serviceId": serviceid,
                    			"sourceLanguage": source_language_code,
                    			"targetLanguage": target_language_code
                		}
            			}
        		}
    		],
    		"inputData": {
        		"input": []
		}
	}
	for src in src_list:
		local_text = {"source": src}
		data_json["inputData"]["input"].append(local_text)
	
	headers={'Content-Type':'application/json', 
		'Authorization': access_token}	
	response = requests.post(dhurva_url, headers=headers, json=data_json)
	log_info("Dhruva has been called with content, request-url: {0}, body: {1}, auth_token: {2}, serviceId: {3}".format(dhurva_url, data_json, access_token, serviceid), MODULE_CONTEXT)
	log_info("Dhruva returned content {0}-{1} |".format(response.status_code, response.text), MODULE_CONTEXT)
	return response


def dhruva_api_request(src_list, source_language_code, target_language_code):
	response = dhruva_api_call(src_list, source_language_code, target_language_code)
	out = []
	response.status_code = 502
	if response.status_code == 200:
		log_info("Dhruva API Request has beed called, successful | {}".format(response.status_code), MODULE_CONTEXT)
		response_dict = js.loads(response.text)
		print(response_dict["pipelineResponse"][0]["output"])
		for transl in response_dict["pipelineResponse"][0]["output"]:
			out.append(transl["target"])		
	else:
		log_info("Dhruva API Request has beed called, Not success {0}-{1} |".format(response.status_code, response.text), MODULE_CONTEXT)
		for i in range(len(src_list)):
			out.append("THERE ARE SOME ISSUES WITH TRANSLATION.")
	return out
	

