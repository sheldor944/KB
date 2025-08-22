import json
import time
import openai
import re
import os
from prompt_list import *
from rank_bm25 import BM25Okapi
from sentence_transformers import util
from openai import OpenAI

def retrieve_top_docs(query, docs, model, width=3):
    query_emb = model.encode(query)
    doc_emb = model.encode(docs)

    scores = util.dot_score(query_emb, doc_emb)[0].cpu().tolist()

    doc_score_pairs = sorted(list(zip(docs, scores)), key=lambda x: x[1], reverse=True)

    top_docs = [pair[0] for pair in doc_score_pairs[:width]]
    top_scores = [pair[1] for pair in doc_score_pairs[:width]]

    return top_docs, top_scores


def compute_bm25_similarity(query, corpus):

    tokenized_corpus = [doc.split(" ") for doc in corpus]
    bm25 = BM25Okapi(tokenized_corpus)
    tokenized_query = query.split(" ")

    doc_scores = bm25.get_scores(tokenized_query)

    return doc_scores


def if_all_zero(topn_scores):
    return all(score == 0 for score in topn_scores)


def clean_relations_bm25_sent(topn_relations, topn_scores, entity_id, head_relations):
    relations = []
    if if_all_zero(topn_scores):
        topn_scores = [float(1/len(topn_scores))] * len(topn_scores)
    i=0
    for relation in topn_relations:
        if relation in head_relations:
            relations.append({"entity": entity_id, "relation": relation, "score": topn_scores[i], "head": True})
        else:
            relations.append({"entity": entity_id, "relation": relation, "score": topn_scores[i], "head": False})
        i+=1
    return True, relations


def run_llm(prompt, temperature, max_tokens, opeani_api_keys, engine="gpt-3.5-turbo", n=1):

    if "llama" in engine.lower():
        openai_api_key = "EMPTY"
        openai_api_base = "http://localhost:7788/v1"

        client = OpenAI(
            api_key=openai_api_key,
            base_url=openai_api_base,
        )

        models = client.models.list()
        engine = models.data[0].id
        print(engine)
    else:
        # client = openai.OpenAI(api_key=opeani_api_keys, base_url="<your_api_url>")
        client = openai.OpenAI(api_key=opeani_api_keys)
        print(f"created a OpenAI client with api key: {opeani_api_keys} and engine: {engine}")



    sys_prompt = '''You are a helpful assistant'''
    messages = [{"role":"system","content":sys_prompt}]
    message_prompt = {"role":"user","content":prompt}
    messages.append(message_prompt)

    f = 4
    while(f > 0):
        if f == 2:
            engine = "gpt-3.5-turbo-16k"    # In case of too long input
        try:    
                print(f"Calling for getting the response")
                response = client.chat.completions.create(
                        model=engine,
                        messages = messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        frequency_penalty=0,
                        presence_penalty=0,
                        n=n)
           
                # print(f"Got the response")
                # print(f"Response: {response}")
                if n > 1:
                    return response
                else:
                    result = response.choices[0].message.content
                f = -1
                return result
        except Exception as e:
            print(e)
            time.sleep(10)
            f -= 1
    return ''

def run_llm_cnfin(prompt, temperature, max_tokens, opeani_api_keys, engine="gpt-3.5-turbo", n=1):

    if "llama" in engine.lower():
        openai_api_key = "EMPTY"
        openai_api_base = "http://localhost:7788/v1"

        client = OpenAI(
            api_key=openai_api_key,
            base_url=openai_api_base,
        )

        models = client.models.list()
        engine = models.data[0].id
        print(engine)
    else:
        client = openai.OpenAI(api_key=opeani_api_keys, base_url="https://api.gptsapi.net/v1")

    sys_prompt = '''你是一个专业的中文金融助手，被设计用于以JSON形式回答问题.'''
    messages = [{"role":"system","content":sys_prompt}]
    message_prompt = {"role":"user","content":prompt}
    messages.append(message_prompt)

    f = 4
    while(f > 0):
        if f == 2:
            engine = "gpt-3.5-turbo-16k"
        try:
                response = client.chat.completions.create(
                        model=engine,
                        messages = messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        frequency_penalty=0,
                        presence_penalty=0,
                        n=n)
                if n > 1:
                    return response
                else:
                    result = response.choices[0].message.content
                f = -1
                return result
        except Exception as e:
            print(e)
            time.sleep(10)
            f -= 1
    return ''

def all_unknown_entity(entity_candidates):
    return all(candidate == "UnName_Entity" for candidate in entity_candidates)


def del_unknown_entity(entity_candidates):
    if len(entity_candidates)==1 and entity_candidates[0]=="UnName_Entity":
        return entity_candidates
    entity_candidates = [candidate for candidate in entity_candidates if candidate != "UnName_Entity"]
    return entity_candidates


def clean_scores(string, entity_candidates):
    scores = re.findall(r'\d+\.\d+', string)
    scores = [float(number) for number in scores]
    if len(scores) == len(entity_candidates):
        return scores
    else:
        print("All entities are created equal.")
        return [1/len(entity_candidates)] * len(entity_candidates)
    

def save_2_jsonl(question,ground_truth, answer, time_cost, search_entity_list,total_related_senteces,  cluster_chain_of_entities, file_name,end_mode,remark):

    sorted_sentences = sorted(total_related_senteces, key=lambda x: x['score'], reverse=True)

    data_dict = {"question":question,'ground_truth':ground_truth,'results':answer,'time_cost':time_cost,'end_mode':end_mode,'remark':remark,'top_5_sentences':sorted_sentences[0:5],"search_entity_list":search_entity_list,"cluster_chain_of_entities":cluster_chain_of_entities}
    filename="ToG_{}.json".format(file_name)

    if os.path.exists(filename):

        with open(filename, "r") as f:
            content = f.read()
            if content.endswith("]"):
                content = content.strip().rstrip("]")
                content += "," + json.dumps(data_dict, indent=4) + "]"
            else:
                content = "["+json.dumps(data_dict, indent=4) + "]"
    else:
        content = "["+json.dumps(data_dict, indent=4) + "]"

    with open(filename, "w") as f:
        f.write(content)

    
def extract_answer(text):
    start_index = text.find("{")
    end_index = text.find("}")
    if start_index != -1 and end_index != -1:
        return text[start_index+1:end_index].strip()
    else:
        return ""
    

def if_true(prompt):
    if prompt.lower().strip().replace(" ","")=="yes":
        return True
    return False

def generate_without_explored_paths(question, args):
    prompt = cot_prompt + "\n\nQ: " + question + "\nA:"
    response = run_llm(prompt, args.temperature_reasoning, args.max_length, args.opeani_api_keys, args.LLM_type)
    return response


def generate_only_with_sentences(question,Total_Related_Senteces, args):

    sorted_sentences = sorted(Total_Related_Senteces, key=lambda x: x['score'], reverse=True)
    texts = [sentence['text'] for sentence in sorted_sentences[0:5]]
    related_sentences_prompt = '\n'.join(texts)    

    prompt = only_with_sentences_prompt + "\n\nQ: " + question +'\nRelated Information: \n' + related_sentences_prompt+"\nA:"

    response = run_llm(prompt, args.temperature_reasoning, args.max_length, args.opeani_api_keys, args.LLM_type)
    return response

def query_reformulate_clue(original_question, answer,args):
    curly_braces_pattern = re.compile(r'\{\{(.*?)\}\}')

    curly_braces_matches = curly_braces_pattern.findall(answer)
    if len(curly_braces_matches) == 0 or len(curly_braces_matches[0]) > 2:
        print("The output does not contain enough curly brace enclosed contents(0):", answer)
        return original_question
    elif len(curly_braces_matches) == 1 and (curly_braces_matches[0].lower() in ["no", "yes"]):
        print("The output does not contain enough curly brace enclosed contents(1):", answer)
        return original_question
    else:
        prompt = prompt_rq.format(original_question, answer)
        response = run_llm(prompt, 0, 20, args.opeani_api_keys, args.LLM_type)
        match = re.search(r'\{(.*?)\}', response)
        return match.group(1) if match else original_question
        
def query_reformulate_add(original_question, answer):
    curly_braces_pattern = re.compile(r'\{\{(.*?)\}\}')

    curly_braces_matches = curly_braces_pattern.findall(answer)
    if len(curly_braces_matches) == 0 or len(curly_braces_matches[0]) > 2:
        print("The output does not contain enough curly brace enclosed contents(0):", answer)
        return original_question
    elif len(curly_braces_matches) == 1 and (curly_braces_matches[0].lower() in ["no", "yes"]):
        print("The output does not contain enough curly brace enclosed contents(1):", answer)
        return original_question
    else:
        return original_question + curly_braces_matches[-1]

def dynamic_requery_fin(answer):
   if "深度搜索" in answer:
       return "深度搜索"
   else:
       return "广度搜弱"

def generate_only_with_gpt(question, args):
    if 'fever' in args.dataset:
        prompt = fever_s1_prompt_demonstration_6_shot + question + "\nAnswer:"
    elif "creak" in args.dataset:
        prompt = vanilla_prompt_fact_check_3shot + question + "\nAnswer:"
    else:
        prompt = cot_prompt + question + "\nAnswer:"

    response = run_llm(prompt, args.temperature_reasoning, args.max_length, args.opeani_api_keys, args.LLM_type)
    return response

def self_consistency(question, data, idx, args):
    def get_s1_prompt(question, args):
        if 'fever' not in args.dataset:
            return hotpotqa_s1_prompt_demonstration + "Q: " + question.strip() + "\nA: "
        else:
            return fever_s1_prompt_demonstration + "Q: " + question.strip() + "\nA: "

    def get_cot_sc_results(data_point, cot_prompt, args, k = 10):
        print(f"Calling the run_llm function from got_cot_sc_results with prompt: ....")
        cot_sc_responses = run_llm(cot_prompt, 0.7, args.max_length, args.opeani_api_keys, args.LLM_type, n=10)
        print("got a response just not printing for now ")
        if cot_sc_responses is not None:
            all_cot_text_response = [choice.message.content.strip() for choice in cot_sc_responses.choices]
            all_cot_results = []

            for x in all_cot_text_response:
                if "The answer is" in x:
                    all_cot_results.append(x.split("The answer is")[1].strip().lower())
                else:
                    None

            all_cot_results = all_cot_results[:k]
            if len(all_cot_results) > 0:
                most_common_answer = max(set(all_cot_results), key=all_cot_results.count)
                most_common_answer_indices = [i for i, x in enumerate(all_cot_results) if x == most_common_answer]
                sc_score = float(len(most_common_answer_indices)) / k
                cot_answer = all_cot_results[0]
                cot_sc_text_response = all_cot_text_response[most_common_answer_indices[0]]
                cot_sc_answer = most_common_answer
            else:
                cot_sc_answer = ""
                cot_sc_text_response = 'No answer found'
                sc_score = 0

        else:
            raise Exception("Stage 1: OpenAI API call failed")

        data_point["cot_sc_score"] = sc_score
        data_point["cot_sc_response"] = cot_sc_text_response
        data_point["cot_sc_answer"] = cot_sc_answer
        return data_point

    def s1_reasoning_preparation(question, data_point,args):
        print("****************** Start stage 1: reasoning preparation ...")
        print("****** Question:", question)

        cot_prompt = get_s1_prompt(question, args)
      

        data_point = get_cot_sc_results(data_point, cot_prompt, args)

        print("****** CoT SC score:", data_point["cot_sc_score"])


        return data_point

    data_point = data
    data_point["id"] = idx
    if 'cot_sc_score' not in data_point:
        data_point = s1_reasoning_preparation(question, data_point,args)

        with open(args.output, "w") as f:
            json.dump(data_point, f)
    return data_point



def if_finish_list(lst):
    if all(elem == "[FINISH_ID]" for elem in lst):
        return True, []
    else:
        new_lst = [elem for elem in lst if elem != "[FINISH_ID]"]
        return False, new_lst


def prepare_dataset(dataset_name):

    if dataset_name == 'cwq':
        with open('../data/cwq.json',encoding='utf-8') as f:
            datas = json.load(f)
        question_string = 'question'
    elif dataset_name == 'hotpot_e':
        with open('../data/hotpotadv_entities_azure.json',encoding='utf-8') as f:
            datas = json.load(f)
        question_string = 'question'
    elif dataset_name == 'fever':
        with open('../data/fever_1000_entities_azure.json', encoding='utf-8') as f:
            datas = json.load(f)
        question_string = 'claim'
    elif dataset_name == 'webqsp':
        with open('../data/webqsp_test.json', encoding='utf-8') as f:
            datas = json.load(f)
        question_string = 'question'
    elif dataset_name == 'grailqa':
        with open('../data/grailqa.json',encoding='utf-8') as f:
            datas = json.load(f)
        question_string = 'question'
    elif dataset_name == 'simpleqa':
        with open('../data/SimpleQA.json',encoding='utf-8') as f:
            datas = json.load(f)    
        question_string = 'question'
    elif dataset_name == 'qald':
        with open('../data/qald_10-en.json',encoding='utf-8') as f:
            datas = json.load(f) 
        question_string = 'question'   
    elif dataset_name == 'webquestions':
        with open('../data/WebQuestions.json',encoding='utf-8') as f:
            datas = json.load(f)
        question_string = 'question'
    elif dataset_name == 'trex':
        with open('../data/T-REX.json',encoding='utf-8') as f:
            datas = json.load(f)
        question_string = 'input'    
    elif dataset_name == 'zeroshotre':
        with open('../data/Zero_Shot_RE.json',encoding='utf-8') as f:
            datas = json.load(f)
        question_string = 'input'    
    elif dataset_name == 'creak':
        with open('../data/creak.json',encoding='utf-8') as f:
            datas = json.load(f)
        question_string = 'sentence'
    elif dataset_name == 'finkg_qa':
        with open('../data/finkg_qa.json', encoding='utf-8') as f:
            datas = json.load(f)
        question_string = 'question'
    else:
        print("Dataset not found.")
        exit(-1)
    return datas, question_string

