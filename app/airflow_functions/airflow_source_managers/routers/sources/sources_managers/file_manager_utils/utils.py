import csv
import io
from typing import Union


def get_csv_delimiter(file_data: bytes):
    """Returns csv delimiter"""
    with io.StringIO(file_data.decode("utf-8")) as data:
        sniffer = csv.Sniffer()
        delimiter = sniffer.sniff(data.readline()).delimiter
    return delimiter


def get_csv_delimiter_by_one_line(line: Union[bytes, str]):
    """Returns csv delimiter by one line"""
    sniffer = csv.Sniffer()
    if isinstance(line, bytes):
        delimiter = sniffer.sniff(line.decode("utf-8")).delimiter
    else:
        delimiter = sniffer.sniff(line).delimiter
    return delimiter
