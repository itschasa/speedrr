from typing import Union



bit_convertion_dict = {
    "bit": 1,
    "B": 8,
    "byte": 8,
    "Kbit": 1000,
    "kilobit": 1000,
    "Kibit": 1024,
    "kibibit": 1024,
    "KB": 8000,
    "kilobyte": 8000,
    "KiB": 8 * 1024,
    "kibibyte": 8 * 1024,
    "Mbit": 1000**2,
    "megabit": 1000**2,
    "Mibit": 1024**2,
    "mebibit": 1024**2,
    "MB": 8 * 1000**2,
    "megabyte": 8 * 1000**2,
    "MiB": 8 * 1024**2,
    "mebibyte": 8 * 1024**2,
    "Gbit": 1000**3,
    "gigabit": 1000**3,
    "Gibit": 1024**3,
    "gibibit": 1024**3,
    "GB": 8 * 1000**3,
    "gigabyte": 8 * 1000**3,
    "GiB": 8 * 1024**3,
    "gibibyte": 8 * 1024**3,
}


def bit_conv(inp: Union[int, float], inp_type: str, out_type: str) -> float:
    "Convert an input in one type to an output in another type, to 3dp."
    return round(inp * bit_convertion_dict[inp_type] / bit_convertion_dict[out_type], 3)