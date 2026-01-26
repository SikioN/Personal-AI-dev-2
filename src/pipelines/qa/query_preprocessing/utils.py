from dataclasses import dataclass, field
from typing import Union, List

@dataclass
class QueryPreprocessingInfo:
    base_query: str
    denoised_query: Union[str, None] = None
    enchanced_query: Union[str, None] = None
    decomposed_query: Union[List[str], None] = None

    def to_str(self):
        str_denoised_query =  self.denoised_query if self.denoised_query is not None else "None"
        str_enchanced_query = self.enchanced_query if self.enchanced_query is not None else "None"
        str_decomposed_query = ';'.join(self.decomposed_query) if self.decomposed_query is not None else "None"
        return f"{self.base_query}|{str_denoised_query}|{str_enchanced_query}|{str_decomposed_query}"
