import requests
import os
import json as js
from anuvaad_auditor.loghandler import log_info, log_exception
from utilities import MODULE_CONTEXT

dhurva_url = os.environ.get('DHURVA_URL')
	
def dhruva_api_call(src_list, source_language_code, target_language_code):

	access_token = os.environ.get('DHRUVA_ACCESS_TOKEN')
	
	data_json = {
    		"pipelineTasks": [
        		{
            			"taskType": "translation",
            			"config": {
                		"language": {
                    			"serviceId": "ai4bharat/indictrans-fairseq-all-gpu--t4",
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
	return response


def dhruva_api_request(src_list, source_language_code, target_language_code):
	response = dhruva_api_call(src_list, source_language_code, target_language_code)
	out = []
	if response.status_code == 200:
		log_info("Dhruva API Request has beed called, successful | {}".format(response.status_code), MODULE_CONTEXT)
		response_dict = js.loads(response.text)
		print(response_dict["pipelineResponse"][0]["output"])
		for transl in response_dict["pipelineResponse"][0]["output"]:
			out.append(transl["target"])		
	else:
		log_info("Dhruva API Request has beed called, Not success {0}-{1} | {}".format(response.status_code, response.text), MODULE_CONTEXT)
	return out
	

