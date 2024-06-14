from typing import Union



bit_convertion_dict = {
    "bit": 1,
    "b": 8,
    "kbit": 1000,
    "kb": 8000,
    "mbit": 1000000,
    "mb": 8000000,
}


def bit_conv(inp: Union[int, float], inp_type: str, out_type: str) -> float:
    "Convert an input in one type to an output in another type, to 3dp."
    return round(inp * bit_convertion_dict[inp_type] / bit_convertion_dict[out_type], 3)