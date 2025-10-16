import io
from abc import ABC, abstractmethod

import pandas as pd
from paramiko.sftp_file import SFTPFile

from v3.routers.sources.sources_managers.file_manager_utils.utils import (
    get_csv_delimiter_by_one_line,
)


class FileHandler(ABC):
    def __init__(self, file: io.StringIO | io.BytesIO | SFTPFile):
        self.file = file

    @abstractmethod
    def parse(self) -> pd.DataFrame:
        pass

    @abstractmethod
    def parse_header(self) -> pd.DataFrame:
        pass


class StrictColumnFileHandler(FileHandler):
    def __init__(self, file: io.StringIO):
        super().__init__(file)
        self._delimiter_line_index = self._get_delimiter_line_index()
        self._delimiter_indices = self._get_delimiter_indices()

    def parse(self) -> pd.DataFrame:
        buffer = io.StringIO()
        self.file.seek(0)
        for i in range(self._delimiter_line_index - 1):
            self.file.readline()

        count = 0
        for line in self.file.readlines():
            parsed = self._parse_line(line)
            if parsed:
                buffer.write(parsed)
                count += 1
            if count == 5001:
                break
        buffer.seek(0)

        return pd.read_csv(buffer, sep=";").convert_dtypes()

    def parse_header(self) -> pd.DataFrame:
        buffer = io.StringIO()
        self.file.seek(0)
        for _ in range(self._delimiter_line_index - 1):
            self.file.readline()

        for _ in range(5):
            line = self.file.readline()
            line = self._parse_line(line)
            if line:
                buffer.write(line)
        buffer.seek(0)

        return pd.read_csv(buffer, sep=";").convert_dtypes()

    def _parse_line(self, line: str) -> str | None:
        values = []
        parsed = line.strip().replace(" ", "")

        if parsed and parsed == len(parsed) * parsed[0]:
            return
        if parsed.startswith("(") and parsed.endswith(")"):
            return

        for i in range(len(self._delimiter_indices) - 1):
            start = self._delimiter_indices[i]
            end = self._delimiter_indices[i + 1]
            values.append(line[start : end + 1].strip())

        line = ";".join(values)
        line += "\n"
        return line

    def _get_delimiter_line_index(self):
        self.file.seek(0)
        for idx, line in enumerate(self.file.readlines()):
            parsed = line.strip().replace(" ", "")
            if parsed and parsed == len(parsed) * parsed[0]:
                return idx

    def _get_delimiter_indices(self) -> list[int]:
        self.file.seek(0)
        entries = [0]
        for line in self.file.readlines():
            line = line.strip()
            parsed = line.replace(" ", "")
            if parsed and parsed == len(parsed) * parsed[0]:
                entries.extend(
                    [idx for idx, char in enumerate(line) if char == " "]
                )
                entries.append(len(line) - 1)
                return sorted(entries)


class CSVFileHandler(FileHandler):
    def __init__(self, file: io.StringIO | io.BytesIO | SFTPFile):
        super().__init__(file)
        self.delimiter = get_csv_delimiter_by_one_line(file.readline())
        self.file.seek(0)

    def parse(self) -> pd.DataFrame:
        return pd.read_csv(self.file, delimiter=self.delimiter).convert_dtypes()

    def parse_header(self) -> pd.DataFrame:
        df = pd.read_csv(self.file, delimiter=self.delimiter).convert_dtypes()
        df = df.head(4)
        return df
