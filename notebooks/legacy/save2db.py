import copy
import json
from collections import Counter
from neo4j_functions import Neo4jConnection

with open("Clean_DiaASQ.json", 'r') as inp:
    data = json.load(inp)

print(len(data["data"]))
samples = [element for element in data["data"] if "_" not in element["doc_id"]]
print(len(samples))

conn = Neo4jConnection(uri="bolt://31.207.47.254:7687", user="neo4j", pwd="password")

insert = True
total_triplets = []
good_samples = []
good_dialogs = 0
for sample in samples:
    triplets = sample["clean_triplets"]
    sentences = sample["sentences"]
    speakers = sample["speakers"]
    speakers_names = sample["speakers_names"]
    found = True
    for triplet in triplets:
        subj, obj, rel_data = triplet
        person = rel_data["speaker"]
        if person != "Unidentified" and person not in speakers_names:
            found = False
    if found:
        good_dialogs += 1
        new_sample = {
            key: value for key, value in sample.items()
            if key in ["doc_id", "sentences", "speakers", "triplets", "questions", "speakers_names"]
        }
        old_triplets = sample["clean_triplets"]
        tr2sp = {}
        for triplet in old_triplets:
            subj, obj, rel_data = triplet
            rel = rel_data["label"]
            speaker = rel_data["speaker"]
            tr2sp[(subj, rel, obj)] = speaker

        sentences = sample["sentences"]
        sentences = [f"{speaker}: {sentence}" for speaker, sentence in zip(new_sample["speakers_names"], sentences)]
        new_sample["sentences"] = sentences
        new_sample["speakers"] = ", ".join([str(element) for element in new_sample["speakers"]])
        clean_triplets = []
        tr2sent = {}
        for triplet in new_sample["triplets"]:
            if len(triplet) > 3 and triplet[-4] in ["pos", "neg", "neu"] and triplet[-2]:
                subj = triplet[-3]
                rel = triplet[-1]
                obj = triplet[-2]
                sent = triplet[-4]
                speaker = tr2sp.get((subj, rel, obj), "")
                if len(rel) > 1 and not rel[0].isdigit() and speaker and speaker != "Unidentified":
                    tr2sent[(subj, obj, speaker)] = sent
                    clean_triplets.append([subj, rel, obj, sent, speaker])
                    total_triplets.append([subj, rel, obj, sent])

        new_sentences = copy.deepcopy(new_sample["sentences"])
        for i in range(len(new_sentences)):
            found_sent = ""
            for (subj, obj, speaker), sent in tr2sent.items():
                if all([element.lower() in new_sentences[i].lower() for element in [subj, obj, speaker]]):
                    found_sent = sent
                    break
            if found_sent:
                new_sentences[i] = f"{new_sentences[i]} Sentiment: {found_sent}"

        new_sample["triplets"] = clean_triplets
        new_sample["sentences"] = new_sentences
        new_sample["questions"] = [question for question in new_sample["questions"]
                                   if not question["question"].startswith("The majority")]
        good_samples.append(new_sample)
        if insert:
            for triplet in clean_triplets:
                subj, rel, obj, sentiment, speaker = triplet
                subj = subj.replace(" ", "_")
                rel = rel.replace(" ", "_")
                for symb in "'.-":
                    rel = rel.replace(symb, "")
                obj = obj.replace(" ", "_")
                print(triplet, subj, rel, obj, sentiment, speaker)
                if len(rel) > 1:
                    res1 = conn.extract_node(node_type="device", node_name=subj, db="testdb")
                    if not res1:
                        conn.create_node(node_type="device", node_name=subj, db="testdb")
                    res2 = conn.extract_node(node_type="feature", node_name=obj, db="testdb")
                    if not res2:
                        conn.create_node(node_type="feature", node_name=obj, db="testdb")
                    conn.create_relationship_2props(
                        type1="device",
                        type2="feature",
                        name1=subj,
                        name2=obj,
                        rel_name=rel,
                        rel_prop_name1="person",
                        rel_prop_value1=speaker,
                        rel_prop_name2="sentiment",
                        rel_prop_value2=sentiment,
                        db="testdb"
                    )

mult_rels, mult_subj = 0, 0
stats1, stats2 = {}, {}
for subj, rel, obj, sent in total_triplets:
    if (subj, obj) not in stats1:
        stats1[(subj, obj)] = []
    stats1[(subj, obj)].append((rel, sent))
    if obj not in stats2:
        stats2[obj] = []
    stats2[obj].append((subj, rel, sent))

stats1 = {subj_obj: rel_sent for subj_obj, rel_sent in stats1.items() if len(rel_sent) > 1}
stats1 = list(stats1.items())
stats1 = sorted(stats1, key=lambda x: len(x[1]), reverse=True)

stats2 = {obj: subj_rel for obj, subj_rel in stats2.items() if len(subj_rel) > 1}
stats2 = list(stats2.items())
stats2 = sorted(stats2, key=lambda x: len(x[1]), reverse=True)

print("multiple rels", len(stats1))
print("multiple subjects", len(stats2))

with open("multiple_rels.json", 'w') as out:
    json.dump(stats1, out, indent=2)

with open("multiple_subjects.json", 'w') as out:
    json.dump(stats2, out, indent=2)

with open("multiple_subjects.txt", 'w') as out:
    for obj, subj_rel in stats2[:15]:
        subj_rel = sorted(subj_rel, key=lambda x: x[0])
        out.write(f"----- {obj}"+'\n')
        for element in subj_rel:
            out.write(str(element)+'\n')
        out.write("\n")

utterances, questions = [], []
with open("good_examples.json", 'w', encoding="utf8") as out:
    json.dump(good_samples[:10], out, indent=2, ensure_ascii=False)

for sample in good_samples:
    utterances += sample["sentences"]
    questions += sample["questions"]

with open("utterances_for_test.json", 'w', encoding="utf8") as out:
    json.dump(utterances, out, indent=2, ensure_ascii=False)

with open("questions_for_test.json", 'w', encoding="utf8") as out:
    json.dump(questions, out, indent=2, ensure_ascii=False)

print("good dialogs", good_dialogs)
print("utterances", len(utterances))
print("questions", len(questions))
