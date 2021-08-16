# IndicTrans Inference  (aai4b-nmt-inference)
Inference pipeline to deploy IndicTrans nmt models on top of the Flask server.
This service currently suports 11 indic languages:

| <!-- -->  | <!-- --> | <!-- --> | <!-- --> |
| ------------- | ------------- | ------------- | ------------- |
| Assamese (as)  | Hindi (hi) | Marathi (mr) | Tamil (ta)|
| Bengali (bn) | Kannada (kn)| Oriya (or) | Telugu (te)|
| Gujarati (gu) | Malayalam (ml) | Punjabi (pa) |

## Prerequisites
- python 3.6 +
- ubuntu 16.04 +

Install various python libraries as mentioned in requirements.txt file

```bash
pip install -r src/requirements.txt
```

## APIs and Documentation
Run app.py to start the service with all the packages installed

```bash
python src/app.py
```
# Training Repository
https://github.com/AI4Bharat/indicTrans
# License
The indictrans inference service code (and models) are released under the MIT License.
