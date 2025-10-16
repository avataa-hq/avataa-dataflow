from v3.routers.sources.sources_managers.file_manager_utils.enums import (
    FileType,
)
from v3.routers.sources.sources_managers.file_manager_utils.handlers import (
    StrictColumnFileHandler,
    CSVFileHandler,
)


class FileValidator:
    handlers = {
        FileType.CSV: CSVFileHandler,
        FileType.STRICT_COLUMN: StrictColumnFileHandler,
    }

    def __init__(self, file):
        self.file = file
        self._file_type = None

    @property
    def file_type(self):
        return self._file_type

    @file_type.setter
    def file_type(self, value):
        if value not in FileType:
            raise ValueError(f"File type {value} is not supported!")
        self._file_type = value

    def get_file_handler(self):
        self.check_file_type()
        return self.handlers.get(self.file_type)(self.file)

    def check_file_type(self) -> None:
        self.file.seek(0)
        for idx, line in enumerate(self.file.readlines()):
            line = line.strip().replace(" ", "")
            if line and line == len(line) * line[0]:
                self.file_type = FileType.STRICT_COLUMN
                break

            if idx == 5:
                self.file_type = FileType.CSV
                break
        else:
            self.file_type = FileType.CSV

        self.file.seek(0)
