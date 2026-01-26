# Source: https://amitness.com/2020/08/information-retrieval-evaluation/

from torchmetrics.text.rouge import ROUGEScore
from torchmetrics.text import BLEUScore
import evaluate
from typing import List, Dict
from torchmetrics.text.bert import BERTScore

#
class ReaderMetrics:
    def __init__(self, base_dir: str, bs_model_path: str):
        self.rouge_obj = ROUGEScore()
        self.bleu1_obj = BLEUScore(n_gram=1)
        self.bleu2_obj = BLEUScore(n_gram=2)
        print("Loading Meteor...")
        self.meteor_obj = evaluate.load(f"{base_dir}/src/utils/metrics/meteor")
        print("Loading ExactMatch")
        self.em_obj = evaluate.load(f"{base_dir}/src/utils/metrics/exact_match")
        print("Loading BertScore")
        self.bertscore_obj = BERTScore(f"{base_dir}/models/{bs_model_path}", return_hash=True)

    def bertscore(self, predicted: List[str], targets: List[str]) -> Dict[str, List[float]]:
        output = self.bertscore_obj(predicted, targets)
        return output

    def rougel(self, predicted: List[str], targets: List[str]) -> List[float]:
        return [self.rouge_obj(
            predicted[i], targets[i])['rougeL_fmeasure']
                 for i in range(len(targets))]

    def bleu1(self, predicted: List[str], targets: List[str]) -> List[float]:
        return [self.bleu1_obj(
            [predicted[i]], [[targets[i]]])
                 for i in range(len(targets))]

    def bleu2(self, predicted: List[str], targets: List[str]) -> List[float]:
        return [self.bleu2_obj(
            [predicted[i]], [[targets[i]]])
                 for i in range(len(targets))]

    def meteor(self, predicted: List[str], targets: List[str]) -> List[float]:
        return [self.meteor_obj.compute(
            predictions=[predicted[i]], references=[targets[i]])['meteor']
                 for i in range(len(targets))]

    def exact_match(self, predicted: List[str], targets: List[str]) -> List[float]:
        return [self.em_obj.compute(
            predictions=[predicted[i]], references=[targets[i]], ignore_case=True)["exact_match"]
                for i in range(len(targets))]
