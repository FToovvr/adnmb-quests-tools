from typing import List, Any


def flatten_list(the_list: List[Any]):
    result = []
    for elem in the_list:
        if isinstance(elem, list):
            result.extend(flatten_list(elem))
        else:
            result.append(elem)
    return result
