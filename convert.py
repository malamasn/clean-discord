import io
import os
import re
import time
import json
import argparse
from tqdm import tqdm
from src.helpers import *
from datetime import datetime

parser = argparse.ArgumentParser(description='Clean Discord data')
parser.add_argument('-dir', type=str, default="data",
                    help='the data folder containing discord .jsons')
parser.add_argument('-out', type=str, default="./",
                    help='the folder to output the cleaned files')
parser.add_argument('-conversation_timeout', type=int, default=1800,
                    help='amount of time before a conversation is considered dead (in minutes) default is 30 min')


parser.add_argument("-nontoxic", type=str2bool, nargs='?', const=True, default=False,
                    help="use an AI to clean text files")
parser.add_argument("-batches", type=int, default=100,
                    help="minimum number of batches to feed the AI (only needed if -nontoxic is used)")
parser.add_argument("-confidence", type=float, default=0.85,
                    help="AI must be > 0.85 sure that the message is toxic to remove it")
args = parser.parse_args()



os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

all_messages={}
with tqdm(os.listdir(args.dir), desc="Reading files") as pbar:
    for file in pbar:
        all_messages[file]=json.load(io.open(os.path.join(args.dir,file), mode="r", encoding="utf-8"))["messages"]
        pbar.set_description(f"Found {sum([len(all_messages[msgs]) for msgs in all_messages])} messages")
   
disposed=0 
completed=0
len_all_messages=sum([len(all_messages[msgs]) for msgs in all_messages])
with tqdm(total=sum(len_all_messages, desc="Processing messages") as pbar, io.open(os.path.join(args.out,"context.txt"), mode="w", encoding="utf-8") as f:
    last_id="0"
    for file in all_messages:
        if re.findall(r"\[\d{18,}\]",file)[0] != last_id:
            last_known_name=""
            last_known_time=0
            build=""
            last_id=re.findall(r"\[\d{18,}\]",file)[0]
        for curr_message in all_messages[file]:
            msg=clean(curr_message["content"])
            if msg != None:
                if curr_message["author"]["name"] != last_known_name:
                    last_known_name=curr_message["author"]["name"]
                    build+=f"\t{clean(last_known_name,author=curr_message['author']['id'])}: {msg}"
                else:
                    build+="\\n"+msg
            else:disposed+=1
            try: today=time.mktime(datetime.strptime(curr_message["timestamp"].split(".")[0].replace("+00:00",""), "%Y-%m-%dT%H:%M:%S").timetuple())
            except: print(curr_message["timestamp"])
            if today-last_known_time > args.conversation_timeout and last_known_time != 0:
                if build.startswith("\t"): build=build[1:]
                if build.startswith("\\n"): build=build[2:]
                if build.count("\t") > 1 and build != "":
                    f.write(build.replace("\n","")+"\n")
                    completed+=1
                build=""
                last_known_name=""
            last_known_time=today
                
            title=file.split(" - ")
            try:
                part=re.findall(r"\[part (\d)\]",file)[0]
            except:
                part=0
            pbar.set_description(f'{title[0]} - {title[1]} - Part {part}, Conversations: {completed} Removed: {disposed}')
            pbar.update(1)

disposed_tox=0
if nontoxic:
    from tox_block.prediction import make_predictions as detect       
    to_clean=io.open(os.path.join(args.out,"context.txt"), mode="r", encoding="utf-8").read().strip().split("\n")
    with io.open(os.path.join(args.out,"context-detox.txt"), mode="w", encoding="utf-8") as f:
        with tqdm(to_clean, desc="Processing messages") as pbar:
            for conversation in pbar:
                sents=conversation.strip().split("\t")
                pbar.set_description(f"Batch of {len(sents)}, Removed {disposed_tox}")
                prediction_vals=detect(sents)
                print(sents[0])
                print(prediction_vals[0])
                scores=[max(list(dict(prediction_vals[detection]).values())[1:]) for detection in prediction_vals]
                to_write=[]
                for i,v in enumerate(scores):
                    if v <= args.toxic: to_write.append(sents[i])
                    else: disposed_tox+=1
                to_write="\t".join(to_write)
                f.write(to_write+"\n")

print(f"Removed {disposed}+{disposed_tox}/{len_all_messages}, {round((disposed+disposed_tox)/len_all_messages,2)}%")
print(f"Dataset final size: {len_all_messages - disposed - disposed_tox} messages, reduced from {sizeof_fmt(sum([os.path.getsize(f'{os.path.join(args.dir,fle)}') >> 20 for fle in os.listdir(args.dir)]))} to {sizeof_fmt(os.path.getsize('context-detox.txt') >> 20)}")