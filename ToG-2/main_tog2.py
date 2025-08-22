import argparse
import statistics
from pathlib import Path
from client import *
from utils import *
from search import *
import urllib3
from dotenv import load_dotenv
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import torch
from wiki_func import *

load_dotenv("/home/sheldor/Documents/TOG-Miraj/ToG-2/.env")
openai_api_key = os.getenv("OPEN_API_KEY")
print(f"OpenAI API Key: {openai_api_key}")

parser = argparse.ArgumentParser()

parser.add_argument("--dataset", type=str,
                    default="hotpot_e", help="choose the dataset.")
parser.add_argument("--samples", type=int,
                    default=2000, help="choose the number of samples.")
parser.add_argument("--start", type=int,
                    default=0, help="choose the start number of samples.")
parser.add_argument("--max_length", type=int, help="the max length of LLMs output.")
parser.add_argument("--temperature_exploration", type=float,
                    default=0, help="the temperature in exploration stage.")
parser.add_argument("--temperature_reasoning", type=float,
                    default=0, help="the temperature in reasoning stage.")
parser.add_argument("--width", type=int,
                    default=3, help="choose the search width of ToG.")
parser.add_argument("--depth", type=int,
                    default=3, help="choose the search depth of ToG.")
parser.add_argument("--remove_unnecessary_rel", type=bool,
                    default=True, help="whether removing unnecessary relations.")
parser.add_argument("--LLM_type", type=str,
                    default='gpt-4o-mini', choices=['gpt-3.5-turbo', 'llama','gpt-4o'], help="base LLM model.")
parser.add_argument("--LLM_type_rp", type=str,
                    default="gpt-4o-mini", choices=["gpt-3.5-turbo-16k",'gpt-4o'],help="base LLM model.")
parser.add_argument("--opeani_api_keys", type=str,
                    default=openai_api_key,
                    help="if the LLM_type is gpt-3.5-turbo or gpt-4, you need add your own openai api keys.")
parser.add_argument("--addr_list", type=str,
                    default="server_urls.txt", help="The address of the Wikidata service.")
parser.add_argument("--embedding_model_name", type=str, default="bge-bi")
parser.add_argument("--relation_prune", type=bool, default=True, help="whether to prune the relation")
parser.add_argument("--relation_prune_combination", type=bool, default=True,
                    help="whether to combine the relation prune")
parser.add_argument("--num_sents_for_reasoning", type=int, default=10)
parser.add_argument("--topic_prune", type=bool, default=True)
parser.add_argument("--gpt_only", type=bool, default=False)
parser.add_argument("--self_consistency", type=bool, default=False)
parser.add_argument("--self_consistency_threshold", type=float, default=0.8)
parser.add_argument("--clue_query", type=bool, default=True)
def sliding_window_type(s):
    try:
        window_size, step_size = map(int, s.split(','))
        return window_size, step_size
    except:
        raise argparse.ArgumentTypeError("Sliding window must be two integers separated by a comma, e.g., 3,2")

parser.add_argument(
    'sliding_window',
    type=sliding_window_type,
    help='Specify sliding window size and step size as two integers separated by a comma, e.g., 3,2',
    nargs='?',
    default=(1, 1)
)

args = parser.parse_args()
parser.add_argument("--output", type=str, default='{}_self_consistency'.format(args.dataset))
args = parser.parse_args()
start = args.start
datas, question_string = prepare_dataset(args.dataset)

os.environ["CUDA_VISIBLE_DEVICES"] = "0"
print(f"Available GPU IDs: {os.environ['CUDA_VISIBLE_DEVICES']}")

if args.embedding_model_name == "bge-bi":
    from FlagEmbedding import FlagModel
    print('loading rank model bge embedding model...')
    emb_model = FlagModel('BAAI/bge-large-en-v1.5', use_fp16=False)
elif args.embedding_model_name == "minilm":
    from sentence_transformers import CrossEncoder
    print('loading rank model minilm...')
    emb_model = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2', max_length=512)
elif args.embedding_model_name == "bm25":
    print('loading rank model bm25...')
    emb_model = compute_bm25_similarity
elif args.embedding_model_name == 'bge-ce':
    from FlagEmbedding import FlagReranker
    print("loading rank model bge reranker...")
    emb_model = FlagReranker('BAAI/bge-reranker-large', use_fp16=False)
elif args.embedding_model_name == 'colbert':
    from FlagEmbedding import BGEM3FlagModel
    print("loading rank model Colbert...")
    emb_model = BGEM3FlagModel('BAAI/bge-m3', use_fp16=True)

samples_length = args.samples

print("Start Running ToG on %s dataset." % args.dataset)

print('Dataset length: ' + str(len(datas)))

print('Test samples length: ' + str(samples_length))

# wiki_client
with open(args.addr_list, "r") as f:
    server_addrs = f.readlines()
    server_addrs = [addr.strip() for addr in server_addrs]
wiki_client = MultiServerWikidataQueryClient(server_addrs)
wiki_client.test_connections()



def main_wiki_new(original_question, topic_entity, ground_truth, data_point):
    clue = ''
    question = original_question
    print('\n')
    print('Question   ' + question)
    print('topic_entity   ' + str(','.join(topic_entity)))
    print('\n')
    cluster_chain_of_entities = []
    search_entity_list = []
    Total_Related_Senteces = []

    if args.self_consistency:
        if data_point["cot_sc_score"] >= args.self_consistency_threshold:
            return data_point["cot_sc_response"], search_entity_list, [], [], 'gpt self-consistency', ''

    if len(topic_entity) == 0 or args.gpt_only:
        answer = generate_only_with_gpt(question, args)
        endmode = 'generate_without_explored_paths'
        remark = 'no_topic_entity'
        print(remark)
        return answer, search_entity_list, [], [], endmode, remark

    if args.topic_prune and len(topic_entity) > 2:

        print('--------------- topic entity prune ---------------')
        topic_entity = topic_e_prune(question, topic_entity, args)
        print('--------------- topic entity after prune ---------------')
        print(topic_entity)

        if len(topic_entity) == 0:
            answer = generate_only_with_gpt(question, args)
            endmode = 'generate_without_explored_paths.'
            remark = 'no_topic_entity_tp'
            print(remark)
            return answer, search_entity_list, [], [], endmode, remark
    else:
        print("No topic prune.")

    print('---------------collecting topic_entity docs---------------')
    for entity_id in topic_entity:
        if entity_id != "[FINISH_ID]":
            entity_name = topic_entity[entity_id]
            related_passage = get_wikipedia_page(wiki_client, {'name': entity_name, 'id': entity_id})
            paragraph, sorted_sentences = pages_embedding_search(question, related_passage, args,
                                                                 emb_model, top_k=3)
            Total_Related_Senteces.extend(sorted_sentences)


    if args.depth == 0:
        references = ''
        if len(Total_Related_Senteces) > 0:
            references += "# References \n"
            for idx, s in enumerate(Total_Related_Senteces[:args.num_sents_for_reasoning]):
                references += s["text"].strip() + '\n'
        if 'fever' in args.dataset or 'creak' in args.dataset:
            check_prompt = '### Claim:' + question
            if "fever" in args.dataset:
                system_prompt = prompt_reasoning_fever_3shot_2
            else:
                system_prompt = prompt_reasoning_creak_3shot
        else:
            check_prompt = '### Question:' + question
            system_prompt = vanilla_prompt_reasoning_qa_2shot
        final_prompt = system_prompt + '\n' + check_prompt + '\n' + references + '\n'
        answer = run_llm(final_prompt, 0, 512, args.opeani_api_keys)
        return answer, [], [], [], '', ''

    pre_relations = [''] * len(topic_entity)
    pre_heads = [-1] * len(topic_entity)

    for depth in range(1, args.depth + 1):
        print('\n-----------------------depth: ' + str(depth) + '-----------------------')
        current_entity_relations_list = []
        all_entity_relations = {}

        for index, entity_id in enumerate(topic_entity):
            if entity_id != "[FINISH_ID]":
                if args.relation_prune:
                    print("in the prune relation mode.")
                    if args.relation_prune_combination:
                        print("in the prune relation combination mode.")
                        retrieve_relations = relation_search(entity_id, topic_entity[entity_id], pre_relations[index],
                                                             pre_heads[index], question, args, wiki_client)
                        all_entity_relations[topic_entity[entity_id]] = retrieve_relations
                    else:
                        retrieve_relations_with_scores = relation_search_prune(entity_id, topic_entity[entity_id],
                                                                               pre_relations[index], pre_heads[index],
                                                                               question, args,
                                                                               wiki_client)
                        for relation in retrieve_relations_with_scores:
                            relation['entity_id'] = entity_id
                            relation['entity_name'] = topic_entity[entity_id]
                        current_entity_relations_list.extend(retrieve_relations_with_scores)
                else:
                    retrieve_relations = relation_search(entity_id, topic_entity[entity_id], pre_relations[index],
                                                         pre_heads[index], question, args, wiki_client)

                    print(len(retrieve_relations))
                    current_entity_relations_list.extend(retrieve_relations)

        if args.relation_prune_combination and args.relation_prune:
            current_entity_relations_list.extend(
                relation_prune_all(all_entity_relations, question, args))

        print(
            '\n---------------Find relation for: {}.---------------'.format(
                ','.join(topic_entity)))
        print('---------------total ' + str(len(current_entity_relations_list)) + ' rels')
        print(current_entity_relations_list)
        print('\n')

        if depth == 1 and len(current_entity_relations_list) == 0:
            answer = generate_only_with_gpt(question, args)
            remark = 'WiKi Error: cant find relation of first topic_entity. Depth 1 '
            print(remark, ": ", question)
            end_mode = 'generate_only_with_gpt'

            return answer, search_entity_list, Total_Related_Senteces, [], end_mode, remark

        Indepth_total_candidates = []
        each_relation_right_entityList = []
        for relation in current_entity_relations_list:
            # this is the problematic part, this is returning some garbage ig? check it again throuhly
            print('\n-------------------------------Searching ' + str(relation['entity_name']) + 'relation:  ' + str(
                relation['relation']))
            if relation['head']:
                print("head is true")
                entity_candidates = entity_search(relation['entity_id'], relation['relation'], wiki_client, True)
            else:
                print("head is false")
                entity_candidates = entity_search(relation['entity_id'], relation['relation'], wiki_client, False)
            if len(entity_candidates) == 0:
                print("No entity candidates found for relation:", relation['relation'])
                continue

            print('\n---------------Collected entity_candidates---------------')
            print(entity_candidates)

            entity_candidates = [candidate for candidate in entity_candidates if len(candidate['name']) > 2]
            print('\n---------------Collecting entity_candidates docs---------------')
            for candidate in entity_candidates:
                if candidate['id'] != '[FINISH_ID]':
                    related_passage = get_wikipedia_page(wiki_client, candidate)
                    paragraphs = pages_embedding_search_only_para(related_passage)
                    candidate['related_paragraphs'] = paragraphs
                else:
                    candidate['related_paragraphs'] = []

            entity_candidates = [candidate for candidate in entity_candidates if
                                 bool(candidate.get('related_paragraphs'))]
            Indepth_total_candidates = update_history_find_entity(entity_candidates, relation, Indepth_total_candidates)
            each_relation_right_entityList.append({'current_relation': relation, 'right_entity': entity_candidates})

        search_entity_list.append({'depth': depth, 'current_entity_relations_list': current_entity_relations_list,
                                   'each_relation_right_entityList': each_relation_right_entityList})

        if len(Indepth_total_candidates) == 0:
            if depth:
                answer = generate_only_with_gpt(question, args)
                remark = 'no entity find in depth{}'.format(depth)
                end_mode = 'generate_only_with_gpt'
                print(remark)
                return answer, search_entity_list, Total_Related_Senteces, [], end_mode, remark

        flag, chain_of_entities, entities_id, pre_relations, pre_heads, sorted_entity_list, Indepth_total_candidates = para_rank_topk(
            question, Indepth_total_candidates, args, emb_model)

        cluster_chain_of_entities.append(chain_of_entities)

        if flag:
            for entity in sorted_entity_list:
                s = entity['sentences']
                Total_Related_Senteces.extend(s)
            Total_Related_Senteces = list({sentence['text']: sentence for sentence in Total_Related_Senteces}.values())
            sents = [s['text'] for s in Total_Related_Senteces]
            scores = s2p_relevance_scores(sents, question, args, emb_model)
            Total_Related_Senteces = scores_rank(scores, sents)
            stop, answer, kg_prompt = reasoning(original_question, Indepth_total_candidates, Total_Related_Senteces,
                                                cluster_chain_of_entities, args, clue)
            if stop:
                print("\n-----------------------Find answer. ToG stoped at depth %d." % depth)
                end_mode = 'reasoning stop'
                remark = "Find answer. ToG stoped at depth %d." % depth

                return answer, search_entity_list, Total_Related_Senteces, cluster_chain_of_entities, end_mode, remark
            else:
                print("\n-----------------------depth %d still not find the answer." % depth)
                flag_finish, entities_id = if_finish_list(entities_id)

                if flag_finish:
                    answer = generate_only_with_gpt(question, args)
                    remark = "After entity_find_prune, all entities_id == [FINISH_ID]. No new knowledge added during search depth %d, stop searching." % depth

                    end_mode = 'generate_only_with_gpt'
                    print(remark)
                    return answer, search_entity_list, Total_Related_Senteces, [], end_mode, remark
                else:
                    topic_entity = {qid: topic for qid, topic in zip(entities_id,
                                                                     [wiki_client.query_all("qid2label", entity).pop()
                                                                      for entity in entities_id])}
                    continue
        else:
            remark = 'Last situation topic entity rank list in empty in depth {}, generate_only_with llm.'.format(depth)
            end_mode = 'generate_only_with_gpt'
            print(remark)
            if 'fever' in args.dataset:
                answer = 'The answer is {NOT ENOUGH INFO}.'
            else:
                answer = generate_only_with_gpt(question, args)
            return answer, search_entity_list, Total_Related_Senteces, [], end_mode, remark

    answer = generate_only_with_gpt(question, args)
    remark = 'Last situation. Not into depth. whether it trigger'
    end_mode = 'generate_only_with_gpt'
    print(remark)
    return answer, search_entity_list, Total_Related_Senteces, [], end_mode, remark

length = min(samples_length, len(datas))


cnt = 0

for i in range(start, length):
    print("Running sample: ", i, " / ", length)
    # if i == 0:
    #     continue
    data = datas[i]
    query = data[question_string]
    if args.self_consistency:
        data_point = self_consistency(query, data, i, args)
    else:
        data_point = []
    if 'qid_topic_entity' in data:
        topic_entity = data['qid_topic_entity']
    else:
        topic_entity = data['entities']
    if 'answer' in data:
        ground_truth = data["answer"]
    elif 'answers' in data:
        ground_truth = data["answers"]
    elif 'fever' in args.dataset:
        ground_truth = data['label']
    else:
        ground_truth = ''

    answer, search_entity_list, Total_Related_Senteces, cluster_chain_of_entities, end_mode, remark = main_wiki_new(
        query, topic_entity, ground_truth, data_point)

    save_2_jsonl_simplier(query, ground_truth, answer, search_entity_list, Total_Related_Senteces,
                          cluster_chain_of_entities, args.dataset, end_mode, remark, args)
    print("temporarily ending sample: ", i, " / ", length)
    cnt += 1
    if cnt == 1:
        print("Temporarily ending after 1 samples.")
        break
