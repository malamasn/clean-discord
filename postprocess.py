import os
import json
import re
import io
import argparse
from tqdm import tqdm
import concurrent.futures
from itertools import repeat
from src.validatefiles import check_files
from src.workers import worker_regex, worker_detox, worker_antispam, write_stats

def str2bool(v):
    if isinstance(v, bool): return v
    if v.lower() in ('yes', 'true', 't', 'y', '1'): return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'): return False
    else: raise argparse.ArgumentTypeError('Boolean value expected.')

parser = argparse.ArgumentParser(description='Postprocess cleaned Discord data')
parser.add_argument('-dir', type=str, default="output",
                    help='the data folder containing the cleaned .jsons')
parser.add_argument('-out', type=str, default="discord_data.json",
                    help='the json file to output all postprocessed data')
parser.add_argument("-overwrite", type=str2bool, nargs='?', const=True, default=False, 
                    help="overwrite existing files")

args = parser.parse_args()

# Function to replace '\n' with another string value
def replace_newlines(item, value = '\n'):
    if isinstance(item, str):
        return item.replace('\\n', value)
    elif isinstance(item, list):
        return [replace_newlines(elem) for elem in item]
    elif isinstance(item, dict):
        return {key: replace_newlines(value) for key, value in item.items()}
    else:
        return item


if __name__ == '__main__':
    tasks=os.listdir(args.dir)
    discord_data = []
    for task in tasks:
        data = json.load(io.open(os.path.join(args.dir,task), encoding="utf-8"))
        conversations = []
        for d in data["conversations"]:
            conversations.append([i[0] for i in d])
        
        for i in range(len(conversations)):
            conversation = conversations[i]
            raw_conversation = '\n'.join(conversation)
            raw_conversation = replace_newlines(raw_conversation)
            
            authors_pattern = [author+': ' for author in data["authors"][i]]
            pattern = r'\b(?:' + '|'.join(map(re.escape, authors_pattern)) + r')\b'
            clean_conversation = re.sub(pattern, '', raw_conversation)
            
            authors = data["authors"][i]
            channel_name = data["channel_name"]
            timestamp_first = data["timestamps"][i][0]
            timestamp_last = data["timestamps"][i][1]
            discord_data.append({
                "raw_conversation": raw_conversation,
                "conversation": clean_conversation,
                "authors": authors,
                "channel": channel_name,
                "timestamp_first": timestamp_first,
                "timestamp_last": timestamp_last
            })
        
    with open(os.path.join(args.dir,args.out), "w") as json_file:
        json.dump(discord_data, json_file)
