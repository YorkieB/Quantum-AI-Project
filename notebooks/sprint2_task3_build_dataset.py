#!/usr/bin/env python3
"""
Sprint 2, Task 2.3: Build Expanded Intent Dataset
===================================================
Generates 500+ diverse intent sentences for SEARCH vs ACTION.

Strategy:
  - Multiple phrasing patterns per intent
  - Varied vocabulary, formality, length
  - Include tricky edge cases
  - Proper train/val/test splits (70/15/15)
"""

import json
import os
import random
import numpy as np

random.seed(42)

# === SEARCH INTENT TEMPLATES ===
# Each template group covers a different way people ask for information

search_templates = {
    "direct_search": [
        "search for {topic}",
        "search the web for {topic}",
        "search online for {topic}",
        "do a search for {topic}",
        "run a search on {topic}",
        "google {topic}",
        "look up {topic}",
        "look up {topic} online",
        "look up {topic} for me",
    ],
    "find": [
        "find {topic}",
        "find information about {topic}",
        "find out about {topic}",
        "find me {topic}",
        "find details on {topic}",
        "find articles about {topic}",
        "find the latest on {topic}",
    ],
    "question_what": [
        "what is {topic}",
        "what are {topic}",
        "what does {topic} mean",
        "what happened with {topic}",
        "what is the best {topic}",
        "what are the top {topic}",
        "what is the difference between {topic_pair}",
    ],
    "question_how": [
        "how do you {action_topic}",
        "how to {action_topic}",
        "how does {topic} work",
        "how much does {topic} cost",
        "how long does {topic} take",
        "how many {topic} are there",
        "how far is {place}",
    ],
    "question_who": [
        "who is {person}",
        "who invented {topic}",
        "who won {event}",
        "who wrote {creative}",
        "who directed {creative}",
        "who discovered {topic}",
    ],
    "question_where": [
        "where is {place}",
        "where can I find {topic}",
        "where is the nearest {place_type}",
        "where should I go for {topic}",
        "where did {event} happen",
    ],
    "question_when": [
        "when is {event}",
        "when does {place_type} open",
        "when was {topic} invented",
        "when did {event} happen",
        "when is the next {event}",
    ],
    "show_tell": [
        "show me {topic}",
        "show me pictures of {topic}",
        "tell me about {topic}",
        "tell me more about {topic}",
        "give me information on {topic}",
        "give me details about {topic}",
        "I want to know about {topic}",
        "I need information on {topic}",
    ],
    "check": [
        "check the weather in {place}",
        "check the news about {topic}",
        "check the score of {event}",
        "check the price of {topic}",
        "check the time in {place}",
        "check if {topic} is open",
        "check my {info_type}",
    ],
}

# Fill-in values
topics = [
    "recipes", "dogs", "cats", "python programming", "machine learning",
    "quantum computing", "climate change", "electric cars", "space travel",
    "bitcoin price", "yoga exercises", "healthy meals", "running shoes",
    "winter jackets", "phone cases", "laptop deals", "flight tickets",
    "hotel rooms", "car insurance", "mortgage rates", "stock market",
    "football results", "tennis scores", "movie reviews", "book recommendations",
    "podcast suggestions", "video games", "gardening tips", "home renovation",
    "baby names", "wedding venues", "holiday destinations", "train schedules",
    "bus routes", "parking spots", "restaurant menus", "coffee beans",
    "vitamin supplements", "skincare products", "haircut styles", "gym memberships",
    "piano lessons", "guitar chords", "painting techniques", "photography tips",
    "astronomy facts", "dinosaur species", "ocean currents", "volcano eruptions",
    "earthquake safety", "first aid", "tax rules", "visa requirements",
    "passport renewal", "driving test tips", "job interviews", "salary comparisons",
    "university rankings", "scholarship applications", "history of Rome",
    "the solar system", "deep sea creatures", "rainforest animals",
]

topic_pairs = [
    "cats and dogs", "Python and JavaScript", "iOS and Android",
    "renting and buying", "coffee and tea", "yoga and pilates",
    "stocks and bonds", "solar and wind energy", "Netflix and Disney Plus",
    "electric and hybrid cars",
]

action_topics = [
    "make pancakes", "tie a tie", "change a tyre", "fix a leaky tap",
    "train a puppy", "grow tomatoes", "bake sourdough bread",
    "learn to swim", "start a business", "file taxes", "cook risotto",
    "clean an oven", "iron a shirt", "wrap a present", "build a website",
    "write a CV", "plan a budget", "meditate properly", "do a backflip",
    "solve a Rubik cube",
]

persons = [
    "Elon Musk", "Taylor Swift", "Albert Einstein", "Marie Curie",
    "the prime minister", "the president", "Lionel Messi", "Beyonce",
    "Shakespeare", "Leonardo da Vinci", "Nikola Tesla", "Ada Lovelace",
]

events = [
    "the world cup", "the Olympics", "the Super Bowl", "the election",
    "the Oscars", "the Champions League final", "the marathon",
    "the concert", "the festival", "the grand prix",
]

creatives = [
    "Harry Potter", "the Mona Lisa", "Bohemian Rhapsody", "the Great Gatsby",
    "Star Wars", "the Godfather", "Pride and Prejudice", "Inception",
]

places = [
    "London", "Tokyo", "New York", "Paris", "Sydney", "Berlin",
    "the Eiffel Tower", "the Grand Canyon", "Mount Everest",
    "the nearest train station", "the airport", "the city centre",
]

place_types = [
    "hospital", "pharmacy", "supermarket", "petrol station", "bank",
    "post office", "library", "gym", "cinema", "restaurant",
    "coffee shop", "park", "museum", "dentist", "barber",
]

info_types = [
    "bank balance", "credit score", "order status", "delivery tracking",
    "flight status", "appointment schedule", "calendar",
]

# === ACTION INTENT TEMPLATES ===
action_templates = {
    "set_alarm_timer": [
        "set an alarm for {time}",
        "set a timer for {duration}",
        "set a reminder for {time}",
        "set a reminder to {task} at {time}",
        "wake me up at {time}",
        "remind me to {task}",
        "remind me about {task} at {time}",
        "create an alarm for {time}",
        "schedule a reminder for {time}",
        "alert me at {time}",
    ],
    "lights": [
        "turn on the {room} lights",
        "turn off the {room} lights",
        "switch on the {room} lights",
        "switch off the {room} lights",
        "dim the {room} lights",
        "brighten the {room} lights",
        "turn the {room} lights {on_off}",
        "set the {room} lights to {brightness}",
        "lights {on_off} in the {room}",
    ],
    "music_media": [
        "play {music}",
        "play some {genre} music",
        "play my {playlist} playlist",
        "play the latest {media_type}",
        "pause the music",
        "stop the music",
        "resume playback",
        "skip this song",
        "skip to the next track",
        "go back to the previous song",
        "shuffle my playlist",
        "turn the volume {up_down}",
        "set the volume to {number}",
        "mute the speakers",
        "unmute the speakers",
    ],
    "message_call": [
        "send a message to {person_name}",
        "text {person_name}",
        "message {person_name} saying {short_msg}",
        "call {person_name}",
        "ring {person_name}",
        "dial {person_name}",
        "phone {person_name}",
        "send an email to {person_name}",
        "reply to {person_name}",
        "read my messages",
        "read my latest email",
        "check my texts",
    ],
    "smart_home": [
        "lock the {door}",
        "unlock the {door}",
        "close the {window_door}",
        "open the {window_door}",
        "turn on the {appliance}",
        "turn off the {appliance}",
        "start the {appliance}",
        "stop the {appliance}",
        "set the thermostat to {temp}",
        "turn the heating {on_off}",
        "turn the air conditioning {on_off}",
        "arm the security system",
        "disarm the alarm",
        "activate the robot vacuum",
    ],
    "navigation": [
        "navigate to {destination}",
        "take me to {destination}",
        "get directions to {destination}",
        "start navigation to {destination}",
        "how do I get to {destination}",
    ],
    "device_control": [
        "take a photo",
        "take a screenshot",
        "open {app}",
        "close {app}",
        "launch {app}",
        "turn on bluetooth",
        "turn off wifi",
        "enable do not disturb",
        "disable airplane mode",
        "increase the screen brightness",
        "decrease the screen brightness",
        "restart the computer",
        "shut down the laptop",
    ],
}

# Action fill-in values
times = [
    "seven am", "eight thirty", "six in the morning", "noon",
    "three pm", "midnight", "tomorrow morning", "five minutes",
    "half an hour", "ten o clock", "quarter past nine", "in two hours",
]

durations = [
    "five minutes", "ten minutes", "half an hour", "one hour",
    "two hours", "fifteen minutes", "twenty seconds", "forty five minutes",
]

tasks = [
    "call mum", "buy milk", "take the bins out", "feed the cat",
    "pick up the kids", "water the plants", "submit the report",
    "book the dentist", "renew the insurance", "pay the rent",
    "order groceries", "walk the dog", "clean the kitchen",
    "attend the meeting", "collect the parcel",
]

rooms = [
    "bedroom", "living room", "kitchen", "bathroom", "hallway",
    "dining room", "garage", "office", "study", "conservatory",
    "porch", "garden", "basement", "attic", "nursery",
]

music_items = [
    "my favourite playlist", "something relaxing", "some jazz",
    "the Beatles", "classical music", "today's top hits",
    "chill vibes", "workout music", "morning coffee playlist",
    "some background music", "lo-fi beats", "rock anthems",
]

genres = ["jazz", "rock", "pop", "classical", "hip hop", "electronic",
          "country", "blues", "reggae", "indie", "folk", "soul", "R and B"]

playlists = ["morning", "workout", "chill", "party", "driving", "cooking",
             "study", "sleep", "favourite", "discover weekly"]

media_types = ["podcast", "podcast episode", "audiobook", "news briefing",
               "radio station", "album"]

person_names = ["John", "Sarah", "Mum", "Dad", "Alex", "Emma", "James",
                "Sophie", "Mike", "Lisa", "David", "Rachel", "Tom", "Kate"]

short_msgs = ["I will be late", "on my way", "see you soon",
              "call me back", "happy birthday", "thank you"]

doors = ["front door", "back door", "garage door", "side gate"]

window_doors = ["front door", "back door", "garage", "kitchen window",
                "bedroom window", "blinds", "curtains"]

appliances = ["coffee machine", "washing machine", "dishwasher", "oven",
              "microwave", "fan", "heater", "television", "robot vacuum",
              "air purifier", "humidifier", "dehumidifier"]

temps = ["twenty degrees", "eighteen degrees", "twenty two degrees",
         "nineteen degrees", "twenty five degrees"]

destinations = ["home", "work", "the office", "the airport",
                "the train station", "the nearest petrol station",
                "the hospital", "Tesco", "the gym", "school"]

apps = ["Spotify", "WhatsApp", "the camera", "Settings", "Maps",
        "YouTube", "Netflix", "the calculator", "Notes", "the browser"]

on_off = ["on", "off"]
up_down = ["up", "down"]
brightness = ["fifty percent", "full", "low", "medium", "bright"]
number = ["thirty", "fifty", "seventy", "maximum"]


def fill_template(template, intent):
    """Fill a template with random values."""
    s = template
    s = s.replace("{topic}", random.choice(topics))
    s = s.replace("{topic_pair}", random.choice(topic_pairs))
    s = s.replace("{action_topic}", random.choice(action_topics))
    s = s.replace("{person}", random.choice(persons))
    s = s.replace("{event}", random.choice(events))
    s = s.replace("{creative}", random.choice(creatives))
    s = s.replace("{place}", random.choice(places))
    s = s.replace("{place_type}", random.choice(place_types))
    s = s.replace("{info_type}", random.choice(info_types))
    s = s.replace("{time}", random.choice(times))
    s = s.replace("{duration}", random.choice(durations))
    s = s.replace("{task}", random.choice(tasks))
    s = s.replace("{room}", random.choice(rooms))
    s = s.replace("{music}", random.choice(music_items))
    s = s.replace("{genre}", random.choice(genres))
    s = s.replace("{playlist}", random.choice(playlists))
    s = s.replace("{media_type}", random.choice(media_types))
    s = s.replace("{person_name}", random.choice(person_names))
    s = s.replace("{short_msg}", random.choice(short_msgs))
    s = s.replace("{door}", random.choice(doors))
    s = s.replace("{window_door}", random.choice(window_doors))
    s = s.replace("{appliance}", random.choice(appliances))
    s = s.replace("{temp}", random.choice(temps))
    s = s.replace("{destination}", random.choice(destinations))
    s = s.replace("{app}", random.choice(apps))
    s = s.replace("{on_off}", random.choice(on_off))
    s = s.replace("{up_down}", random.choice(up_down))
    s = s.replace("{brightness}", random.choice(brightness))
    s = s.replace("{number}", random.choice(number))
    return s


# === GENERATE DATASET ===
print("Generating intent dataset...")

search_sentences = []
action_sentences = []

# Generate ~300 of each
TARGET_PER_CLASS = 300

for _ in range(TARGET_PER_CLASS * 3):  # oversample then deduplicate
    # Pick random template group and template
    group = random.choice(list(search_templates.values()))
    template = random.choice(group)
    sent = fill_template(template, "search")
    search_sentences.append(sent)

    group = random.choice(list(action_templates.values()))
    template = random.choice(group)
    sent = fill_template(template, "action")
    action_sentences.append(sent)

# Deduplicate
search_sentences = list(dict.fromkeys(search_sentences))
action_sentences = list(dict.fromkeys(action_sentences))

# Trim to target
search_sentences = search_sentences[:TARGET_PER_CLASS]
action_sentences = action_sentences[:TARGET_PER_CLASS]

print(f"  Generated: {len(search_sentences)} SEARCH, {len(action_sentences)} ACTION")

# === CREATE SPLITS ===
# Combine and shuffle
all_sentences = [(s, 0) for s in search_sentences] + [(s, 1) for s in action_sentences]
random.shuffle(all_sentences)

n_total = len(all_sentences)
n_train = int(n_total * 0.70)
n_val = int(n_total * 0.15)

train_data = all_sentences[:n_train]
val_data = all_sentences[n_train:n_train + n_val]
test_data = all_sentences[n_train + n_val:]

print(f"\n  Splits:")
print(f"    Train: {len(train_data)} ({sum(1 for _,l in train_data if l==0)} SEARCH, {sum(1 for _,l in train_data if l==1)} ACTION)")
print(f"    Val:   {len(val_data)} ({sum(1 for _,l in val_data if l==0)} SEARCH, {sum(1 for _,l in val_data if l==1)} ACTION)")
print(f"    Test:  {len(test_data)} ({sum(1 for _,l in test_data if l==0)} SEARCH, {sum(1 for _,l in test_data if l==1)} ACTION)")

# === SAVE ===
os.makedirs("data", exist_ok=True)

dataset = {
    "description": "Jarvis Intent Classification Dataset v1",
    "classes": {"0": "SEARCH", "1": "ACTION"},
    "stats": {
        "total": n_total,
        "train": len(train_data),
        "val": len(val_data),
        "test": len(test_data),
    },
    "train": [{"sentence": s, "label": l} for s, l in train_data],
    "val": [{"sentence": s, "label": l} for s, l in val_data],
    "test": [{"sentence": s, "label": l} for s, l in test_data],
}

with open("data/jarvis_intents_v1.json", "w") as f:
    json.dump(dataset, f, indent=2)

# Also save as simple text files for easy loading
for split_name, split_data in [("train", train_data), ("val", val_data), ("test", test_data)]:
    with open(f"data/intents_{split_name}.txt", "w") as f:
        for sent, label in split_data:
            f.write(f"{label}\t{sent}\n")

print(f"\nDataset saved to data/jarvis_intents_v1.json")
print(f"Text files: data/intents_train.txt, intents_val.txt, intents_test.txt")

# === SAMPLE PREVIEW ===
print("\nSample sentences:")
print("-" * 50)
for i in range(5):
    s, l = train_data[i]
    print(f"  [{intent_names[l]}] {s}")
print("  ...")
for i in range(5):
    s, l = test_data[i]
    print(f"  [{intent_names[l]}] {s}")

intent_names = {0: "SEARCH", 1: "ACTION"}
print(f"\nTask 2.3 Step 1 Complete - Dataset generated")
print(f"Next: Re-run classical and quantum models on this dataset")