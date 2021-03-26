# Clean-Discord
clean-discord is a fast, efficient, and robust script for cleaning large quantities of messages from discord data generated by [DiscordChatExporter](https://github.com/Tyrrrz/DiscordChatExporter). Its average processing rate is ~300k messages per 50 seconds (including detoxifying) while only consuming about 1gb of memory.

## Usage
#### **With DiscordChatExporter:**
This script uses data from [DiscordChatExporter](https://github.com/Tyrrrz/DiscordChatExporter) with a few important alterations (details in their [wiki](https://github.com/Tyrrrz/DiscordChatExporter/wiki/GUI%2C-CLI-and-Formats-explained#export-)):
- Timestamp format is in `yyyy-mm-dd`
- (Recommended but optional) splitting the files into partitions of N messages.

You can alter and copy this command for ease of use with the CLI version:
```
dotnet DiscordChatExporter.Cli.dll export \
  -t [token] \
  -f json -p 300000 \
  --dateformat yyy-mm-dd \
  -o [output dir] \
  -c [channel id to export]
```
#### **With custom data:**
You may use custom data, formatted properly, to use this script. Your input json files should be formatted as follows:
```
{
  "messages": [
    {
      "id": "12345678910111213",
      "type": "Default",
      "timestamp": "YYYY-MM-DDTHH:MM:SS+00:00",
      "content": "this where the text goes",
      "author": {
        "id": "31211101987654321",
        "name": "Jake",
        "isBot": false,
      },
    },
  ]
}
```
### Benchmarking the script
Regex, parsing, and classification performance can vary from device to device. See the [README in src](./src/README.md) tested on a 3.0ghz CPU (the test is single-threaded).

If you would like to run the benchmark, you run the following command from the base directory:
```
python3 src/workers.py
```
### Cleaning files
All cleaning functionality of this repo can be accessed with [clean.py](./clean.py).

My super large [discord dataset](https://www.kaggle.com/jef1056/discord-data) with over *300 million messages* was cleaned using the command on a 4-core machine with 4gb of memory, in approximately 6 hours.
```
python3 clean.py -detox -workers 8 -dir ../data -out ../cleaned
```

### Creating a compressed dataset and splits
Using the dataset as-is is completely feasible, but it is recommended to create proper splits and also generate all possible turns in a conversation.
Take this conversation for example:
```
Hi    How are you?    Im doing well    This is a conversation?    Yes.    Huh    Its also a test
```
You can make the most out of the turns in this conversation by creating all windows of this conversation (input turns are separated by /b):
```
Hi    How are you?
Hi/bHow are you?    Im doing well
Hi/bHow are you?/bIm doing well/bThis is a conversation?    Yes.
Hi/bHow are you?/bIm doing well/bThis is a conversation?/bYes.    Huh
Hi/bHow are you?/bIm doing well/bThis is a conversation?/bYes./bHuh    Its also a test
```
You can also limit the number of turns in a conversation by this means. As expanding the number of examples this way increases the size of the dataset dramatically, it is recommended to compress the dataset. TensorFlow Datasets supports compressed files for easy streaming and shuffling during training.

To generate splits, you may run the command
```
python3 split.py -compression_level 9 -workers 8 -dir ../data -out ../context
```
Note that the `-out` parameter is a prefix, and `-train.txt`/`-train.txt.gz` and `-val.txt`/`-val.txt.gz` will be appended to the split accordingly.
The script will create a directory named `temp` that contains all the partitioned files individually named in the format `[SPLIT]-ID.txt`/`[SPLIT]-ID.txt.gz`, which can will be merged automatically or later by running:
```
python3 split.py -step merge
```

## How is it done?
The process of cleaning the data includes removing a lot of the issues that can be found in discord chat logs, including:
> Please add a pull request or an issue if you can think of any other cases this script should cover!
- Filtering [common prefixes](./src/prefixes.txt) for popular bots on discord
- Filtering common system messages, such as pins, server joins, etc.
- Translating "special" unicode-based characters into the english alphabet (text like `𝔾𝕣𝕒𝕟𝕕𝕞𝕒'𝕤 🅂🄲🄰🅁🅈 ɖօɢ` to `Grandma's SCARY DOG` (a real username btw))
- Converting excessive spaces and unicode spaces to traditional spaces (text like `hi  		, you!` to `hi, you`)
- Replace users who left the the server(s) without being properly cached (they show up as `Deleted User`) with a random [name](./src/names.txt) that is attached to their id (names like `@Deleted User` to `@Jake`)
- Fixing excessive punctuation or spelling with certain limits (to keep ellipsis, for example) (text like `REEEEEEEEEEEEEEE..........` to `REEE...`)
- Filtering non-ascii characters and commonly used characters for ascii/unicode art (but keeping enough to make the vast majority of messages look ok) (text like `🖊️i like to write <🖊️>` to `i like to write`)
- Converting [supported emojis](./src/emojis.json) to their shorthand form (`😂` to `:joy:`,)
- Removing multiline code blocks while only removing the ticks around the single line code blocks (removing text like <code>\```text```</code>)
- Replacing newlines with an escaped newline (`hi\nhow are you?` to `hi\\nhow are you?`)
- Merging multi-message, single-author continuous messages into a single message merged with escaped newlines
- Removing URLs (like `https://jadeai.ml`)
- Removing emails (like `contact@j-fan.ml`)
- Removing phone numbers (like `+1 (123) 456-7890`)
- Removing custom emojis (like `:pogchamp:`)
- Removing toxic messages (like `f*** you`) *note: example is censored

Doing this for a lot of data (millions of messages) is extremely difficult to do, and this repo employs a lot of optimizations. If you're a developer and would like to benchmark the functionality of the scripts, you can run the script in [src/workers.py](./src/workers.py), which contains benchmarking tools. See the [README in src](./src/src) for my benchmark results.