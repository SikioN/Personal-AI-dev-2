from typing import List, Dict, Union

def entextr_custom_parse(raw_response: str, **kwargs) -> Dict[str, Union[List[str], str]]:
    # Expected format:
    # ent1 | ent2 ...
    # [Time]
    # year
    
    raw_response = raw_response.strip()
    if not raw_response:
         return {"entities": [], "time": None}
         
    parts = raw_response.split('[Time]')
    entities_part = parts[0].strip()
    time_part = parts[1].strip() if len(parts) > 1 else None
    
    # helper for entities
    extracted_entities = list(map(lambda item: item.strip(), entities_part.split('|')))
    filtered_entities = list(filter(lambda entitie: len(entitie) > 0, extracted_entities))
    
    # helper for time
    time_val = None
    if time_part and time_part.lower() != 'null':
        # Try to find 4 digit year
        import re
        match = re.search(r'\d{4}', time_part)
        if match:
            time_val = match.group(0)
            
    return {"entities": filtered_entities, "time": time_val}
