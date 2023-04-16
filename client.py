import requests

ROOT_URL = "http://localhost:5001"

# # v1 - English to Indic
# response = requests.post(
#     f"{ROOT_URL}/aai4b-nmt-inference/v1/translate",
#     json={
#         "model_id": 104,
#         "src_list": [
#             {"src": "Hello world"},
#             {"src": "Goodbye, I am done with the world."},
#         ],
#         "source_language_code": "en",
#         "target_language_code": "ta",
#     }
# )
# print(response.json())

# # v1 - Indic to Indic
# response = requests.post(
#     f"{ROOT_URL}/aai4b-nmt-inference/v1.1/translate",
#     json={
#         "model_id": 144,
#         "src_list": [
#             {"src": "सलाम दुनिया"},
#             {"src": "अलविदा, मैं इस दुनिया से हो चुका हूं।"},
#         ],
#         "source_language_code": "hi",
#         "target_language_code": "ta",
#     }
# )
# print(response.json())

# # v2 - English to Indic
# response = requests.post(
#     f"{ROOT_URL}/aai4b-nmt-inference/v2/translate",
#     json={
#         "src_list": [
#             {"src": "Hello world"},
#             {"src": "Goodbye, I am done with the world."},
#         ],
#         "source_language_code": "en",
#         "target_language_code": "ks",
#     }
# )
# print(response.json())

# # v2 Constrained - English to Indic
# response = requests.post(
#     f"{ROOT_URL}/aai4b-nmt-inference/v2/interactive-translation",
#     json=[
#         {
#             "source_language_code": "en",
#             "target_language_code": "hi",
#             "src": "Hello world",
#             "target_prefix": "सलाम"
#         }
#     ]
# )
# print(response.json())

# # v1 - Indic to English
# response = requests.post(
#     f"{ROOT_URL}/aai4b-nmt-inference/v2/translate",
#     json={
#         "src_list": [
#             {"src": "सलाम दुनिया"},
#             {"src": "अलविदा, मैं इस दुनिया से हो चुका हूं।"},
#         ],
#         "source_language_code": "hi",
#         "target_language_code": "en",
#     }
# )
# print(response.json())

# # v1 - Indic to Indic
# response = requests.post(
#     f"{ROOT_URL}/aai4b-nmt-inference/v2/translate",
#     json={
#         "src_list": [
#             {"src": "सलाम दुनिया"},
#             {"src": "अलविदा, मैं इस दुनिया से हो चुका हूं।"},
#         ],
#         "source_language_code": "hi",
#         "target_language_code": "mni_Beng",
#     }
# )
# print(response.json())
