# Think-on-Graph 2.0: Deep and Faithful Large Language Model Reasoning with Knowledge-guided Retrieval Augmented Generation (ToG-2)
## Paper
https://arxiv.org/abs/2407.10805

## Project Structure
- `requirements.txt`: Pip environment file.
- `data/`: Evaluation datasets.
- `eval/`: Evaluation script. See `eval/README.md` for details.
- `Wikidata/`: Wikidata environment setting. See `Wikidata/README.md` for details.
- `ToG-2/`: Source codes.
  - `client.py`: Pre-defined Wikidata APIs, copy from `Wikidata/`.
  - `server_urls.txt`: Wikidata server urls, copy from `Wikidata/`.
  - `main_tog2.py`: Same as above but using Wikidata as KG source. See `README.md` for details.
  - `prompt_list.py`: The prompts lib.
  - `wiki_func.py`: The functions including wiki-related functions.
  - `utils.py`: The functions used in `main_tog2.py`.
  - `search.py`: The functions including retrieval-related functions.
  - `ner.py`: The tools for ner using Azure API.

## Get started
Before running ToG-2, please ensure that you have successfully installed **Wikidata** on your local machine and correctly save your Wikidata server urls in `ToG-2/server_urls.txt`. The comprehensive installation instructions and necessary configuration details can be found in the `README.md` file located within the respective folder.

The required libraries can be found in `requirements.txt`.


## How to run
### Upon successfully installing all the necessary configurations, you can proceed to execute ToG directly by employing the following command:

```sh
python main_tog2.py \  
--dataset <dataset_name> \  # dataset your wanna test. "hotpot_e" for HotpotQA, "fever", "qald", "creak", "webqsp", "zeroshotre".
--max_length 256 \  # max length for generation.
--temperature_exploration 0 \  # the temperature in exploration stage, our default setting is 0.
--temperature_reasoning 0 \  # the temperature in reasoning stage, our default setting is 0.
--width 3 \  # choose the search width, 3 is the default setting.
--depth 3 \  # choose the search depth, 3 is the default setting.
--remove_unnecessary_rel True \  # whether removing unnecessary relations.
--LLM_type_rp gpt-3.5-turbo \  # the LLM you choose for RP
--LLM_type gpt-3.5-turbo \  # the LLM you choose for other generations.
--opeani_api_keys <api_key> \  # your own api key, if LLM_type is local LLMs, this parameter would be rendered ineffective.
--embedding_model_name <search_model_name> \  # model name for text search. "bge-bi" (bge embedding), "bge-ce" (bge reranker),"bm25","minilm" (ms-marco-MiniLM-L-6-v2) and "colbert" (bge-m3).
--relation_prune_combination True\  # whether perform relation_prune_combination. 
--num_sents_for_reasoning 10 \  # number of sentences retained for reasoning. 10 is the default setting.
--topic_prune True \  # whether perform topic prune.
--self_consistency_threshold 0.8 \  # self-consistency threshold, 0.8 is the default setting.
--clue_query True \  # whether use clue query.
```
### Example: Our experimental script for HotpotQA.
```
cd ToG-2
python main_tog2.py \
--dataset hotpot_e
--max_length 256 \  
--temperature_exploration 0 \ 
--temperature_reasoning 0 \  
--width 3 \ 
--depth 3 \  
--remove_unnecessary_rel True 
--LLM_type_rp gpt-3.5-turbo \
--LLM_type gpt-3.5-turbo \ 
--opeani_api_keys <api_key> \  # your own api key, if LLM_type is local LLMs, this parameter would be rendered ineffective.
--embedding_model_name bge-bi \ 
--relation_prune_combination True\  
--num_sents_for_reasoning 10 \  
--topic_prune True \ 
--self_consistency_threshold 0.8 \  
--clue_query True\  
```

The output file will be saved by `search.save_2_jsonl_simplier`. See `search.py` for details of the name format of output files.

## How to eval
Using the script in the `eval` folder.

We use **Exact Match** as our evaluation metric.

After getting the final result file, use the following command to evaluate the results:

```sh
python eval.py \  # 
--dataset <dataset_name> \ # dataset your wanna test. "hotpot_e" for HotpotQA, "fever", "qald", "creak", "webqsp", "zeroshotre".
--output_file <output_file_name> \  # the output file from main_tog2.py, which should be .json.
--data_question_string <question_string> \  # key to access the question in the output file.
```

### Example: Our experimental script for HotpotQA.
```
cd eval
python eval.py \
--dataset hotpot_e
--output_file <output_file_name> \ 
--data_question_string question
```

## Other issues:
Regarding ToG-FinQA, we must note that this dataset was constructed using data provided by a third-party data provider. Since we have not yet granted permission to share the data, we are currently unable to provide access to ToG-FinQA outside our research team.

## Citation
If you are interested or inspired by this work, you can cite us by:
```
@misc{ma2024thinkongraph20deepfaithful,
      title={Think-on-Graph 2.0: Deep and Faithful Large Language Model Reasoning with Knowledge-guided Retrieval Augmented Generation}, 
      author={Shengjie Ma and Chengjin Xu and Xuhui Jiang and Muzhi Li and Huaren Qu and Cehao Yang and Jiaxin Mao and Jian Guo},
      year={2024},
      eprint={2407.10805},
      archivePrefix={arXiv},
      primaryClass={cs.CL},
      url={https://arxiv.org/abs/2407.10805}, 
}
```

## Claim
This project uses the Apache 2.0 protocol. The project assumes no legal responsibility for any of the model's output and will not be held liable for any damages that may result from the use of the resources and output.
