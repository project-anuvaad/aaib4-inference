# IndicTrans Inference (aai4b-nmt-inference)

## Anuvaad-AI4Bharat API for Machine Translation
Inference pipeline to deploy IndicTrans NMT models on top of Flask server.

## Prerequisites
- Python 3.6 +
- Ubuntu 16.04 +

Install various python libraries as mentioned in `requirements.txt` file

```bash
pip install -r src/requirements.txt
```

## APIs and Documentation

- Put all the models in `src/nmt_models` folder as per the specs in `config/fetch_models.json`
- Run `app.py` to start the service with all the packages installed

```bash
python src/app.py
```

## Languages

### v1

IndicTrans-v1 suports 11 major Indic languages:

| <!-- -->  | <!-- --> | <!-- --> | <!-- --> |
| ------------- | ------------- | ------------- | ------------- |
| Assamese (as)  | Hindi (hi) | Marathi (mr) | Tamil (ta)|
| Bangla (bn) | Kannada (kn)| Oriya (or) | Telugu (te)|
| Gujarati (gu) | Malayalam (ml) | Panjabi (pa) |

### v2

IndicTrans-v2 supports all [22 scheduled langauges of India](https://en.wikipedia.org/wiki/Eighth_Schedule_to_the_Constitution_of_India), which includes English, 20 Indic languages (4 [Dravidian](https://en.wikipedia.org/wiki/Dravidian_languages), 15 [Indo-Aryan](https://en.wikipedia.org/wiki/Indo-Aryan_languages), 1 [Munda](https://en.wikipedia.org/wiki/Munda_languages)) and 2 [Tibeto-Burman languages](https://en.wikipedia.org/wiki/Tibeto-Burman_languages) (Bodo & Manipuri).

|ISO 639 code | Language |
|---|--------------------|
|as |Assamese - অসমীয়া   |
|bn |Bangla - বাংলা       |
|brx|Boro - बड़ो	      |
|doi|Dogri - डोगरी |
|gom|Goan-Konkani - कोंकणी|
|gu |Gujarati - ગુજરાતી   |
|hi |Hindi - हिंदी         |
|kn |Kannada - ಕನ್ನಡ     |
|ks |Kashmiri - كٲشُر 	  |
|ks_Deva|Kashmiri - कॉशुर |
|gom|Konkani Goan - कोंकणी|
|mai|Maithili - मैथिली     |
|ml |Malayalam - മലയാളം|
|mni|Manipuri - ꯃꯤꯇꯩꯂꯣꯟ	 |
|mni_Beng|Manipuri - মিতৈলোন |
|mr |Marathi - मराठी       |
|ne |Nepali - नेपाली 	    |
|or |Oriya - ଓଡ଼ିଆ         |
|pa |Panjabi - ਪੰਜਾਬੀ      |
|sa |Sanskrit - संस्कृतम् 	 |
|sat |Santali - ᱥᱟᱱᱛᱟᱲᱤ |
|sd |Sindhi - سنڌي       |
|sd_Deva|Sindhi - सिंधी |
|ta |Tamil - தமிழ்       |
|te |Telugu - తెలుగు      |
|ur |Urdu - اُردُو         |

## Training Repository
https://github.com/AI4Bharat/indicTrans

## License
The indictrans inference service code (and models) are released under the MIT License.
